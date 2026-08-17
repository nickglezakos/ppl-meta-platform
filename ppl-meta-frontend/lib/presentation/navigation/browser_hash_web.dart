/// Web implementation: reads the real browser location hash.
library;

// web-only by design — this file is only resolved under dart.library.html.
// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:html' as html;

String windowLocationHash() => html.window.location.hash;
