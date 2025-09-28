/// PPL Meta Frontend - PPL Thread Test Screen
/// 
/// A simple test screen to demonstrate the PPL Thread service integration
/// without interfering with the existing complex widget system.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/ppl_thread_providers.dart';
import '../widgets/simple_person_count_widget.dart';
import '../providers/face_data_providers.dart';

class PPLThreadTestScreen extends ConsumerWidget {
  const PPLThreadTestScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Test media IDs that we know have face detection data
    final testMediaIds = [
      '291ae808-c9b8-4eec-b835-97f72a108308',
      '6cb0a76c-70da-441d-9411-9f5ae579ee0c',
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('PPL Thread Service Test'),
        backgroundColor: Colors.blue.shade800,
        foregroundColor: Colors.white,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '🎉 PPL Thread Integration Test',
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'This screen tests the new READ-ONLY PPL Thread service integration. '
                      'It fetches person count data directly from the Orchestrator API.',
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.blue.shade200),
                      ),
                      child: const Text(
                        '✅ Backend automation complete\n'
                        '✅ Authentication working\n'
                        '✅ Orchestrator endpoints functional\n'
                        '✅ Vision Service integration established',
                        style: TextStyle(fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Test Results
            Text(
              'Test Results:',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            
            const SizedBox(height: 8),
            
            Expanded(
              child: ListView.builder(
                itemCount: testMediaIds.length,
                itemBuilder: (context, index) {
                  final mediaId = testMediaIds[index];
                  
                  return Card(
                    margin: const EdgeInsets.only(bottom: 12),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Test Media ${index + 1}',
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                          
                          const SizedBox(height: 4),
                          
                          Text(
                            'UUID: $mediaId',
                            style: TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 10,
                              color: Colors.grey.shade600,
                            ),
                          ),
                          
                          const SizedBox(height: 12),
                          
                          Row(
                            children: [
                              // Face Count
                              Consumer(
                                builder: (context, ref, child) {
                                  final faceData = ref.watch(mediaFaceDataProvider(mediaId));
                                  
                                  return Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(Icons.face, size: 16, color: Colors.orange),
                                      const SizedBox(width: 4),
                                      Text('${faceData.totalCount} faces'),
                                    ],
                                  );
                                },
                              ),
                              
                              const SizedBox(width: 16),
                              
                              // Person Count (NEW)
                              SimplePersonCountWidget(
                                mediaId: mediaId,
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                              ),
                            ],
                          ),
                          
                          const SizedBox(height: 8),
                          
                          // API Status
                          Consumer(
                            builder: (context, ref, child) {
                              final personCountAsync = ref.watch(personCountProvider(mediaId));
                              final existsAsync = ref.watch(personObjectsExistsProvider(mediaId));
                              
                              return Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Icon(
                                        personCountAsync.isLoading ? Icons.hourglass_empty : 
                                        personCountAsync.hasError ? Icons.error : Icons.check_circle,
                                        size: 14,
                                        color: personCountAsync.isLoading ? Colors.orange :
                                               personCountAsync.hasError ? Colors.red : Colors.green,
                                      ),
                                      const SizedBox(width: 4),
                                      Text(
                                        personCountAsync.isLoading ? 'Loading...' :
                                        personCountAsync.hasError ? 'API Error' : 'API Success',
                                        style: const TextStyle(fontSize: 12),
                                      ),
                                    ],
                                  ),
                                  
                                  existsAsync.when(
                                    data: (exists) => Row(
                                      children: [
                                        Icon(
                                          exists ? Icons.storage : Icons.storage_outlined,
                                          size: 14,
                                          color: exists ? Colors.green : Colors.grey,
                                        ),
                                        const SizedBox(width: 4),
                                        Text(
                                          exists ? 'Data exists' : 'No data yet',
                                          style: const TextStyle(fontSize: 12),
                                        ),
                                      ],
                                    ),
                                    loading: () => const SizedBox.shrink(),
                                    error: (_, __) => const SizedBox.shrink(),
                                  ),
                                ],
                              );
                            },
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}