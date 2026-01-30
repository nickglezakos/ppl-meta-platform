import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/core.dart';
import '../widgets/registration_form.dart';
import '../widgets/server_status_indicator.dart';
import '../widgets/login_form.dart';
import '../../camera/camera.dart';
import 'simple_setup_screen_new.dart';

/// Main authentication screen with login and registration tabs
class AuthenticationScreen extends StatefulWidget {
  const AuthenticationScreen({Key? key}) : super(key: key);

  @override
  State<AuthenticationScreen> createState() => _AuthenticationScreenState();
}

class _AuthenticationScreenState extends State<AuthenticationScreen>
    with TickerProviderStateMixin {
  late TabController _tabController;
  bool _isInitialized = false;
  String? _discoveredServerUrl;
  bool _isHowTosExpanded = false;  // Track expansion state for How Tos

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _initializeAuth();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _initializeAuth() async {
    // Skip auto-discovery since we're using Simple Setup approach
    setState(() {
      _isInitialized = true;
    });

    // Check if already authenticated
    final authProvider = context.read<AuthenticationProvider>();
    if (authProvider.isAuthenticated) {
      _navigateToHome();
    }
  }

  void _navigateToHome() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (context) => const CameraScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!_isInitialized) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      resizeToAvoidBottomInset: true, // Handle keyboard properly
      body: SafeArea(
        child: Column(
          children: [
            // Header Section
            _buildHeader(),
            
            // Server Status
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 24.0),
              child: ServerStatusIndicator(),
            ),
            
            // Simple Setup Option
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.settings_ethernet,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Simple Network Setup',
                                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                Text(
                                  'Enter Discovery Service port + credentials',
                                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: () async {
                            final result = await Navigator.push<Map<String, dynamic>>(
                              context,
                              MaterialPageRoute(
                                builder: (context) => const SimpleSetupScreen(),
                              ),
                            );
                            // Handle successful connection and authentication
                            if (result != null) {
                              // Authentication was successful, navigate to home
                              _navigateToHome();
                            }
                          },
                          icon: const Icon(Icons.rocket_launch),
                          label: const Text('Start Simple Setup'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                            foregroundColor: Theme.of(context).colorScheme.onPrimaryContainer,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            
            // Tab Bar
            _buildTabBar(),
            
            // Tab Content - Make it scrollable and keyboard-aware
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  // Login Form with scrollable container
                  SingleChildScrollView(
                    keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                    padding: EdgeInsets.only(
                      bottom: MediaQuery.of(context).viewInsets.bottom,
                    ),
                    child: LoginForm(
                      onLoginSuccess: _navigateToHome,
                      prefilledServerUrl: _discoveredServerUrl,
                    ),
                  ),
                  // Registration Form with scrollable container
                  SingleChildScrollView(
                    keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                    padding: EdgeInsets.only(
                      bottom: MediaQuery.of(context).viewInsets.bottom,
                    ),
                    child: RegistrationForm(onRegistrationSuccess: _navigateToHome),
                  ),
                ],
              ),
            ),
            
            // Footer
            _buildFooter(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    // Make header exactly 1/3 of screen height
    final screenHeight = MediaQuery.of(context).size.height;
    final headerHeight = screenHeight / 3;
    final isSmallScreen = screenHeight < 700;
    
    return SizedBox(
      height: headerHeight,
      child: Container(
        padding: EdgeInsets.all(isSmallScreen ? 16.0 : 24.0),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Eyenet Vision Logo
              Container(
                width: isSmallScreen ? 80 : 100,
                height: isSmallScreen ? 80 : 100,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surface,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Theme.of(context).colorScheme.primary.withOpacity(0.2),
                      blurRadius: 20,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: ClipOval(
                  child: Image.asset(
                    'assets/logo.png',
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) {
                      // Fallback to icon if image fails to load
                      return Icon(
                        Icons.camera_alt_rounded,
                        size: isSmallScreen ? 40 : 50,
                        color: Theme.of(context).colorScheme.primary,
                      );
                    },
                  ),
                ),
              ),
              
              SizedBox(height: isSmallScreen ? 8 : 16),
              
              // Title
              Text(
            'Eyenet Vision',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: Theme.of(context).colorScheme.onSurface,
              fontSize: isSmallScreen ? 20 : 24,
            ),
          ),
          
          SizedBox(height: isSmallScreen ? 4 : 8),
          
          // Subtitle
          Text(
            'Professional camera streaming & capture',
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
              fontSize: isSmallScreen ? 12 : 14,
            ),
            textAlign: TextAlign.center,
          ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTabBar() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 24.0),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
      ),
      child: TabBar(
        controller: _tabController,
        indicator: BoxDecoration(
          color: Theme.of(context).colorScheme.primary,
          borderRadius: BorderRadius.circular(10),
        ),
        indicatorSize: TabBarIndicatorSize.tab,
        labelColor: Theme.of(context).colorScheme.onPrimary,
        unselectedLabelColor: Theme.of(context).colorScheme.onSurfaceVariant,
        labelStyle: const TextStyle(
          fontWeight: FontWeight.w600,
          fontSize: 16,
        ),
        unselectedLabelStyle: const TextStyle(
          fontWeight: FontWeight.w500,
          fontSize: 16,
        ),
        tabs: const [
          Tab(
            text: 'Login',
            icon: Icon(Icons.login),
          ),
          Tab(
            text: 'Register',
            icon: Icon(Icons.app_registration),
          ),
        ],
      ),
    );
  }

  Widget _buildFooter() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
            width: 1,
          ),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // How Tos Expandable Section
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () {
                setState(() {
                  _isHowTosExpanded = !_isHowTosExpanded;
                });
              },
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.help_outline,
                          size: 20,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'How Tos',
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: Theme.of(context).colorScheme.onSurface,
                          ),
                        ),
                      ],
                    ),
                    Icon(
                      _isHowTosExpanded ? Icons.expand_less : Icons.expand_more,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ],
                ),
              ),
            ),
          ),
          
          // Expandable Content
          AnimatedSize(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeInOut,
            child: _isHowTosExpanded
                ? Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainer.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildHowToSection(
                          icon: Icons.cloud,
                          title: 'Server Connection',
                          steps: [
                            'Enter your server URL (e.g., http://192.168.1.68:8001)',
                            'Or use the full platform URL if provided',
                          ],
                        ),
                        const SizedBox(height: 12),
                        _buildHowToSection(
                          icon: Icons.login,
                          title: 'Login Credentials',
                          steps: [
                            'Use your existing account username and password',
                            'Contact your administrator if you need credentials',
                          ],
                        ),
                        const SizedBox(height: 12),
                        _buildHowToSection(
                          icon: Icons.app_registration,
                          title: 'Camera Registration',
                          steps: [
                            'After login, you\'ll be asked to register this device',
                            'Enter a unique name for your mobile camera',
                            'Grant camera and storage permissions when prompted',
                          ],
                        ),
                        const SizedBox(height: 12),
                        _buildHowToSection(
                          icon: Icons.error_outline,
                          title: 'Troubleshooting',
                          steps: [
                            'Ensure your device is on the same network as the server',
                            'Check that the server URL is correct and accessible',
                            'Contact your system administrator for access codes',
                          ],
                        ),
                      ],
                    ),
                  )
                : const SizedBox.shrink(),
          ),
          
          const SizedBox(height: 8),
          
          // Version Info
          Text(
            'Eyenet Vision v1.0.0',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
            ),
          ),
          const SizedBox(height: 4),
        ],
      ),
    );
  }

  Widget _buildHowToSection({
    required IconData icon,
    required String title,
    required List<String> steps,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 16,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(width: 8),
            Text(
              title,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ...steps.map((step) => Padding(
              padding: const EdgeInsets.only(left: 24, bottom: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '• ',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      step,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                ],
              ),
            )),
      ],
    );
  }

  void _showHelpDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Connection Help'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('To connect to your PPL Meta platform:'),
            SizedBox(height: 16),
            Text('1. Enter your server URL (e.g., https://your-server.com)'),
            Text('2. Use your existing account credentials, or'),
            Text('3. Register a new camera device with an access code'),
            SizedBox(height: 16),
            Text('Contact your system administrator for:'),
            Text('• Server URL'),
            Text('• Access codes for device registration'),
            Text('• Account credentials'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Got it'),
          ),
        ],
      ),
    );
  }
}
