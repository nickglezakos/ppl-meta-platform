import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/providers/users_provider.dart';
import '../../../core/providers/roles_provider.dart';
import '../../../core/models/user.dart';
import '../../../core/models/role.dart';
import '../../../widgets/custom_app_bar.dart';

class UsersScreen extends ConsumerStatefulWidget {
  const UsersScreen({super.key});

  @override
  ConsumerState<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends ConsumerState<UsersScreen> {
  String _activeRoleFilter = 'All';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(usersNotifierProvider.notifier).loadUsers();
      ref.read(rolesNotifierProvider.notifier).loadRoles();
    });
  }

  @override
  Widget build(BuildContext context) {
    final usersState = ref.watch(usersNotifierProvider);

    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Users',
      ),
      body: _buildBody(usersState),
    );
  }

  Widget _buildBody(UsersState state) {
    if (state.isLoading && state.users.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading users...'),
          ],
        ),
      );
    }

    if (state.error != null && state.users.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Failed to load users',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              state.error!,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.error,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => ref.read(usersNotifierProvider.notifier).loadUsers(),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.users.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.people_outline,
              size: 64,
              color: Colors.grey,
            ),
            SizedBox(height: 16),
            Text(
              'No users found',
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey,
              ),
            ),
          ],
        ),
      );
    }

    final filteredUsers = _filteredUsers(state.users);
    return Column(
      children: [
        // Role filter chips
        _buildRoleFilterChips(),
        // Header with user count
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
          child: Row(
            children: [
              Icon(
                Icons.people,
                color: Theme.of(context).primaryColor,
              ),
              const SizedBox(width: 8),
              Text(
                '${state.users.length} ${state.users.length == 1 ? 'User' : 'Users'}',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              if (state.isLoading)
                const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
        ),
        
        // Users list
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(8),
            itemCount: filteredUsers.length,
            itemBuilder: (context, index) {
              final user = filteredUsers[index];
              return _UserCard(user: user, getRoleColor: _getRoleColor);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildRoleFilterChips() {
    final rolesState = ref.watch(rolesNotifierProvider);
    final roles = rolesState.roles;
    final roleNames = ['All', ...roles.map((r) => r.name)];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: roleNames.map((name) {
            final isActive = _activeRoleFilter == name;
            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: FilterChip(
                label: Text(name),
                selected: isActive,
                onSelected: (selected) {
                  setState(() => _activeRoleFilter = selected ? name : 'All');
                },
                backgroundColor: Colors.grey[200],
                selectedColor: _getRoleColor(name).withOpacity(0.2),
                labelStyle: TextStyle(
                  color: isActive ? _getRoleColor(name) : Colors.grey[700],
                  fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  List<User> _filteredUsers(List<User> users) {
    if (_activeRoleFilter == 'All') return users;
    return users.where((u) => u.roles.contains(_activeRoleFilter)).toList();
  }

  Color _getRoleColor(String role) {
    switch (role) {
      case 'owner': return Colors.amber.shade800;
      case 'admin': return Colors.deepPurple;
      case 'user': return Colors.blue;
      default: return Colors.teal;
    }
  }
}

class _UserCard extends StatelessWidget {
  final User user;
  final Color Function(String) getRoleColor;

  const _UserCard({required this.user, required this.getRoleColor});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => context.go('/profile?userId=${user.id}'),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              CircleAvatar(
                radius: 24,
                backgroundColor: Colors.teal.withOpacity(0.2),
                child: Text(
                  (user.username.isNotEmpty ? user.username[0] : '?').toUpperCase(),
                  style: const TextStyle(
                    color: Colors.teal,
                    fontWeight: FontWeight.bold,
                    fontSize: 18,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(user.username, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    Text(user.email, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey[600])),
                    const SizedBox(height: 6),
                    if (user.roles.isNotEmpty)
                      Wrap(
                        spacing: 4,
                        runSpacing: 4,
                        children: user.roles.map((role) {
                          final color = getRoleColor(role);
                          return Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(8)),
                            child: Text(role, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
                          );
                        }).toList(),
                      ),
                    const SizedBox(height: 2),
                    Text('${user.capabilities.length} capabilities',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey[500])),
                  ],
                ),
              ),
              Column(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: user.emailVerified ? Colors.green.withOpacity(0.2) : Colors.orange.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(user.emailVerified ? 'Verified' : 'Unverified',
                      style: TextStyle(color: user.emailVerified ? Colors.green[700] : Colors.orange[700], fontSize: 11, fontWeight: FontWeight.w500)),
                  ),
                  const SizedBox(height: 4),
                  const Icon(Icons.chevron_right, color: Colors.grey),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
