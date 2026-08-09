import 'package:json_annotation/json_annotation.dart';

part 'capability.g.dart';

/// Capability model representing a named permission in the RBAC system.
@JsonSerializable()
class Capability {
  final int id;
  final String name;

  const Capability({
    required this.id,
    required this.name,
  });

  /// Derive namespace from name: "auth.roles.create" → "auth", "cameras:view" → "cameras"
  String get namespace {
    if (name.contains(':')) return name.split(':').first;
    if (name.contains('.')) return name.split('.').first;
    return 'other';
  }

  factory Capability.fromJson(Map<String, dynamic> json) =>
      _$CapabilityFromJson(json);
  Map<String, dynamic> toJson() => _$CapabilityToJson(this);

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is Capability && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => 'Capability(id: $id, name: $name)';
}
