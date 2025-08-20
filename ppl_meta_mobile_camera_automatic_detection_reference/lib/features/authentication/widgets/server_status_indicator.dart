import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/core.dart';

/// Widget that displays the current server connection status
class ServerStatusIndicator extends StatelessWidget {
  const ServerStatusIndicator({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthenticationProvider>(
      builder: (context, authProvider, child) {
        if (authProvider.serverUrl == null) {
          return const SizedBox.shrink();
        }

        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          margin: const EdgeInsets.only(bottom: 16),
          decoration: BoxDecoration(
            color: _getStatusColor(authProvider.isServerOnline, context),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: _getStatusBorderColor(authProvider.isServerOnline, context),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              // Status Icon
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: _getStatusIconColor(authProvider.isServerOnline),
                  shape: BoxShape.circle,
                ),
              ),
              
              const SizedBox(width: 12),
              
              // Status Text
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _getStatusText(authProvider.isServerOnline),
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: _getStatusTextColor(authProvider.isServerOnline, context),
                      ),
                    ),
                    if (authProvider.serverUrl != null)
                      Text(
                        _formatServerUrl(authProvider.serverUrl!),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: _getStatusTextColor(authProvider.isServerOnline, context)
                              .withOpacity(0.8),
                        ),
                      ),
                  ],
                ),
              ),
              
              // Action Button
              if (!authProvider.isServerOnline)
                IconButton(
                  onPressed: () => _retryConnection(context, authProvider),
                  icon: Icon(
                    Icons.refresh,
                    color: _getStatusTextColor(authProvider.isServerOnline, context),
                    size: 20,
                  ),
                  tooltip: 'Retry connection',
                ),
              
              // Info Button
              IconButton(
                onPressed: () => _showServerInfo(context, authProvider),
                icon: Icon(
                  Icons.info_outline,
                  color: _getStatusTextColor(authProvider.isServerOnline, context),
                  size: 20,
                ),
                tooltip: 'Server information',
              ),
            ],
          ),
        );
      },
    );
  }

  Color _getStatusColor(bool isOnline, BuildContext context) {
    if (isOnline) {
      return Colors.green.withOpacity(0.1);
    } else {
      return Theme.of(context).colorScheme.errorContainer;
    }
  }

  Color _getStatusBorderColor(bool isOnline, BuildContext context) {
    if (isOnline) {
      return Colors.green.withOpacity(0.3);
    } else {
      return Theme.of(context).colorScheme.error.withOpacity(0.3);
    }
  }

  Color _getStatusIconColor(bool isOnline) {
    return isOnline ? Colors.green : Colors.red;
  }

  Color _getStatusTextColor(bool isOnline, BuildContext context) {
    if (isOnline) {
      return Colors.green.shade700;
    } else {
      return Theme.of(context).colorScheme.onErrorContainer;
    }
  }

  String _getStatusText(bool isOnline) {
    return isOnline ? 'Server Online' : 'Server Offline';
  }

  String _formatServerUrl(String url) {
    try {
      final uri = Uri.parse(url);
      return uri.host;
    } catch (e) {
      return url;
    }
  }

  Future<void> _retryConnection(
    BuildContext context,
    AuthenticationProvider authProvider,
  ) async {
    if (authProvider.serverUrl != null) {
      await authProvider.checkServerConnection(authProvider.serverUrl!);
    }
  }

  void _showServerInfo(
    BuildContext context,
    AuthenticationProvider authProvider,
  ) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Server Information'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildInfoRow(
                'Status',
                authProvider.isServerOnline ? 'Online' : 'Offline',
                authProvider.isServerOnline ? Colors.green : Colors.red,
              ),
              _buildInfoRow('URL', authProvider.serverUrl ?? 'Not set'),
              
              if (authProvider.serverInfo != null) ...[
                const SizedBox(height: 16),
                Text(
                  'Server Details',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                
                if (authProvider.serverInfo!['name'] != null)
                  _buildInfoRow('Name', authProvider.serverInfo!['name']),
                
                if (authProvider.serverInfo!['version'] != null)
                  _buildInfoRow('Version', authProvider.serverInfo!['version']),
                
                if (authProvider.serverInfo!['status'] != null)
                  _buildInfoRow('Health', authProvider.serverInfo!['status']),
                
                if (authProvider.serverInfo!['timestamp'] != null)
                  _buildInfoRow(
                    'Last Check',
                    _formatTimestamp(authProvider.serverInfo!['timestamp']),
                  ),
              ],
              
              if (authProvider.error != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Connection Error',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: Theme.of(context).colorScheme.onErrorContainer,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        authProvider.error!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onErrorContainer,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        actions: [
          if (!authProvider.isServerOnline)
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _retryConnection(context, authProvider);
              },
              child: const Text('Retry'),
            ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, [Color? valueColor]) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(color: valueColor),
            ),
          ),
        ],
      ),
    );
  }

  String _formatTimestamp(dynamic timestamp) {
    try {
      if (timestamp is String) {
        final dateTime = DateTime.parse(timestamp);
        return '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
      }
      return timestamp.toString();
    } catch (e) {
      return 'Invalid';
    }
  }
}
