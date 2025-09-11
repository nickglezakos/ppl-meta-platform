import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import '../../../widgets/camera/camera_card.dart';
import '../../../core/providers/camera_providers.dart';
import '../../../core/providers/multi_camera_providers.dart';
import '../../../core/models/camera.dart';
import 'package:go_router/go_router.dart';

/// Build responsive camera grid using StaggeredGridView:
/// - Mobile (< 600px): 1 column
/// - Tablet (600-1024px): 2 columns  
/// - Desktop (> 1024px): 2 columns
/// StaggeredGridView automatically handles different item heights
Widget buildResponsiveCameraGrid(List<dynamic> cameras) {
  return LayoutBuilder(
    builder: (context, constraints) {
      int crossAxisCount;
      
      if (constraints.maxWidth < 600) {
        // Mobile: 1 column
        crossAxisCount = 1;
      } else {
        // Tablet and Desktop: 2 columns
        crossAxisCount = 2;
      }

      return MasonryGridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: SliverSimpleGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: crossAxisCount,
        ),
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        itemCount: cameras.length,
        itemBuilder: (context, index) {
          final camera = cameras[index];
          return CameraCard(
            camera: camera,
            showStream: true, // Enable streaming like CAM-FLUTTER-005
          );
        },
      );
    },
  );
}

/// Multi-Camera Management Page with USB and RTSP support
/// Based on proven CAM-FLUTTER-005 implementation
class MultiCameraPage extends ConsumerStatefulWidget {
  const MultiCameraPage({super.key});

  @override
  ConsumerState<MultiCameraPage> createState() => _MultiCameraPageState();
}

class _MultiCameraPageState extends ConsumerState<MultiCameraPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    
    // Listen to tab changes to update FAB visibility
    _tabController.addListener(() {
      setState(() {});
    });
    
    // Load cameras when the page initializes using proven pattern
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(cameraListProvider.notifier).loadCameras();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cameraListState = ref.watch(cameraListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Multi-Camera Management'),
        centerTitle: true,
        elevation: 0,
        backgroundColor: Theme.of(context).colorScheme.surface,
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        leading: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () {
                if (context.canPop()) {
                  context.pop();
                } else {
                  context.go('/');
                }
              },
              tooltip: 'Back',
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.home),
            onPressed: () => context.go('/'),
            tooltip: 'Home',
          ),
          // Refresh cameras using proven pattern
          IconButton(
            onPressed: () => ref.read(cameraListProvider.notifier).loadCameras(),
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh cameras',
          ),
          const SizedBox(width: 8),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: Container(
            color: Theme.of(context).colorScheme.surface,
            child: TabBar(
              controller: _tabController,
              labelColor: Theme.of(context).colorScheme.primary,
              unselectedLabelColor: Theme.of(context).colorScheme.onSurfaceVariant,
              indicatorColor: Theme.of(context).colorScheme.primary,
              tabs: [
                Tab(
                  text: 'All Cameras (${cameraListState.cameras.length})',
                  icon: const Icon(Icons.videocam),
                ),
                Tab(
                  text: 'USB Cameras',
                  icon: const Icon(Icons.usb),
                ),
                Tab(
                  text: 'RTSP Cameras',
                  icon: const Icon(Icons.wifi),
                ),
              ],
            ),
          ),
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _AllCamerasTab(),
          _USBCamerasTab(),
          _RTSPCamerasTab(),
        ],
      ),
      floatingActionButton: _tabController.index == 2 ? FloatingActionButton.extended(
        onPressed: () => _showAddRTSPCameraDialog(context),
        icon: const Icon(Icons.add),
        label: const Text('Add RTSP Camera'),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Colors.white,
      ) : null,
    );
  }

  void _showAddRTSPCameraDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => _AddRTSPCameraDialog(),
    );
  }

}

/// All cameras tab using proven CAM-FLUTTER-005 pattern
class _AllCamerasTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cameraListState = ref.watch(cameraListProvider);

    return _buildCamerasContent(context, ref, cameraListState);
  }

  Widget _buildCamerasContent(BuildContext context, WidgetRef ref, dynamic cameraListState) {
    if (cameraListState.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    
    if (cameraListState.error != null) {
      return _buildErrorView(context, cameraListState.error.toString());
    }
    
    return _buildCamerasList(context, ref, cameraListState.cameras);
  }

  Widget _buildCamerasList(BuildContext context, WidgetRef ref, List<dynamic> cameras) {
    if (cameras.isEmpty) {
      return _buildEmptyState(context);
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.read(cameraListProvider.notifier).loadCameras();
      },
      child: buildResponsiveCameraGrid(cameras),
    );
  }

  Widget _buildErrorView(BuildContext context, String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: Theme.of(context).colorScheme.error,
          ),
          const SizedBox(height: 16),
          Text(
            'Failed to load cameras',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            error,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.videocam_off,
            size: 64,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            'No cameras found',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Connect cameras to get started',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

/// USB cameras tab using proven CAM-FLUTTER-005 pattern
class _USBCamerasTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cameraListState = ref.watch(cameraListProvider);
    
    // Filter for USB cameras
    final usbCameras = cameraListState.cameras
        .where((camera) => camera.type == CameraType.usb)
        .toList();

    return _buildCamerasList(context, ref, usbCameras);
  }

  Widget _buildCamerasList(BuildContext context, WidgetRef ref, List<dynamic> cameras) {
    if (cameras.isEmpty) {
      return _buildEmptyState(context, 'No USB cameras found');
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.read(cameraListProvider.notifier).loadCameras();
      },
      child: buildResponsiveCameraGrid(cameras),
    );
  }

  Widget _buildEmptyState(BuildContext context, String message) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.usb_off,
            size: 64,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            message,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

/// RTSP cameras tab using proven CAM-FLUTTER-005 pattern
class _RTSPCamerasTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cameraListState = ref.watch(cameraListProvider);
    
    // Filter for RTSP cameras
    final rtspCameras = cameraListState.cameras
        .where((camera) => camera.type == CameraType.rtsp)
        .toList();

    return _buildCamerasList(context, ref, rtspCameras);
  }

  Widget _buildCamerasList(BuildContext context, WidgetRef ref, List<dynamic> cameras) {
    if (cameras.isEmpty) {
      return _buildEmptyState(context);
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.read(cameraListProvider.notifier).loadCameras();
      },
      child: buildResponsiveCameraGrid(cameras),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.wifi_off,
            size: 64,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            'No RTSP cameras found',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tap + to add RTSP cameras',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

/// Dialog for adding RTSP cameras
class _AddRTSPCameraDialog extends ConsumerStatefulWidget {
  @override
  ConsumerState<_AddRTSPCameraDialog> createState() => _AddRTSPCameraDialogState();
}

class _AddRTSPCameraDialogState extends ConsumerState<_AddRTSPCameraDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _hostController = TextEditingController();
  final _portController = TextEditingController(text: '554');
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _pathController = TextEditingController(text: '/stream');
  
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add RTSP Camera'),
      content: SizedBox(
        width: 400,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Camera Name',
                    hintText: 'e.g., Security Camera 1',
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Please enter a camera name';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                
                Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: TextFormField(
                        controller: _hostController,
                        decoration: const InputDecoration(
                          labelText: 'Host/IP',
                          hintText: '192.168.1.100',
                          border: OutlineInputBorder(),
                        ),
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return 'Please enter host/IP';
                          }
                          return null;
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      flex: 1,
                      child: TextFormField(
                        controller: _portController,
                        decoration: const InputDecoration(
                          labelText: 'Port',
                          border: OutlineInputBorder(),
                        ),
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return 'Required';
                          }
                          final port = int.tryParse(value);
                          if (port == null || port < 1 || port > 65535) {
                            return 'Invalid port';
                          }
                          return null;
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                
                TextFormField(
                  controller: _usernameController,
                  decoration: const InputDecoration(
                    labelText: 'Username (optional)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                
                TextFormField(
                  controller: _passwordController,
                  decoration: const InputDecoration(
                    labelText: 'Password (optional)',
                    border: OutlineInputBorder(),
                  ),
                  obscureText: true,
                ),
                const SizedBox(height: 16),
                
                TextFormField(
                  controller: _pathController,
                  decoration: const InputDecoration(
                    labelText: 'Stream Path',
                    hintText: '/stream or /live/ch00_1',
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Please enter stream path';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'RTSP URL Preview:',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _buildRTSPUrl(),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontFamily: 'monospace',
                          color: Theme.of(context).colorScheme.primary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isLoading ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _isLoading ? null : _addRTSPCamera,
          child: _isLoading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Add Camera'),
        ),
      ],
    );
  }

  String _buildRTSPUrl() {
    final host = _hostController.text.trim();
    final port = _portController.text.trim();
    final username = _usernameController.text.trim();
    final password = _passwordController.text.trim();
    final path = _pathController.text.trim();

    if (host.isEmpty) return 'rtsp://...';

    String credentials = '';
    if (username.isNotEmpty) {
      credentials = password.isNotEmpty ? '$username:$password@' : '$username@';
    }

    return 'rtsp://$credentials$host:$port$path';
  }

  Future<void> _addRTSPCamera() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
    });

    try {
      final cameraActions = ref.read(cameraActionsProvider);
      
      final camera = await cameraActions.addRTSPCamera(
        name: _nameController.text.trim(),
        host: _hostController.text.trim(),
        port: int.parse(_portController.text.trim()),
        streamPath: _pathController.text.trim(),
        username: _usernameController.text.trim().isEmpty 
            ? null 
            : _usernameController.text.trim(),
        password: _passwordController.text.trim().isEmpty 
            ? null 
            : _passwordController.text.trim(),
      );
      
      if (mounted) {
        Navigator.of(context).pop();
        if (camera != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('RTSP camera "${camera.name}" added successfully!'),
              backgroundColor: Colors.green,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Failed to add RTSP camera. Please try again.'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error adding RTSP camera: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _hostController.dispose();
    _portController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _pathController.dispose();
    super.dispose();
  }
}
