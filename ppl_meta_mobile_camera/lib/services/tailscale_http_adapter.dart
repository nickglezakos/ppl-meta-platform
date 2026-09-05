import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:http/http.dart' as pkg_http;

/// A [HttpClientAdapter] (dio) that transparently routes every request through
/// the camera's own embedded Tailscale node (WP3).
///
/// [Tailscale.instance.http.client] is a `package:http` client whose requests
/// travel over the tailnet — LAN-direct when co-located, DERPF-relayed
/// otherwise. Bridging it to dio lets existing dio-based clients use the mesh
/// without rewrites.
///
/// This is best-effort: the caller only installs it when the embedded node is
/// up ([TailscaleService.isUp]).
class TailscaleHttpClientAdapter implements HttpClientAdapter {
  final pkg_http.Client _client;

  TailscaleHttpClientAdapter(this._client);

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    // 1. Build a package:http request from the dio RequestOptions.
    final uri = options.uri;
    final headers = <String, String>{
      for (final entry in options.headers.entries)
        if (entry.value != null) entry.key: entry.value.toString(),
    };

    // Assemble the request body bytes. dio normally serializes the body and
    // delivers it via requestStream; fall back to options.data for the rare
    // cases where the transformer hasn't run yet.
    Uint8List? body;
    if (requestStream != null) {
      final builder = BytesBuilder(copy: false);
      await for (final chunk in requestStream) {
        builder.add(chunk);
      }
      body = builder.takeBytes();
    } else if (options.data != null) {
      final data = options.data;
      if (data is String) {
        body = Uint8List.fromList(utf8.encode(data));
      } else if (data is Uint8List) {
        body = data;
      } else if (data is List<int>) {
        body = Uint8List.fromList(data);
      } else if (data is Map) {
        body = Uint8List.fromList(utf8.encode(jsonEncode(data)));
      }
    }

    final request = pkg_http.Request(options.method, uri)
      ..headers.addAll(headers);
    if (body != null) {
      request.bodyBytes = body;
    }

    // 2. Send over the tailnet (the camera's own node) and adapt the response.
    final response = await _client.send(request);
    final responseBytes = await response.stream.toBytes();

    return ResponseBody.fromBytes(
      responseBytes,
      response.statusCode,
      statusMessage: response.reasonPhrase,
      headers: response.headers.map((k, v) => MapEntry(k, <String>[v])),
    );
  }

  @override
  void close({bool force = false}) {
    // Intentionally do NOT close the tailscale client — it is owned by
    // TailscaleService and reused for the process lifetime.
  }
}