import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:developer' as developer;

import '../providers/ppl_thread_providers.dart';

/// Enhanced PPL Thread widget using Enhanced Logic V2
/// 
/// This widget now uses the simplified PPL Thread endpoint that:
/// 1. Calls Enhanced Logic V2 for face detection
/// 2. Applies backend grouping logic 
/// 3. Returns calculated person count (not just face count)
class PPLThreadTestWidget extends ConsumerWidget {
  final String mediaId;

  const PPLThreadTestWidget({
    super.key,
    required this.mediaId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    developer.log('PPLThreadTestWidget (Enhanced V2) build for mediaId: $mediaId', name: 'PPLThreadTest');
    
    final personCountAsync = ref.watch(personCountProvider(mediaId));

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.green.withOpacity(0.1), // Changed to green to indicate Enhanced Logic V2
        border: Border.all(color: Colors.green.withOpacity(0.4)),
        borderRadius: BorderRadius.circular(2),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'PPL V2:', // Updated label to indicate Enhanced Logic V2
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.green.shade700,
              fontSize: 8,
            ),
          ),
          const SizedBox(width: 2),
          personCountAsync.when(
            data: (personCount) {
              developer.log('PPL Thread Enhanced V2 SUCCESS: personCount=$personCount for mediaId=$mediaId', name: 'PPLThreadTest');
              return Text(
                '$personCount',
                style: TextStyle(
                  color: Colors.green.shade800,
                  fontSize: 8,
                  fontWeight: FontWeight.w600,
                ),
              );
            },
            loading: () {
              developer.log('PPL Thread Enhanced V2 LOADING for mediaId=$mediaId', name: 'PPLThreadTest');
              return SizedBox(
                width: 6,
                height: 6,
                child: CircularProgressIndicator(strokeWidth: 1, color: Colors.green),
              );
            },
            error: (error, stack) {
              developer.log('PPL Thread Enhanced V2 ERROR for mediaId=$mediaId: $error', name: 'PPLThreadTest', error: error, stackTrace: stack);
              return Text(
                'ERR',
                style: TextStyle(
                  color: Colors.red,
                  fontSize: 8,
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}