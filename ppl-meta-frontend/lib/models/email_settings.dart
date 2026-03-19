// Email settings model for SMTP configuration
import 'package:json_annotation/json_annotation.dart';

part 'email_settings.g.dart';

@JsonSerializable()
class EmailSettings {
  final int id;
  @JsonKey(name: 'mail_enabled')
  final bool mailEnabled;
  @JsonKey(name: 'mail_server')
  final String mailServer;
  @JsonKey(name: 'mail_port')
  final int mailPort;
  @JsonKey(name: 'mail_username')
  final String mailUsername;
  @JsonKey(name: 'mail_password')
  final String mailPassword;
  @JsonKey(name: 'mail_from')
  final String mailFrom;
  @JsonKey(name: 'mail_from_name')
  final String mailFromName;
  @JsonKey(name: 'mail_starttls')
  final bool mailStarttls;
  @JsonKey(name: 'mail_ssl_tls')
  final bool mailSslTls;
  @JsonKey(name: 'use_credentials')
  final bool useCredentials;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  const EmailSettings({
    required this.id,
    required this.mailEnabled,
    required this.mailServer,
    required this.mailPort,
    required this.mailUsername,
    required this.mailPassword,
    required this.mailFrom,
    required this.mailFromName,
    required this.mailStarttls,
    required this.mailSslTls,
    required this.useCredentials,
    required this.createdAt,
    required this.updatedAt,
  });

  factory EmailSettings.fromJson(Map<String, dynamic> json) =>
      _$EmailSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$EmailSettingsToJson(this);

  EmailSettings copyWith({
    int? id,
    bool? mailEnabled,
    String? mailServer,
    int? mailPort,
    String? mailUsername,
    String? mailPassword,
    String? mailFrom,
    String? mailFromName,
    bool? mailStarttls,
    bool? mailSslTls,
    bool? useCredentials,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return EmailSettings(
      id: id ?? this.id,
      mailEnabled: mailEnabled ?? this.mailEnabled,
      mailServer: mailServer ?? this.mailServer,
      mailPort: mailPort ?? this.mailPort,
      mailUsername: mailUsername ?? this.mailUsername,
      mailPassword: mailPassword ?? this.mailPassword,
      mailFrom: mailFrom ?? this.mailFrom,
      mailFromName: mailFromName ?? this.mailFromName,
      mailStarttls: mailStarttls ?? this.mailStarttls,
      mailSslTls: mailSslTls ?? this.mailSslTls,
      useCredentials: useCredentials ?? this.useCredentials,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

@JsonSerializable()
class EmailSettingsUpdate {
  @JsonKey(name: 'mail_enabled')
  final bool? mailEnabled;
  @JsonKey(name: 'mail_server')
  final String? mailServer;
  @JsonKey(name: 'mail_port')
  final int? mailPort;
  @JsonKey(name: 'mail_username')
  final String? mailUsername;
  @JsonKey(name: 'mail_password')
  final String? mailPassword;
  @JsonKey(name: 'mail_from')
  final String? mailFrom;
  @JsonKey(name: 'mail_from_name')
  final String? mailFromName;
  @JsonKey(name: 'mail_starttls')
  final bool? mailStarttls;
  @JsonKey(name: 'mail_ssl_tls')
  final bool? mailSslTls;
  @JsonKey(name: 'use_credentials')
  final bool? useCredentials;

  const EmailSettingsUpdate({
    this.mailEnabled,
    this.mailServer,
    this.mailPort,
    this.mailUsername,
    this.mailPassword,
    this.mailFrom,
    this.mailFromName,
    this.mailStarttls,
    this.mailSslTls,
    this.useCredentials,
  });

  factory EmailSettingsUpdate.fromJson(Map<String, dynamic> json) =>
      _$EmailSettingsUpdateFromJson(json);

  Map<String, dynamic> toJson() => _$EmailSettingsUpdateToJson(this);
}
