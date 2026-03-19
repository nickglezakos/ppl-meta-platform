import 'package:flutter/material.dart';
import '../../services/developer_settings_service.dart';

/// Developer & Marketing Settings Page
/// Controls features like screenshot capture for marketing purposes
class DeveloperSettingsPage extends StatefulWidget {
  const DeveloperSettingsPage({Key? key}) : super(key: key);

  @override
  State<DeveloperSettingsPage> createState() => _DeveloperSettingsPageState();
}

class _DeveloperSettingsPageState extends State<DeveloperSettingsPage> {
  final DeveloperSettingsService _devSettings = DeveloperSettingsService();

  @override
  void initState() {
    super.initState();
    _devSettings.initialize();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Developer Settings'),
        backgroundColor: Colors.deepPurple,
      ),
      body: ListenableBuilder(
        listenable: _devSettings,
        builder: (context, child) {
          if (!_devSettings.isInitialized) {
            return const Center(child: CircularProgressIndicator());
          }

          return ListView(
            children: [
              // Header Section
              Container(
                padding: const EdgeInsets.all(16),
                color: Colors.deepPurple.withOpacity(0.1),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: const [
                        Icon(Icons.developer_mode, size: 32, color: Colors.deepPurple),
                        SizedBox(width: 12),
                        Text(
                          'Developer & Marketing Tools',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Enable features for creating marketing materials and documentation',
                      style: TextStyle(
                        color: Colors.grey[600],
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Screenshot Settings Section
              _buildSectionHeader('Screenshot Tools'),
              
              SwitchListTile(
                title: const Text('Screenshot Capture Button'),
                subtitle: const Text(
                  'Show floating camera button to capture app screenshots for marketing',
                ),
                value: _devSettings.screenshotFabEnabled,
                onChanged: (value) async {
                  await _devSettings.setScreenshotFabEnabled(value);
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          value
                              ? '📸 Screenshot button enabled - Look for camera icon'
                              : '📸 Screenshot button disabled',
                        ),
                        duration: const Duration(seconds: 2),
                      ),
                    );
                  }
                },
                secondary: const Icon(Icons.camera_alt, color: Colors.blue),
              ),

              if (_devSettings.screenshotFabEnabled) ...[
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Card(
                    color: Colors.blue.withOpacity(0.1),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          Icon(Icons.info_outline, color: Colors.blue[700], size: 20),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'A camera button will appear on pages that support screenshots. '
                              'Click it to save screenshots to docs/screenshots/',
                              style: TextStyle(fontSize: 12, color: Colors.blue[900]),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],

              const Divider(height: 32),

              // Info Section
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'About Developer Settings',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey[700],
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'These settings are intended for creating marketing materials, '
                      'documentation screenshots, and development purposes. '
                      'Disable them after your marketing cycle to keep the interface clean.',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Icon(Icons.save_alt, size: 16, color: Colors.grey[600]),
                        const SizedBox(width: 8),
                        Text(
                          'Settings are saved automatically',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: Colors.grey[700],
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
