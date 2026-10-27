import 'package:flutter_test/flutter_test.dart';
import 'package:signage_simple_player/services/desktop_window_service.dart';

void main() {
  late DesktopWindowService service;

  setUp(() {
    DesktopWindowService.exitProcessOnQuit = false;
    DesktopWindowService.enableProcessCalls = false;
    service = DesktopWindowService();
    service.resetForTest();
  });

  test('quit increments counter without exiting when disabled', () async {
    await service.quit();
    expect(service.quitCallCount, 1);
    await service.quit();
    expect(service.quitCallCount, 2);
  });

  test('toggleFullscreen increments counter', () async {
    await service.toggleFullscreen();
    expect(service.toggleFullscreenCallCount, 1);
  });
}
