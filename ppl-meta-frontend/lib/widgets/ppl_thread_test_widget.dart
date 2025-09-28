import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:developer' as developer;

import '../providers/ppl_thread_providers.dart';

/// Simple test widget to debug PPL Thread service
class PPLThreadTestWidget extends ConsumerWidget {
  final String mediaId;

  const PPLThreadTestWidget({
    super.key,
    required this.mediaId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    developer.log('PPLThreadTestWidget build for mediaId: $mediaId', name: 'PPLThreadTest');
    
    final personCountAsync = ref.watch(personCountProvider(mediaId));

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.purple.withOpacity(0.1),
        border: Border.all(color: Colors.purple.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(2),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'PPL:',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.purple,
              fontSize: 8,
            ),
          ),
          const SizedBox(width: 2),
          personCountAsync.when(
            data: (personCount) {
              developer.log('PPL Thread TEST SUCCESS: personCount=$personCount for mediaId=$mediaId', name: 'PPLThreadTest');
              return Text(
                '$personCount',
                style: TextStyle(
                  color: Colors.green,
                  fontSize: 8,
                  fontWeight: FontWeight.w600,
                ),
              );
            },
            loading: () {
              developer.log('PPL Thread TEST LOADING for mediaId=$mediaId', name: 'PPLThreadTest');
              return SizedBox(
                width: 6,
                height: 6,
                child: CircularProgressIndicator(strokeWidth: 1),
              );
            },
            error: (error, stack) {
              developer.log('PPL Thread TEST ERROR for mediaId=$mediaId: $error', name: 'PPLThreadTest', error: error, stackTrace: stack);
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