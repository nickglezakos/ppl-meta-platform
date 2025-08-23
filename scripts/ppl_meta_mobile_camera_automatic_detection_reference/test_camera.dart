import 'package:camera/camera.dart';

void main() async {
  final cameras = await availableCameras();
  print('Cameras: ${cameras.length}');
}
