import 'package:flutter/material.dart';
import 'models/mock_data.dart';
import 'screens/resource_home_screen.dart';

/// Throwaway UI-only prototype validating the Unified CRUD UX proposal
/// (docs/proposals/UX/unified-crud-ux.md).
///
/// This is NOT a deliverable and must not be wired to real APIs.
void main() {
  runApp(const PplMetaMockupApp());
}

const _seed = Color(0xFF0B7CFF);

class PplMetaMockupApp extends StatefulWidget {
  const PplMetaMockupApp({super.key});

  @override
  State<PplMetaMockupApp> createState() => _PplMetaMockupAppState();
}

class _PplMetaMockupAppState extends State<PplMetaMockupApp> {
  ThemeMode _themeMode = ThemeMode.light;

  void _toggleTheme() {
    setState(() {
      _themeMode =
          _themeMode == ThemeMode.light ? ThemeMode.dark : ThemeMode.light;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PPL Meta — CRUD UX Mockup',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: _seed),
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _seed,
          brightness: Brightness.dark,
        ),
      ),
      themeMode: _themeMode,
      home: PrototypeHome(
        isDark: _themeMode == ThemeMode.dark,
        onThemeToggle: _toggleTheme,
      ),
    );
  }
}

/// Launcher that exposes the four target resources.
class PrototypeHome extends StatelessWidget {
  const PrototypeHome({
    super.key,
    required this.isDark,
    required this.onThemeToggle,
  });

  final bool isDark;
  final VoidCallback onThemeToggle;

  @override
  Widget build(BuildContext context) {
    final resources = kResources.values.toList();
    return Scaffold(
      appBar: AppBar(
        title: const Text('PPL Meta — CRUD UX Mockup'),
        actions: [
          IconButton(
            tooltip: isDark ? 'Switch to light theme' : 'Switch to dark theme',
            onPressed: onThemeToggle,
            icon: Icon(
              isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
              child: Text(
                'Unified data-object management for Cameras, Collections, '
                'Individual Groups and Triggers.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                'Validate: grid/list toggle · search & filter · master/detail '
                '(resize wide) · the single unified toggle (flip a switch, '
                'enable "Simulate commit failure" to see revert) · the editor '
                'surface changes by width (full-screen → dialog → inline).',
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant),
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final cols = constraints.maxWidth < 600
                      ? 1
                      : constraints.maxWidth < 1000
                          ? 2
                          : 4;
                  return GridView.builder(
                    padding: const EdgeInsets.all(16),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: cols,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 2.2,
                    ),
                    itemCount: resources.length,
                    itemBuilder: (context, i) {
                      final r = resources[i];
                      final scheme = Theme.of(context).colorScheme;
                      return Card(
                        clipBehavior: Clip.antiAlias,
                        child: InkWell(
                          onTap: () => Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder: (_) => ResourceHomeScreen(resource: r),
                            ),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Row(
                              children: [
                                CircleAvatar(
                                  radius: 22,
                                  backgroundColor: scheme.primaryContainer,
                                  child: Icon(r.icon, color: scheme.onPrimaryContainer),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(r.name,
                                          style: Theme.of(context).textTheme.titleMedium),
                                      Text(
                                        '${r.items.length} items · ${r.defaultGrid ? 'grid' : 'list'} default',
                                        style: Theme.of(context).textTheme.bodySmall,
                                      ),
                                    ],
                                  ),
                                ),
                                const Icon(Icons.chevron_right),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
