import 'package:flutter/material.dart';

void main() {
  runApp(const SimplePPLMetaApp());
}

class SimplePPLMetaApp extends StatelessWidget {
  const SimplePPLMetaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Eyenet Vision - Simple Test',
      theme: ThemeData.dark(useMaterial3: true),
      home: const SimpleHomePage(),
    );
  }
}

class SimpleHomePage extends StatelessWidget {
  const SimpleHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Eyenet Vision'),
      ),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Eyenet Vision',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 16),
            Text('Platform is loading...'),
          ],
        ),
      ),
    );
  }
}
