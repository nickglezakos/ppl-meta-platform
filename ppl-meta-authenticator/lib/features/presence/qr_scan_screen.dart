import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class QrScanScreen extends StatefulWidget {
  const QrScanScreen({super.key, this.title = 'Scan station QR'});

  final String title;

  @override
  State<QrScanScreen> createState() => _QrScanScreenState();
}

class _QrScanScreenState extends State<QrScanScreen> {
  bool _done = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Column(
        children: [
          const Padding(
            padding: EdgeInsets.all(12),
            child: Text('Point the back camera at the station Presence QR.'),
          ),
          Expanded(
            child: MobileScanner(
              onDetect: (capture) {
                if (_done) return;
                String? raw;
                for (final barcode in capture.barcodes) {
                  final value = barcode.rawValue;
                  if (value != null && value.isNotEmpty) {
                    raw = value;
                    break;
                  }
                }
                if (raw == null) return;
                _done = true;
                Navigator.of(context).pop(raw);
              },
            ),
          ),
        ],
      ),
    );
  }
}
