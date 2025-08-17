// Web download helper
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;

void downloadFileWeb(List<int> bytes, String filename) {
  // Create a blob from the bytes
  final blob = html.Blob([bytes]);
  final url = html.Url.createObjectUrlFromBlob(blob);
  
  // Create a temporary anchor element and trigger download
  final anchor = html.AnchorElement(href: url)
    ..setAttribute('download', filename)
    ..style.display = 'none';
  
  html.document.body?.children.add(anchor);
  anchor.click();
  html.document.body?.children.remove(anchor);
  html.Url.revokeObjectUrl(url);
}
