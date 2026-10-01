/// Models for non-blocking rich media message overlays.
library;

class RichMessageOverlayPayload {
  final String templateId;
  final String title;
  final String? message;
  final String htmlBody;
  final String? mediaUrl;
  final String? soundUrl;
  final int titleFontSize;
  final int messageFontSize;
  final String titleColor;
  final String messageColor;
  final String backgroundColor;
  final int opacity;
  final String layout;
  final int durationMs;

  const RichMessageOverlayPayload({
    required this.templateId,
    this.title = '',
    this.message,
    required this.htmlBody,
    this.mediaUrl,
    this.soundUrl,
    this.titleFontSize = 48,
    this.messageFontSize = 28,
    this.titleColor = '#FFFFFF',
    this.messageColor = '#F0F0F0',
    this.backgroundColor = '#000000',
    this.opacity = 80,
    this.layout = 'card',
    this.durationMs = 15000,
  });

  factory RichMessageOverlayPayload.fromJson(Map<String, dynamic> json) {
    return RichMessageOverlayPayload(
      templateId: (json['template_id'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      message: json['message']?.toString(),
      htmlBody: (json['html_body'] ?? '').toString(),
      mediaUrl: json['media_url']?.toString(),
      soundUrl: json['sound_url']?.toString(),
      titleFontSize: _asInt(json['title_font_size'], 48),
      messageFontSize: _asInt(json['message_font_size'], 28),
      titleColor: (json['title_color'] ?? '#FFFFFF').toString(),
      messageColor: (json['message_color'] ?? '#F0F0F0').toString(),
      backgroundColor: (json['background_color'] ?? '#000000').toString(),
      opacity: _asInt(json['opacity'], 80),
      layout: (json['layout'] ?? 'card').toString(),
      durationMs: _asInt(json['duration_ms'], 15000),
    );
  }

  Map<String, dynamic> toJson() => {
        'template_id': templateId,
        'title': title,
        'message': message,
        'html_body': htmlBody,
        'media_url': mediaUrl,
        'sound_url': soundUrl,
        'title_font_size': titleFontSize,
        'message_font_size': messageFontSize,
        'title_color': titleColor,
        'message_color': messageColor,
        'background_color': backgroundColor,
        'opacity': opacity,
        'layout': layout,
        'duration_ms': durationMs,
      };

  static int _asInt(dynamic value, int fallback) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? fallback;
    return fallback;
  }
}
