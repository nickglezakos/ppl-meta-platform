import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'features/connection/screens/connection_screen.dart';
import 'services/app_logger.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize logging system
  await AppLogger.instance.initialize();
  AppLogger.instance.info('🚀 PPL Meta Mobile Camera streaming app starting...');
  
  runApp(const PPLMetaMobileCameraApp());
}

class PPLMetaMobileCameraApp extends StatelessWidget {
  const PPLMetaMobileCameraApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PPL Meta Mobile Camera',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.blue,
          foregroundColor: Colors.white,
          systemOverlayStyle: SystemUiOverlayStyle.light,
        ),
      ),
      home: const ConnectionScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
