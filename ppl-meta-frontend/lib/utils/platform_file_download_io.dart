import 'dart:io';

import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';

Future<String?> downloadFileBytes({
  required List<int> bytes,
  required String filename,
  String mimeType = 'application/octet-stream',
}) async {
  final directory = await getApplicationDocumentsDirectory();
  final filePath = path.join(directory.path, filename);
  final file = File(filePath);
  await file.writeAsBytes(bytes, flush: true);
  return file.path;
}
