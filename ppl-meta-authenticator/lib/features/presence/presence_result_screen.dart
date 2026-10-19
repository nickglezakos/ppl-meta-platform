import 'package:flutter/material.dart';

import '../../data/presence_authenticator_api.dart';

class PresenceResultScreen extends StatelessWidget {
  const PresenceResultScreen({super.key, required this.result});

  final PresenceResultSummary result;

  @override
  Widget build(BuildContext context) {
    final granted = result.isGranted;
    return Scaffold(
      appBar: AppBar(title: const Text('Presence result')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Icon(
              granted ? Icons.check_circle : Icons.cancel,
              size: 72,
              color: granted
                  ? Colors.green
                  : Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              granted ? 'Presence granted' : 'Presence ${result.decision}',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              result.reasonCode,
              textAlign: TextAlign.center,
            ),
            if (result.matchedMemberName != null) ...[
              const SizedBox(height: 8),
              Text(
                result.matchedMemberName!,
                textAlign: TextAlign.center,
              ),
            ],
            const Spacer(),
            FilledButton(
              onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
              child: const Text('Done'),
            ),
          ],
        ),
      ),
    );
  }
}
