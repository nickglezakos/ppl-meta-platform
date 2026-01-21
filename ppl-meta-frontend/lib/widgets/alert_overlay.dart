import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/alert_notification_service.dart';

/// Global alert overlay widget that displays alerts on top of any screen
class AlertOverlay extends ConsumerStatefulWidget {
  final Widget child;
  
  const AlertOverlay({
    super.key,
    required this.child,
  });
  
  @override
  ConsumerState<AlertOverlay> createState() => _AlertOverlayState();
}

class _AlertOverlayState extends ConsumerState<AlertOverlay> {
  final List<_ActiveAlert> _activeAlerts = [];
  
  @override
  void initState() {
    super.initState();
    print('🎨 AlertOverlay: Initialized');
  }
  
  void _showAlert(AlertNotification alert) {
    if (!mounted) return;
    
    print('🎨 AlertOverlay: Showing alert: ${alert.message}');
    setState(() {
      // Add alert to active list
      final activeAlert = _ActiveAlert(
        alert: alert,
        onDismiss: () => _dismissAlert(alert.id),
      );
      _activeAlerts.add(activeAlert);
      
      // Auto-dismiss after duration
      Timer(Duration(seconds: alert.durationSeconds), () {
        _dismissAlert(alert.id);
      });
    });
  }
  
  void _dismissAlert(String alertId) {
    if (!mounted) return;
    
    setState(() {
      _activeAlerts.removeWhere((a) => a.alert.id == alertId);
    });
  }
  
  @override
  Widget build(BuildContext context) {
    // Listen to alert stream
    ref.listen<AsyncValue<AlertNotification>>(
      alertStreamProvider,
      (previous, next) {
        next.whenData((alert) {
          print('🔔 AlertOverlay: Received alert from stream');
          _showAlert(alert);
        });
      },
    );
    
    print('🎨 AlertOverlay: Build with ${_activeAlerts.length} active alerts');
    
    return Stack(
      children: [
        // Main app content
        widget.child,
        
        // Alert overlays
        if (_activeAlerts.isNotEmpty)
          Positioned(
            top: 16,
            right: 16,
            left: 16,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: _activeAlerts.map((activeAlert) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _AlertCard(
                    alert: activeAlert.alert,
                    onDismiss: activeAlert.onDismiss,
                  ),
                );
              }).toList(),
            ),
          ),
      ],
    );
  }
}

/// Internal class to track active alerts with their dismiss callbacks
class _ActiveAlert {
  final AlertNotification alert;
  final VoidCallback onDismiss;
  
  _ActiveAlert({
    required this.alert,
    required this.onDismiss,
  });
}

/// Alert card widget with animation
class _AlertCard extends StatefulWidget {
  final AlertNotification alert;
  final VoidCallback onDismiss;
  
  const _AlertCard({
    required this.alert,
    required this.onDismiss,
  });
  
  @override
  State<_AlertCard> createState() => _AlertCardState();
}

class _AlertCardState extends State<_AlertCard> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;
  
  @override
  void initState() {
    super.initState();
    
    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    
    _slideAnimation = Tween<Offset>(
      begin: const Offset(1, 0),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    ));
    
    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeIn,
    ));
    
    _controller.forward();
  }
  
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: Material(
          elevation: 8,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 500),
            decoration: BoxDecoration(
              color: Colors.grey[900],
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: widget.alert.color,
                width: 2,
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Icon
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: widget.alert.color.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(
                      widget.alert.icon,
                      color: widget.alert.color,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 12),
                  
                  // Content
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Severity badge + trigger name
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: widget.alert.color,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                widget.alert.severity.toUpperCase(),
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            if (widget.alert.triggerName != null) ...[
                              const SizedBox(width: 8),
                              Flexible(
                                child: Text(
                                  widget.alert.triggerName!,
                                  style: TextStyle(
                                    color: Colors.grey[400],
                                    fontSize: 12,
                                    fontWeight: FontWeight.w500,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 8),
                        
                        // Alert message
                        Text(
                          widget.alert.message,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        
                        // Action name (if available)
                        if (widget.alert.actionName != null) ...[
                          const SizedBox(height: 4),
                          Text(
                            'Action: ${widget.alert.actionName}',
                            style: TextStyle(
                              color: Colors.grey[400],
                              fontSize: 11,
                            ),
                          ),
                        ],
                        
                        // Timestamp
                        if (widget.alert.timestamp != null) ...[
                          const SizedBox(height: 4),
                          Text(
                            _formatTimestamp(widget.alert.timestamp!),
                            style: TextStyle(
                              color: Colors.grey[500],
                              fontSize: 10,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  
                  // Dismiss button
                  IconButton(
                    icon: const Icon(Icons.close),
                    color: Colors.grey[400],
                    iconSize: 20,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    onPressed: widget.onDismiss,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
  
  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);
    
    if (difference.inSeconds < 60) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else {
      return '${timestamp.day}/${timestamp.month} ${timestamp.hour}:${timestamp.minute.toString().padLeft(2, '0')}';
    }
  }
}
