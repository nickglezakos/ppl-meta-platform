import 'dart:html' as html;

Future<String?> downloadFileBytes({
  required List<int> bytes,
  required String filename,
  String mimeType = 'application/octet-stream',
}) async {
  final blob = html.Blob([bytes], mimeType);
  final url = html.Url.createObjectUrlFromBlob(blob);
  final anchor = html.AnchorElement(href: url)
    ..setAttribute('download', filename)
    ..click();
  html.Url.revokeObjectUrl(url);
  return 'Downloads/$filename';
}
