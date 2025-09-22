import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/providers/auth_provider.dart';
import '../core/providers/features_provider.dart';
import '../widgets/custom_app_bar.dart';
import '../core/theme/app_theme.dart';

class FeaturesScreen extends ConsumerWidget {
  const FeaturesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final featuresState = ref.watch(featuresNotifierProvider);
    final featuresNotifier = ref.read(featuresNotifierProvider.notifier);
    final user = authState.user;

    if (user == null) {
      return Scaffold(
        appBar: const CustomAppBar(
          title: 'Features',
          showBackButton: true,
        ),
        body: const Center(
          child: Text('User not found'),
        ),
      );
    }

    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Features',
        showBackButton: true,
      ),
      body: featuresState.when(
        data: (features) => SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Text(
                'Advanced Features',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Manage your advanced features and capabilities. Some features may require special permissions.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[600],
                ),
              ),
              const SizedBox(height: 24),
              
              // Vision Features Section
              if (features.hasVisionCapability) ...[
                _FeatureSection(
                  title: 'Vision & AI Features',
                  icon: Icons.visibility,
                  children: [
                    _FaceDetectionSettings(
                      featuresState: features,
                      featuresNotifier: featuresNotifier,
                    ),
                    const SizedBox(height: 16),
                    _FaceDetectionOnSaveSettings(
                      featuresState: features,
                      featuresNotifier: featuresNotifier,
                    ),
                  ],
                ),
                const SizedBox(height: 24),
              ] else ...[
                // Show upgrade message for users without vision capability
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.blue[50],
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.blue[200]!),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.star, color: Colors.blue[600]),
                          const SizedBox(width: 8),
                          Text(
                            'Premium Vision Features',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              color: Colors.blue[700],
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Unlock advanced AI-powered vision features including real-time face detection with overlay rectangles on photos and videos.',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.blue[600],
                        ),
                      ),
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Vision capability upgrade coming soon!'),
                            ),
                          );
                        },
                        icon: const Icon(Icons.upgrade),
                        label: const Text('Upgrade to Vision'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blue[600],
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
              ],
              
              // General Features Section
              _FeatureSection(
                title: 'General Features',
                icon: Icons.settings,
                children: [
                  _FeatureToggle(
                    icon: Icons.auto_awesome,
                    title: 'Smart Organization',
                    subtitle: 'Automatically organize your media library',
                    value: features.smartOrganizationEnabled,
                    onChanged: (value) {
                      featuresNotifier.toggleSmartOrganization(value);
                    },
                  ),
                  _FeatureToggle(
                    icon: Icons.cloud_sync,
                    title: 'Auto Sync',
                    subtitle: 'Automatically sync your media across devices',
                    value: features.autoSyncEnabled,
                    onChanged: (value) {
                      featuresNotifier.toggleAutoSync(value);
                    },
                  ),
                ],
              ),
              
              const SizedBox(height: 32),
              
              // Info card for users without vision capability
              if (!features.hasVisionCapability) ...[
                Card(
                  color: AppColors.primary.withOpacity(0.1),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      children: [
                        Icon(
                          Icons.lock,
                          size: 48,
                          color: AppColors.primary,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Premium Features',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Some advanced features require special permissions or premium access. Contact your administrator for more information.',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
        loading: () => const Scaffold(
          appBar: CustomAppBar(
            title: 'Features',
            showBackButton: true,
          ),
          body: Center(
            child: CircularProgressIndicator(),
          ),
        ),
        error: (error, stackTrace) => Scaffold(
          appBar: const CustomAppBar(
            title: 'Features',
            showBackButton: true,
          ),
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(
                  Icons.error,
                  size: 64,
                  color: Colors.red,
                ),
                const SizedBox(height: 16),
                Text(
                  'Failed to load features',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  error.toString(),
                  style: Theme.of(context).textTheme.bodyMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () {
                    ref.refresh(featuresNotifierProvider);
                  },
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _FeatureSection extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Widget> children;

  const _FeatureSection({
    required this.title,
    required this.icon,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 24,
              color: AppColors.primary,
            ),
            const SizedBox(width: 8),
            Text(
              title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ...children,
      ],
    );
  }
}

class _FeatureToggle extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String? description;
  final bool value;
  final ValueChanged<bool> onChanged;
  final bool premium;

  const _FeatureToggle({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.description,
    required this.value,
    required this.onChanged,
    this.premium = false,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                icon,
                color: AppColors.primary,
                size: 24,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        title,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (premium) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.amber.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            'PREMIUM',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: Colors.amber[700],
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey[600],
                    ),
                  ),
                  if (description != null) ...[
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: Colors.blue.withOpacity(0.3),
                          width: 1,
                        ),
                      ),
                      child: Text(
                        description!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.blue[700],
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            Switch(
              value: value,
              onChanged: onChanged,
              activeColor: AppColors.primary,
            ),
          ],
        ),
      ),
    );
  }
}

class _FaceDetectionSettings extends StatelessWidget {
  final FeaturesState featuresState;
  final FeaturesNotifier featuresNotifier;

  const _FaceDetectionSettings({
    required this.featuresState,
    required this.featuresNotifier,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Main toggle header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    Icons.face,
                    color: AppColors.primary,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            'Face Detection on Stream',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.amber.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              'PREMIUM',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: Colors.amber[700],
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Automatically detect and highlight faces in photos and videos with real-time overlay rectangles',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ),
                Switch(
                  value: featuresState.faceDetectionEnabled,
                  onChanged: (value) {
                    featuresNotifier.toggleFaceDetection(value);
                  },
                  activeColor: AppColors.primary,
                ),
              ],
            ),
            
            // Advanced settings (shown only when enabled)
            if (featuresState.faceDetectionEnabled) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: Colors.blue.withOpacity(0.2),
                    width: 1,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.settings,
                          size: 18,
                          color: Colors.blue[700],
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Advanced Settings',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: Colors.blue[700],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    
                    // Detection Method Selection
                    Text(
                      'Detection Method',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: Colors.grey[700],
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.grey[300]!),
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: featuresState.selectedDetectionMethod,
                          items: const [
                            DropdownMenuItem(
                              value: 'two_stage',
                              child: Text('Two-Stage (Recommended) - Haar + Dlib validation'),
                            ),
                            DropdownMenuItem(
                              value: 'haar',
                              child: Text('Haar Cascade - Fast detection'),
                            ),
                            DropdownMenuItem(
                              value: 'dlib',
                              child: Text('Dlib - High accuracy'),
                            ),
                            DropdownMenuItem(
                              value: 'mtcnn',
                              child: Text('MTCNN - Multi-task CNN'),
                            ),
                          ],
                          onChanged: (value) {
                            if (value != null) {
                              featuresNotifier.updateDetectionMethod(value);
                            }
                          },
                          isExpanded: true,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    // Confidence Threshold Slider
                    Text(
                      'Confidence Threshold: ${(featuresState.confidenceThreshold * 100).toInt()}%',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: Colors.grey[700],
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Text(
                          'Low (30%)',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                            fontSize: 10,
                          ),
                        ),
                        Expanded(
                          child: Slider(
                            value: featuresState.confidenceThreshold,
                            min: 0.3,
                            max: 1.0,
                            divisions: 14, // 0.3 to 1.0 with 0.05 steps
                            activeColor: AppColors.primary,
                            onChanged: (value) {
                              featuresNotifier.updateConfidenceThreshold(value);
                            },
                          ),
                        ),
                        Text(
                          'High (100%)',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    
                    // Method-specific default info
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.orange.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            Icons.info_outline,
                            size: 16,
                            color: Colors.orange[700],
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              _getMethodDescription(featuresState.selectedDetectionMethod),
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Colors.orange[700],
                                fontSize: 11,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              
              // Status description
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: Colors.green.withOpacity(0.3),
                    width: 1,
                  ),
                ),
                child: Text(
                  'Face detection is active. View media in the Media Preview to see face detection rectangles overlaid on images and videos using ${featuresState.selectedDetectionMethod} method with ${(featuresState.confidenceThreshold * 100).toInt()}% confidence.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.green[700],
                    fontSize: 11,
                  ),
                ),
              ),
            ] else ...[
              // Disabled description
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.grey.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: Colors.grey.withOpacity(0.3),
                    width: 1,
                  ),
                ),
                child: Text(
                  'Enable face detection to see face rectangles when viewing media in Media Preview with configurable confidence thresholds.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                    fontSize: 11,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _getMethodDescription(String method) {
    switch (method) {
      case 'two_stage':
        return 'Recommended method: Combines Haar cascade speed with Dlib accuracy. Default: 80%';
      case 'haar':
        return 'Fast detection with moderate accuracy. Best for real-time processing. Default: 50%';
      case 'dlib':
        return 'High accuracy face detection with slower processing. Default: 50%';
      case 'mtcnn':
        return 'Multi-task CNN with excellent accuracy for complex scenes. Default: 50%';
      default:
        return 'Advanced face detection method with configurable confidence.';
    }
  }
}

/// NEW: Face Detection on Save Settings Widget
class _FaceDetectionOnSaveSettings extends StatelessWidget {
  final FeaturesState featuresState;
  final FeaturesNotifier featuresNotifier;

  const _FaceDetectionOnSaveSettings({
    required this.featuresState,
    required this.featuresNotifier,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            'Face Detection on Save',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.green.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              'AUTO',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: Colors.green[700],
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Automatically detect faces in camera recordings when videos are saved to the media service',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ),
                Switch(
                  value: featuresState.faceDetectionOnSaveEnabled,
                  onChanged: (value) {
                    featuresNotifier.toggleFaceDetectionOnSave(value);
                  },
                  activeColor: AppColors.primary,
                ),
              ],
            ),
            
            // Status message (shown when enabled)
            if (featuresState.faceDetectionOnSaveEnabled) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: Colors.green.withOpacity(0.3),
                    width: 1,
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.check_circle,
                      color: Colors.green[700],
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Automatic face detection is enabled. All camera recordings will be processed for face detection when saved.',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.green[700],
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ] else ...[
              // Disabled description
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.grey.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: Colors.grey.withOpacity(0.3),
                    width: 1,
                  ),
                ),
                child: Text(
                  'Enable to automatically process camera recordings with face detection when they are saved to the media service.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                    fontSize: 11,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
