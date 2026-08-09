import 'package:dio/dio.dart';
import '../models/role.dart';
import '../models/capability.dart';
import '../api/api_client.dart';

/// Service for role-related API calls to the EyeNet Node backend.
class RolesService {
  final ApiClient _apiClient;

  RolesService(this._apiClient);

  // ── CRUD ──────────────────────────────────────────────────────

  /// Get list of all roles
  Future<List<Role>> getRoles() async {
    try {
      final response = await _apiClient.get<List<dynamic>>('/roles/');

      if (response.data == null) {
        throw Exception('No data received from server');
      }

      return response.data!
          .map((json) => Role.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Get a single role by ID
  Future<Role> getRoleById(int roleId) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/roles/$roleId',
      );

      if (response.data == null) {
        throw Exception('Role not found');
      }

      return Role.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Get a single role by name
  Future<Role> getRoleByName(String name) async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/roles/by-name/$name',
      );

      if (response.data == null) {
        throw Exception('Role not found');
      }

      return Role.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Create a new role
  Future<Role> createRole(String name) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/roles/',
        data: {'name': name},
      );

      if (response.data == null) {
        throw Exception('Failed to create role');
      }

      return Role.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Update a role's name
  Future<Role> updateRole(int roleId, String newName) async {
    try {
      final response = await _apiClient.put<Map<String, dynamic>>(
        '/roles/$roleId',
        data: {'name': newName},
      );

      if (response.data == null) {
        throw Exception('Failed to update role');
      }

      return Role.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Delete a role
  Future<void> deleteRole(int roleId) async {
    try {
      await _apiClient.delete('/roles/$roleId');
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  // ── User-Role Assignment ─────────────────────────────────────

  /// Assign a role to a user
  Future<void> assignRoleToUser(int userId, int roleId) async {
    try {
      await _apiClient.post(
        '/roles/assign/',
        queryParameters: {'user_id': userId, 'role_id': roleId},
      );
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Unassign a role from a user
  Future<void> unassignRoleFromUser(int userId, int roleId) async {
    try {
      await _apiClient.post(
        '/roles/unassign/',
        queryParameters: {'user_id': userId, 'role_id': roleId},
      );
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  // ── Role-Capability Assignment ───────────────────────────────

  /// Add a capability to a role
  Future<void> addCapabilityToRole(int roleId, int capabilityId) async {
    try {
      await _apiClient.post(
        '/roles/add-capability/',
        data: {'role_id': roleId, 'capability_id': capabilityId},
      );
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  /// Remove a capability from a role
  Future<void> removeCapabilityFromRole(int roleId, int capabilityId) async {
    try {
      await _apiClient.post(
        '/roles/remove-capability/',
        data: {'role_id': roleId, 'capability_id': capabilityId},
      );
    } on DioException catch (e) {
      throw _handleError(e);
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  // ── Helpers ──────────────────────────────────────────────────

  Exception _handleError(DioException e) {
    if (e.response?.statusCode == 401) {
      return Exception('Authentication required. Please log in again.');
    } else if (e.response?.statusCode == 403) {
      return Exception('Access denied. Insufficient permissions.');
    } else if (e.response?.statusCode == 404) {
      return Exception('Role not found.');
    } else if (e.response?.statusCode == 400) {
      final detail = (e.response?.data as Map?)?['detail']?.toString() ??
          'Bad request';
      return Exception(detail);
    } else if (e.type == DioExceptionType.connectionTimeout) {
      return Exception('Connection timeout. Please check your connection.');
    } else {
      return Exception('Failed: ${e.message}');
    }
  }
}
