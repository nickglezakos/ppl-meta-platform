/// Platform-safe access to the browser location hash.
///
/// `dart:html` is web-only, so a direct import breaks Android/iOS builds.
/// This facade dispatches to a web implementation (reads `window.location.hash`)
/// or a stub (returns `''`) depending on the platform.
library;

import 'browser_hash_stub.dart'
    if (dart.library.html) 'browser_hash_web.dart' as impl;

/// Returns the current browser location hash fragment, or `''` on
/// non-web platforms (where there is no `window.location`).
String windowLocationHash() => impl.windowLocationHash();
