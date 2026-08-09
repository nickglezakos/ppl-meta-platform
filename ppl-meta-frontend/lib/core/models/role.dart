import 'package:json_annotation/json_annotation.dart';

part 'role.g.dart';

/// Role model representing a named role in the RBAC system.
@JsonSerializable()
class Role {
  final int id;
  final String name;

  const Role({
    required this.id,
    required this.name,
  });

  /// System roles are immutable: cannot be renamed or deleted.
  bool get isSystemRole =>
      name == 'owner' || name == 'admin' || name == 'user';

  factory Role.fromJson(Map<String, dynamic> json) => _$RoleFromJson(json);
  Map<String, dynamic> toJson() => _$RoleToJson(this);

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is Role && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => 'Role(id: $id, name: $name)';
}
