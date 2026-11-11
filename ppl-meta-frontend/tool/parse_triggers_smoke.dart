import 'dart:convert';
import 'dart:io';
import 'package:ppl_meta_frontend/models/trigger_model.dart';

void main() {
  final raw = File('/tmp/triggers.json').readAsStringSync();
  final decoded = jsonDecode(raw);
  print('top keys=${(decoded as Map).keys.toList()}');
  try {
    final list = TriggerListResponse.fromJson(
      Map<String, dynamic>.from(decoded as Map),
    );
    print('OK count=${list.triggers.length}');
    for (final t in list.triggers) {
      print('- ${t.triggerMode} | ${t.name} | lookback=${t.behaviouralLookbackFlushes} | lastMatch=${t.lastMatchInfo != null}');
    }
  } catch (e, st) {
    print('FAIL: $e');
    print(st);
  }
}
