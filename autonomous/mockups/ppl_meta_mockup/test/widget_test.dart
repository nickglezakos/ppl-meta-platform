import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ppl_meta_mockup/main.dart';
import 'package:ppl_meta_mockup/models/mock_data.dart';

void main() {
  testWidgets('launcher lists all four resources', (tester) async {
    await tester.pumpWidget(const PplMetaMockupApp());
    for (final r in kResources.values) {
      expect(find.text(r.name), findsWidgets);
    }
  });

  testWidgets('opening a resource shows the unified resource home', (tester) async {
    await tester.pumpWidget(const PplMetaMockupApp());
    await tester.tap(find.text('Cameras'));
    await tester.pumpAndSettle();

    // Unified toolbar actions present on the resource home.
    expect(find.text('Cameras'), findsWidgets);
    expect(find.byIcon(Icons.search), findsOneWidget);
    expect(find.byIcon(Icons.filter_list), findsOneWidget);

    // A fake item is visible.
    expect(find.text('Lobby — Entrance'), findsWidgets);
  });
}
