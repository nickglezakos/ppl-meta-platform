import 'package:flutter/material.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/triggers_tab.dart';
import '../widgets/actions_tab.dart';

/// Standalone Triggers and Actions management screen
/// 
/// Contains two tabs:
/// 1. Triggers - Automated alerts based on person detection criteria
/// 2. Actions - Orchestrator workflows that can be fired from triggers
class TriggersScreen extends StatefulWidget {
  const TriggersScreen({Key? key}) : super(key: key);

  @override
  State<TriggersScreen> createState() => _TriggersScreenState();
}

class _TriggersScreenState extends State<TriggersScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _showHelp() {
    final isTriggersTab = _tabController.index == 0;
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(isTriggersTab ? 'About Triggers' : 'About Actions'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (isTriggersTab) ...[
                const Text(
                  'Triggers are automated alerts based on person detection criteria.',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 16),
                const Text('Features:'),
                const SizedBox(height: 8),
                const Text('• Person count conditions (more than, less than, equals, between)'),
                const Text('• Age range filtering (underage, adults, seniors, all)'),
                const Text('• Gender filtering'),
                const Text('• Time span restrictions'),
                const Text('• Media source assignment (cameras/collections)'),
                const Text('• Multiple action types (alert, email, webhook, log)'),
                const SizedBox(height: 16),
                const Text('Actions:'),
                const SizedBox(height: 8),
                const Text('• Click status badge to toggle active/inactive'),
                const Text('• Use Edit button to modify trigger settings'),
                const Text('• Use Delete button to remove triggers'),
                const Text('• Use Create button to add new triggers'),
              ] else ...[
                const Text(
                  'Actions wrap orchestrator workflows that can be triggered automatically.',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 16),
                const Text('Features:'),
                const SizedBox(height: 8),
                const Text('• Wrap workflow execution in action data types'),
                const Text('• Can be fired from triggers when conditions are met'),
                const Text('• Track execution count and success rates'),
                const Text('• Support for multiple workflow types'),
                const SizedBox(height: 16),
                const Text('Workflow Types:'),
                const SizedBox(height: 8),
                const Text('• Face Detection - Process videos for face detection'),
                const Text('• Person Tracking - Track individuals across videos'),
                const Text('• Demographics - Analyze age and gender'),
                const SizedBox(height: 16),
                const Text('Management:'),
                const SizedBox(height: 8),
                const Text('• Click status badge to enable/disable actions'),
                const Text('• Use Edit button to modify action settings'),
                const Text('• Use Delete button to remove actions'),
                const Text('• Use Create button to add new workflow actions'),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: 'Triggers & Actions',
        showBackButton: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: () {
              // Trigger a rebuild to reload data
              setState(() {});
            },
          ),
          IconButton(
            icon: const Icon(Icons.help_outline),
            tooltip: 'Help',
            onPressed: _showHelp,
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(
              icon: Icon(Icons.notifications_active),
              text: 'Triggers',
            ),
            Tab(
              icon: Icon(Icons.play_circle_outline),
              text: 'Actions',
            ),
          ],
          indicatorColor: Colors.orange,
          labelColor: Colors.orange,
          unselectedLabelColor: Colors.grey,
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [
          TriggersTab(),
          ActionsTab(),
        ],
      ),
    );
  }
}
