import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

/// A simple test page for the face detection API integration
class FaceDetectionTestPage extends StatefulWidget {
  const FaceDetectionTestPage({super.key});

  @override
  State<FaceDetectionTestPage> createState() => _FaceDetectionTestPageState();
}

class _FaceDetectionTestPageState extends State<FaceDetectionTestPage> {
  final String baseUrl = 'http://localhost:8002';
  final String authToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmcmVzaC51c2VyQGV4YW1wbGUuY29tIiwidXNlcl9pZCI6IjQ5ZTA5NDhkLTMzNGItNDY0NC1hNzIyLWQ1Yzc0ZWNiNjJhYyIsImV4cCI6MTc1OTc3NjQ2N30.rO7MX3_qWa3xPYagq-zMTvUCe6CbCTRWMDaHn5d3nojbLE';
  
  List<Map<String, dynamic>> sessions = [];
  bool loading = false;
  String? error;
  String? selectedMediaId;

  final List<Map<String, String>> testMedia = [
    {
      'id': '87eff63e-9a5a-4c5e-b1e8-0f033cff5658',
      'name': 'Large Media (190+ faces)',
    },
    {
      'id': '436b948c-8b5a-4c5e-b1e8-0f033cff5658', 
      'name': 'Small Media (0 faces)',
    },
  ];

  @override
  void initState() {
    super.initState();
    loadSessions();
  }

  Future<void> loadSessions() async {
    setState(() {
      loading = true;
      error = null;
    });

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/sessions'),
        headers: {
          'Authorization': 'Bearer $authToken',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as List;
        setState(() {
          sessions = data.cast<Map<String, dynamic>>();
          loading = false;
        });
      } else {
        setState(() {
          error = 'Failed to load sessions: ${response.statusCode}';
          loading = false;
        });
      }
    } catch (e) {
      setState(() {
        error = 'Network error: $e';
        loading = false;
      });
    }
  }

  Future<void> createSession(String mediaId) async {
    setState(() {
      loading = true;
      error = null;
    });

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/face-detection'),
        headers: {
          'Authorization': 'Bearer $authToken',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'media_id': mediaId,
          'detection_method': 'two_stage_haar_dlib',
          'confidence_threshold': 0.5,
        }),
      );

      if (response.statusCode == 200) {
        await loadSessions();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Face detection session created!')),
          );
        }
      } else {
        setState(() {
          error = 'Failed to create session: ${response.statusCode}';
          loading = false;
        });
      }
    } catch (e) {
      setState(() {
        error = 'Network error: $e';
        loading = false;
      });
    }
  }

  Future<void> getMediaFaces(String mediaId) async {
    setState(() {
      loading = true;
      error = null;
    });

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/media/$mediaId/faces'),
        headers: {
          'Authorization': 'Bearer $authToken',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          loading = false;
        });
        
        if (mounted) {
          showDialog(
            context: context,
            builder: (context) => AlertDialog(
              title: Text('Media Faces: $mediaId'),
              content: SingleChildScrollView(
                child: Text(
                  const JsonEncoder.withIndent('  ').convert(data),
                  style: const TextStyle(fontFamily: 'monospace'),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Close'),
                ),
              ],
            ),
          );
        }
      } else {
        setState(() {
          error = 'Failed to get media faces: ${response.statusCode}';
          loading = false;
        });
      }
    } catch (e) {
      setState(() {
        error = 'Network error: $e';
        loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Face Detection API Test'),
        backgroundColor: Colors.blue.shade700,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: loadSessions,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Test Media Section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Test Media',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 12),
                    ...testMedia.map((media) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  media['name']!,
                                  style: const TextStyle(fontWeight: FontWeight.bold),
                                ),
                                Text(
                                  media['id']!,
                                  style: TextStyle(
                                    fontFamily: 'monospace',
                                    fontSize: 12,
                                    color: Colors.grey.shade600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          ElevatedButton(
                            onPressed: loading ? null : () => createSession(media['id']!),
                            child: const Text('Create Session'),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: loading ? null : () => getMediaFaces(media['id']!),
                            child: const Text('Get Faces'),
                          ),
                        ],
                      ),
                    )),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Error Display
            if (error != null)
              Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      Icon(Icons.error, color: Colors.red.shade700),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          error!,
                          style: TextStyle(color: Colors.red.shade700),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            const SizedBox(height: 16),

            // Sessions List
            Expanded(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            'Face Detection Sessions',
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const Spacer(),
                          if (loading) const CircularProgressIndicator(),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Expanded(
                        child: sessions.isEmpty
                            ? const Center(
                                child: Text('No sessions found. Create one to get started!'),
                              )
                            : ListView.builder(
                                itemCount: sessions.length,
                                itemBuilder: (context, index) {
                                  final session = sessions[index];
                                  return Card(
                                    margin: const EdgeInsets.symmetric(vertical: 4),
                                    child: ListTile(
                                      title: Text(
                                        'Session: ${session['session_id'] ?? session['sessionId'] ?? 'Unknown'}',
                                        style: const TextStyle(fontFamily: 'monospace'),
                                      ),
                                      subtitle: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text('Media: ${session['media_id'] ?? session['mediaId'] ?? 'Unknown'}'),
                                          Text('Status: ${session['status'] ?? 'Unknown'}'),
                                          if (session['result'] != null)
                                            Text('Total Faces: ${session['result']['total_faces'] ?? 'N/A'}'),
                                        ],
                                      ),
                                      trailing: Icon(
                                        session['status'] == 'completed'
                                            ? Icons.check_circle
                                            : session['status'] == 'pending'
                                                ? Icons.pending
                                                : Icons.error,
                                        color: session['status'] == 'completed'
                                            ? Colors.green
                                            : session['status'] == 'pending'
                                                ? Colors.orange
                                                : Colors.red,
                                      ),
                                      onTap: () {
                                        showDialog(
                                          context: context,
                                          builder: (context) => AlertDialog(
                                            title: const Text('Session Details'),
                                            content: SingleChildScrollView(
                                              child: Text(
                                                const JsonEncoder.withIndent('  ').convert(session),
                                                style: const TextStyle(fontFamily: 'monospace'),
                                              ),
                                            ),
                                            actions: [
                                              TextButton(
                                                onPressed: () => Navigator.of(context).pop(),
                                                child: const Text('Close'),
                                              ),
                                            ],
                                          ),
                                        );
                                      },
                                    ),
                                  );
                                },
                              ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}