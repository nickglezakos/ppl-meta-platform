// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'email_settings.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

EmailSettings _$EmailSettingsFromJson(Map<String, dynamic> json) =>
    EmailSettings(
      id: (json['id'] as num).toInt(),
      mailEnabled: json['mail_enabled'] as bool,
      mailServer: json['mail_server'] as String,
      mailPort: (json['mail_port'] as num).toInt(),
      mailUsername: json['mail_username'] as String,
      mailPassword: json['mail_password'] as String,
      mailFrom: json['mail_from'] as String,
      mailFromName: json['mail_from_name'] as String,
      mailStarttls: json['mail_starttls'] as bool,
      mailSslTls: json['mail_ssl_tls'] as bool,
      useCredentials: json['use_credentials'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );

Map<String, dynamic> _$EmailSettingsToJson(EmailSettings instance) =>
    <String, dynamic>{
      'id': instance.id,
      'mail_enabled': instance.mailEnabled,
      'mail_server': instance.mailServer,
      'mail_port': instance.mailPort,
      'mail_username': instance.mailUsername,
      'mail_password': instance.mailPassword,
      'mail_from': instance.mailFrom,
      'mail_from_name': instance.mailFromName,
      'mail_starttls': instance.mailStarttls,
      'mail_ssl_tls': instance.mailSslTls,
      'use_credentials': instance.useCredentials,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

EmailSettingsUpdate _$EmailSettingsUpdateFromJson(Map<String, dynamic> json) =>
    EmailSettingsUpdate(
      mailEnabled: json['mail_enabled'] as bool?,
      mailServer: json['mail_server'] as String?,
      mailPort: (json['mail_port'] as num?)?.toInt(),
      mailUsername: json['mail_username'] as String?,
      mailPassword: json['mail_password'] as String?,
      mailFrom: json['mail_from'] as String?,
      mailFromName: json['mail_from_name'] as String?,
      mailStarttls: json['mail_starttls'] as bool?,
      mailSslTls: json['mail_ssl_tls'] as bool?,
      useCredentials: json['use_credentials'] as bool?,
    );

Map<String, dynamic> _$EmailSettingsUpdateToJson(
        EmailSettingsUpdate instance) =>
    <String, dynamic>{
      'mail_enabled': instance.mailEnabled,
      'mail_server': instance.mailServer,
      'mail_port': instance.mailPort,
      'mail_username': instance.mailUsername,
      'mail_password': instance.mailPassword,
      'mail_from': instance.mailFrom,
      'mail_from_name': instance.mailFromName,
      'mail_starttls': instance.mailStarttls,
      'mail_ssl_tls': instance.mailSslTls,
      'use_credentials': instance.useCredentials,
    };
