import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:signage_simple_player/models/rich_message_models.dart';
import 'package:signage_simple_player/services/rich_message_overlay_service.dart';
import 'package:webview_flutter/webview_flutter.dart';

/// Non-blocking rich message overlay rendered above playlist video.
class RichMessageOverlay extends StatelessWidget {
  const RichMessageOverlay({super.key});

  @override
  Widget build(BuildContext context) {
    final service = context.watch<RichMessageOverlayService>();
    if (!service.isVisible || service.current == null) {
      return const SizedBox.shrink();
    }

    final payload = service.current!;
    // Key by generation so every show remounts (same template still reappears).
    return Positioned.fill(
      key: ValueKey('rich-message-${service.showGeneration}'),
      child: _RichMessageOverlayBody(
        key: ValueKey('rich-message-body-${service.showGeneration}'),
        payload: payload,
        onDismiss: () => service.dismiss(),
      ),
    );
  }
}

class _RichMessageOverlayBody extends StatefulWidget {
  final RichMessageOverlayPayload payload;
  final VoidCallback onDismiss;

  const _RichMessageOverlayBody({
    super.key,
    required this.payload,
    required this.onDismiss,
  });

  @override
  State<_RichMessageOverlayBody> createState() => _RichMessageOverlayBodyState();
}

class _RichMessageOverlayBodyState extends State<_RichMessageOverlayBody> {
  WebViewController? _webController;
  bool _webViewFailed = false;

  @override
  void initState() {
    super.initState();
    _initWebView();
  }

  void _initWebView() {
    final html = widget.payload.htmlBody;
    if (html.isEmpty) {
      _webViewFailed = true;
      return;
    }
    try {
      _webController = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(const Color(0x00000000))
        ..loadHtmlString(html);
      _webViewFailed = false;
    } catch (_) {
      _webViewFailed = true;
      _webController = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final payload = widget.payload;
    return IgnorePointer(
      ignoring: false,
      child: Material(
        color: Colors.transparent,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Container(color: Colors.black.withValues(alpha: 0.15)),
            _buildLayout(payload),
            Positioned(
              top: 12,
              right: 12,
              child: IconButton(
                icon: const Icon(Icons.close, color: Colors.white70),
                tooltip: 'Dismiss message',
                onPressed: widget.onDismiss,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLayout(RichMessageOverlayPayload payload) {
    final child = _webViewFailed || _webController == null
        ? _buildFlutterFallback(payload)
        : WebViewWidget(controller: _webController!);

    switch (payload.layout) {
      case 'fullscreen':
        return Positioned.fill(child: child);
      case 'banner':
        return Positioned(
          top: 0,
          left: 0,
          right: 0,
          height: MediaQuery.of(context).size.height * 0.35,
          child: child,
        );
      case 'card':
      default:
        return Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: 720,
              maxHeight: MediaQuery.of(context).size.height * 0.8,
            ),
            child: SizedBox(
              width: MediaQuery.of(context).size.width * 0.92,
              height: MediaQuery.of(context).size.height * 0.55,
              child: child,
            ),
          ),
        );
    }
  }

  Widget _buildFlutterFallback(RichMessageOverlayPayload payload) {
    final bg = _parseColor(payload.backgroundColor)
        .withValues(alpha: (payload.opacity.clamp(0, 100)) / 100.0);
    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius:
            payload.layout == 'card' ? BorderRadius.circular(16) : null,
      ),
      padding: const EdgeInsets.all(28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            payload.title,
            style: TextStyle(
              color: _parseColor(payload.titleColor),
              fontSize: payload.titleFontSize.toDouble(),
              fontWeight: FontWeight.bold,
              height: 1.15,
            ),
          ),
          if (payload.message != null && payload.message!.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              payload.message!,
              style: TextStyle(
                color: _parseColor(payload.messageColor),
                fontSize: payload.messageFontSize.toDouble(),
                height: 1.35,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Color _parseColor(String hex) {
    var raw = hex.trim().replaceFirst('#', '');
    if (raw.length == 3) {
      raw = raw.split('').map((c) => '$c$c').join();
    }
    if (raw.length == 6) raw = 'FF$raw';
    final value = int.tryParse(raw, radix: 16);
    if (value == null) return Colors.white;
    return Color(value);
  }
}
