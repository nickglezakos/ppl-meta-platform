import 'package:flutter/material.dart';
import 'package:ppl_meta_mobile_camera/services/device_identifier_service.dart';
import 'package:ppl_meta_mobile_camera/services/auto_camera_registration_service.dart';

/// Demo application to test automatic camera naming system
void main() {
  runApp(AutomaticNamingDemoApp());
}

class AutomaticNamingDemoApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PPL Meta - Automatic Camera Naming Demo',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: AutomaticNamingDemoScreen(),
    );
  }
}

class AutomaticNamingDemoScreen extends StatefulWidget {
  @override
  _AutomaticNamingDemoScreenState createState() => _AutomaticNamingDemoScreenState();
}

class _AutomaticNamingDemoScreenState extends State<AutomaticNamingDemoScreen> {
  final DeviceIdentifierService _deviceService = DeviceIdentifierService();
  
  String? _generatedCameraName;
  String? _deviceDescription;
  Map<String, dynamic>? _deviceInfo;
  bool _isLoading = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Automatic Camera Naming Demo'),
        backgroundColor: Colors.blue.shade700,
        foregroundColor: Colors.white,
      ),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '🤖 Zero-Input Camera Registration',
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: Colors.blue.shade700,
                      ),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'This demo shows how the mobile camera app automatically generates unique camera names using device information, eliminating the need for user input.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(height: 16),
            
            ElevatedButton.icon(
              onPressed: _isLoading ? null : _generateAutomaticCameraName,
              icon: _isLoading 
                ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : Icon(Icons.auto_awesome),
              label: Text(_isLoading ? 'Generating...' : 'Generate Automatic Camera Name'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue.shade600,
                foregroundColor: Colors.white,
                padding: EdgeInsets.symmetric(vertical: 12),
              ),
            ),
            
            SizedBox(height: 24),
            
            if (_error != null) ...[
              Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.error, color: Colors.red),
                          SizedBox(width: 8),
                          Text('Error', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.red)),
                        ],
                      ),
                      SizedBox(height: 8),
                      Text(_error!, style: TextStyle(color: Colors.red.shade700)),
                    ],
                  ),
                ),
              ),
              SizedBox(height: 16),
            ],
            
            if (_generatedCameraName != null) ...[
              Card(
                color: Colors.green.shade50,
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.camera_alt, color: Colors.green),
                          SizedBox(width: 8),
                          Text('Generated Camera Name', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green.shade700)),
                        ],
                      ),
                      SizedBox(height: 8),
                      Container(
                        padding: EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.grey.shade100,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          _generatedCameraName!,
                          style: TextStyle(
                            fontFamily: 'monospace',
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: Colors.blue.shade700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              SizedBox(height: 16),
            ],
            
            if (_deviceDescription != null) ...[
              Card(
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.phone_android, color: Colors.blue),
                          SizedBox(width: 8),
                          Text('Device Description', style: TextStyle(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      SizedBox(height: 8),
                      Text(_deviceDescription!),
                    ],
                  ),
                ),
              ),
              SizedBox(height: 16),
            ],
            
            if (_deviceInfo != null) ...[
              Expanded(
                child: Card(
                  child: Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.info, color: Colors.orange),
                            SizedBox(width: 8),
                            Text('Device Registration Info', style: TextStyle(fontWeight: FontWeight.bold)),
                          ],
                        ),
                        SizedBox(height: 12),
                        Expanded(
                          child: ListView(
                            children: _deviceInfo!.entries.map((entry) {
                              return Padding(
                                padding: EdgeInsets.symmetric(vertical: 4),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    SizedBox(
                                      width: 120,
                                      child: Text(
                                        '${entry.key}:',
                                        style: TextStyle(fontWeight: FontWeight.w500),
                                      ),
                                    ),
                                    Expanded(
                                      child: Text(
                                        entry.value?.toString() ?? 'null',
                                        style: TextStyle(fontFamily: 'monospace'),
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            }).toList(),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
      floatingActionButton: _generatedCameraName != null 
        ? FloatingActionButton.extended(
            onPressed: _resetDemo,
            icon: Icon(Icons.refresh),
            label: Text('Reset Demo'),
            backgroundColor: Colors.orange,
            foregroundColor: Colors.white,
          )
        : null,
    );
  }

  Future<void> _generateAutomaticCameraName() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      print('🚀 Starting automatic camera name generation demo...');
      
      // Generate camera name
      final cameraName = await _deviceService.generateCameraName();
      print('✅ Generated camera name: $cameraName');
      
      // Get device description
      final description = await _deviceService.getDeviceDescription();
      print('✅ Device description: $description');
      
      // Get device registration info
      final deviceInfo = await _deviceService.getDeviceRegistrationInfo();
      print('✅ Device info collected with ${deviceInfo.keys.length} fields');
      
      setState(() {
        _generatedCameraName = cameraName;
        _deviceDescription = description;
        _deviceInfo = deviceInfo;
        _isLoading = false;
      });
      
      print('🎉 Automatic naming demo completed successfully!');
      
    } catch (e) {
      print('💥 Demo error: $e');
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _resetDemo() {
    setState(() {
      _generatedCameraName = null;
      _deviceDescription = null;
      _deviceInfo = null;
      _error = null;
    });
    
    // Clear the service cache to allow fresh generation
    _deviceService.clearCache();
    print('🔄 Demo reset - cache cleared');
  }
}
