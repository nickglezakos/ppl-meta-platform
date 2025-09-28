import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:developer' as developer;

import '../providers/face_data_providers.dart';
import '../providers/person_objects_provider.dart' as legacy;
import '../providers/person_objects_provider.dart';
import '../providers/ppl_thread_providers.dart';
import '../models/person_objects_models.dart';

/// Enhanced widget that displays both face count and person count
/// Automatically triggers person objects workflow when face detection completes
class FaceAndPersonCountWidget extends ConsumerStatefulWidget {
  final String mediaId;
  final bool showIcon;
  final bool compact;
  final Color? textColor;
  final Color? iconColor;

  const FaceAndPersonCountWidget({
    super.key,
    required this.mediaId,
    this.showIcon = true,
    this.compact = false,
    this.textColor,
    this.iconColor,
  });

  @override
  ConsumerState<FaceAndPersonCountWidget> createState() => _FaceAndPersonCountWidgetState();
}

class _FaceAndPersonCountWidgetState extends ConsumerState<FaceAndPersonCountWidget> {
  bool _hasTriggeredPersonObjects = false;
  bool _hasAttemptedRetry = false;

  @override
  Widget build(BuildContext context) {
    print('🏗️ FaceAndPersonCountWidget.build() called for mediaId: ${widget.mediaId}');
    
    final faceData = ref.watch(mediaFaceDataProvider(widget.mediaId));
    // Use the updated provider that calls Orchestrator endpoint
    final personObjectsAsync = ref.watch(personObjectsDataProvider(widget.mediaId));
    
    // Add debug logging and check all provider states
    personObjectsAsync.when(
      data: (data) {
        if (data != null) {
          print('🎯 WIDGET DEBUG: PersonObjects data received: totalPersons=${data.totalPersons}, success=${data.success}');
          developer.log('🎯 PersonObjects data received: totalPersons=${data.totalPersons}, success=${data.success}', name: 'PersonCountWidget');
        } else {
          print('🎯 WIDGET DEBUG: PersonObjects data is null');
        }
      },
      loading: () {
        print('🎯 WIDGET DEBUG: PersonObjects provider is loading');
      },
      error: (error, stackTrace) {
        print('🎯 WIDGET DEBUG: PersonObjects provider error: $error');
      },
    );
    
    // Force refresh provider cache every 5 seconds to pick up new data
    // This ensures we get updated person counts after PPL Thread processing
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted) {
        ref.invalidate(personObjectsDataProvider(widget.mediaId));
      }
    });
    final workflowState = ref.watch(personObjectsWorkflowControllerProvider);

    print('🔍 Main Widget build - faceData: totalCount=${faceData.totalCount}, isLoading=${faceData.isLoading}, hasError=${faceData.hasError}');
    print('🔍 Main Widget build - personObjectsAsync: value=${personObjectsAsync.value?.totalPersons}, isLoading=${personObjectsAsync.isLoading}, hasError=${personObjectsAsync.hasError}, hasValue=${personObjectsAsync.hasValue}');

    // Debug logging
    developer.log(
      'FaceAndPersonCountWidget build: mediaId=${widget.mediaId}, faces=${faceData.totalCount}, personObjectsAsync=${personObjectsAsync.runtimeType}',
      name: 'FaceAndPersonCountWidget',
    );

    // LOUD DEBUG - should definitely show up
    debugPrint('🚨 WIDGET RENDERING: faces=${faceData.totalCount}, persons=${personObjectsAsync.value?.totalPersons ?? 0}');
    
    // Auto-trigger person objects workflow when face detection completes
    _autoTriggerPersonObjectsIfNeeded(faceData, personObjectsAsync, workflowState);

    if (widget.compact) {
      return _buildCompactWidget(context, faceData, personObjectsAsync, workflowState);
    } else {
      return _buildFullWidget(context, faceData, personObjectsAsync, workflowState);
    }
  }

  /// Automatically trigger person objects workflow when face detection is complete
  void _autoTriggerPersonObjectsIfNeeded(
    MediaFaceDataState faceData,
    AsyncValue<PersonObjectsData?> personObjectsAsync,
    legacy.PersonObjectsWorkflowState workflowState,
  ) {
    // LOUD DEBUG - should definitely show up
    debugPrint('🚨 AUTO-TRIGGER CALLED: mediaId=${widget.mediaId}, faces=${faceData.totalCount}, hasTriggered=$_hasTriggeredPersonObjects');
    
    // Debug logging for all videos
    developer.log(
      'AUTO-TRIGGER CHECK: mediaId=${widget.mediaId}, '
      'hasTriggered=$_hasTriggeredPersonObjects, '
      'faceLoading=${faceData.isLoading}, '
      'faceError=${faceData.hasError}, '
      'faceCount=${faceData.totalCount}, '
      'personObjectsValue=${personObjectsAsync.value}, '
      'workflowState=$workflowState',
      name: 'FaceAndPersonCountWidget',
    );

    // Reset trigger flag only once when conditions change (prevent infinite loops)
    // We only reset if we haven't already attempted a retry
    if (_hasTriggeredPersonObjects && !_hasAttemptedRetry) {
      bool shouldResetTrigger = false;
      
      // 1. If person objects provider is in error state (404 means no session exists)
      if (personObjectsAsync.hasError) {
        debugPrint('🔄 RESETTING TRIGGER FLAG: Person objects provider in error state, will retry workflow');
        shouldResetTrigger = true;
      }
      // 2. If workflow completed but returned no persons (suggests session creation failed)
      else if (workflowState == legacy.PersonObjectsWorkflowState.completed &&
          (personObjectsAsync.value == null || personObjectsAsync.value!.totalPersons == 0) &&
          faceData.totalCount > 0) {
        debugPrint('🔄 RESETTING TRIGGER FLAG: Workflow completed but no persons found despite having ${faceData.totalCount} faces');
        shouldResetTrigger = true;
      }
      
      if (shouldResetTrigger) {
        _hasTriggeredPersonObjects = false;
        _hasAttemptedRetry = true; // Prevent multiple retry attempts
      }
    }
    
    // Only trigger if:
    // 1. Face detection is complete and has faces
    // 2. Person objects workflow hasn't been triggered yet (or was reset due to conditions above)
    // 3. Person objects don't already exist (or are in error state due to no session)
    // 4. Not currently processing person objects
    debugPrint('🔍 AUTO-TRIGGER CONDITIONS: hasTriggered=$_hasTriggeredPersonObjects, faceLoading=${faceData.isLoading}, faceError=${faceData.hasError}, faceCount=${faceData.totalCount}, personObjectsError=${personObjectsAsync.hasError}, workflowState=$workflowState, personCount=${personObjectsAsync.value?.totalPersons ?? 0}');
    
    if (!_hasTriggeredPersonObjects &&
        !faceData.isLoading &&
        !faceData.hasError &&
        faceData.totalCount > 0 &&
        (personObjectsAsync.value == null || personObjectsAsync.hasError || personObjectsAsync.value!.totalPersons == 0) &&
        workflowState != legacy.PersonObjectsWorkflowState.processing &&
        workflowState != legacy.PersonObjectsWorkflowState.triggering) {
      
      _hasTriggeredPersonObjects = true;
      
      debugPrint('🚀 STARTING AUTO-TRIGGER: About to trigger person objects workflow for ${widget.mediaId}');
      
      developer.log(
        'Auto-triggering person objects workflow for media: ${widget.mediaId} (${faceData.totalCount} faces detected)',
        name: 'FaceAndPersonCountWidget',
      );

      // Trigger person objects workflow after a small delay
      WidgetsBinding.instance.addPostFrameCallback((_) async {
        try {
          debugPrint('🚀 CALLING CONTROLLER: Attempting to trigger workflow for ${widget.mediaId}');
          final controller = ref.read(legacy.personObjectsWorkflowControllerProvider.notifier);
          await controller.autoTriggerWorkflow(widget.mediaId);
          
          debugPrint('✅ WORKFLOW TRIGGERED: Successfully triggered workflow for ${widget.mediaId}');
          developer.log(
            'Person objects workflow triggered successfully for: ${widget.mediaId}',
            name: 'FaceAndPersonCountWidget',
          );
        } catch (e) {
          debugPrint('❌ WORKFLOW FAILED: Error triggering workflow for ${widget.mediaId}: $e');
          developer.log(
            'Failed to trigger person objects workflow for ${widget.mediaId}: $e',
            name: 'FaceAndPersonCountWidget',
            error: e,
          );
        }
      });
    } else {
      // Debug why workflow wasn't triggered
      developer.log(
        'AUTO-TRIGGER SKIPPED for ${widget.mediaId}: '
        'hasTriggered=$_hasTriggeredPersonObjects, '
        'faceLoading=${faceData.isLoading}, '
        'faceError=${faceData.hasError}, '
        'faceCount=${faceData.totalCount}, '
        'hasPersonObjects=${personObjectsAsync.value != null}, '
        'workflowBusy=${workflowState == legacy.PersonObjectsWorkflowState.processing || workflowState == legacy.PersonObjectsWorkflowState.triggering}',
        name: 'FaceAndPersonCountWidget',
      );
    }
  }

  Widget _buildCompactWidget(
    BuildContext context,
    MediaFaceDataState faceData,
    AsyncValue<PersonObjectsData?> personObjectsAsync,
    legacy.PersonObjectsWorkflowState workflowState,
  ) {
    final theme = Theme.of(context);
    final effectiveTextColor = widget.textColor ?? theme.textTheme.bodySmall?.color ?? Colors.white70;
    final effectiveIconColor = widget.iconColor ?? effectiveTextColor;

    if (faceData.isLoading) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (widget.showIcon) ...[
            SizedBox(
              width: 12,
              height: 12,
              child: CircularProgressIndicator(
                strokeWidth: 1.5,
                valueColor: AlwaysStoppedAnimation<Color>(effectiveIconColor),
              ),
            ),
            const SizedBox(width: 4),
          ],
          Text(
            'Loading...',
            style: TextStyle(
              color: effectiveTextColor,
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      );
    }

    if (faceData.hasError) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (widget.showIcon) ...[
            Icon(
              Icons.error_outline,
              size: 12,
              color: Colors.red[300],
            ),
            const SizedBox(width: 4),
          ],
          Text(
            'Error',
            style: TextStyle(
              color: Colors.red[300],
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Face count line
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.showIcon) ...[
              Icon(
                Icons.face,
                size: 12,
                color: effectiveIconColor,
              ),
              const SizedBox(width: 4),
            ],
            Text(
              '${faceData.totalCount} faces',
              style: TextStyle(
                color: effectiveTextColor,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        
        // Person count line (only show if faces exist)
        if (faceData.totalCount > 0) ...[
          const SizedBox(height: 2),
          _buildPersonCountWidget(
            context, 
            personObjectsAsync, 
            workflowState, 
            effectiveTextColor, 
            effectiveIconColor,
          ),
        ],
      ],
    );
  }

  /// Build person count widget using workflow result or API data
  Widget _buildPersonCountWidget(
    BuildContext context,
    AsyncValue<PersonObjectsData?> personObjectsAsync,
    legacy.PersonObjectsWorkflowState workflowState,
    Color textColor,
    Color iconColor,
  ) {
    // First, check if we have workflow result data (preferred)
    if (workflowState == legacy.PersonObjectsWorkflowState.completed) {
      // Get the workflow controller to access lastResult
      final workflowController = ref.read(legacy.personObjectsWorkflowControllerProvider.notifier);
      final data = workflowController.lastResult;
      
      if (data != null) {
        developer.log(
          'Using workflow result: ${data.totalPersons} persons',
          name: 'FaceAndPersonCountWidget',
        );
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.showIcon) ...[
              Icon(
                Icons.people,
                size: 12,
                color: Colors.blue.shade300,
              ),
              const SizedBox(width: 4),
            ],
            Text(
              '${data.totalPersons} persons',
              style: TextStyle(
                color: Colors.blue.shade300,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        );
      }
    }

    // Fall back to API data if no workflow result
    return personObjectsAsync.when(
      data: (data) {
        // Debug logging for person objects data
        developer.log(
          'PersonObjects API data received: data=${data?.runtimeType}, totalPersons=${data?.totalPersons}, workflowState=$workflowState',
          name: 'FaceAndPersonCountWidget',
        );
        
        if (data != null) {
          developer.log(
            'Showing person count from API: ${data.totalPersons} persons',
            name: 'FaceAndPersonCountWidget',
          );
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (widget.showIcon) ...[
                Icon(
                  Icons.people,
                  size: 12,
                  color: Colors.blue.shade300,
                ),
                const SizedBox(width: 4),
              ],
              Text(
                '${data.totalPersons} persons',
                style: TextStyle(
                  color: Colors.blue.shade300,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          );
        } else if (workflowState == legacy.PersonObjectsWorkflowState.processing ||
                   workflowState == legacy.PersonObjectsWorkflowState.triggering) {
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 10,
                height: 10,
                child: CircularProgressIndicator(
                  strokeWidth: 1,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.orange.shade300),
                ),
              ),
              const SizedBox(width: 4),
              Text(
                'Grouping...',
                style: TextStyle(
                  color: Colors.orange.shade300,
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          );
        } else {
          developer.log(
            'PersonObjects API data is null, hiding person count widget. WorkflowState: $workflowState',
            name: 'FaceAndPersonCountWidget',
          );
          return const SizedBox.shrink();
        }
            },
            loading: () {
              developer.log(
                'PersonObjects loading state - showing loading indicator',
                name: 'FaceAndPersonCountWidget',
              );
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 10,
                    height: 10,
                    child: CircularProgressIndicator(
                      strokeWidth: 1,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.grey.shade400),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Loading...',
                    style: TextStyle(
                      color: Colors.grey.shade400,
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              );
            },
            error: (error, stack) {
              developer.log(
                'PersonObjects error state: $error',
                name: 'FaceAndPersonCountWidget',
                error: error,
              );
              return const SizedBox.shrink();
            },
          );
  }

  Widget _buildFullWidget(
    BuildContext context,
    MediaFaceDataState faceData,
    AsyncValue<PersonObjectsData?> personObjectsAsync,
    legacy.PersonObjectsWorkflowState workflowState,
  ) {
    final theme = Theme.of(context);
    final effectiveTextColor = widget.textColor ?? theme.textTheme.bodyMedium?.color ?? Colors.white;
    final effectiveIconColor = widget.iconColor ?? effectiveTextColor;

    if (faceData.isLoading) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.blue.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.blue.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.blue),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              'Loading faces...',
              style: TextStyle(
                color: Colors.blue,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    if (faceData.hasError) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.red.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.red.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              size: 16,
              color: Colors.red[300],
            ),
            const SizedBox(width: 8),
            Text(
              'Face load error',
              style: TextStyle(
                color: Colors.red[300],
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    Color containerColor;
    Color borderColor;
    if (faceData.totalCount > 0) {
      containerColor = Colors.green.withOpacity(0.1);
      borderColor = Colors.green.withOpacity(0.3);
    } else {
      containerColor = Colors.grey.withOpacity(0.1);
      borderColor = Colors.grey.withOpacity(0.3);
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: containerColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Face count line
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.face,
                size: 16,
                color: faceData.totalCount > 0 ? Colors.green : Colors.grey,
              ),
              const SizedBox(width: 8),
              Text(
                'Faces: ${faceData.totalCount}',
                style: TextStyle(
                  color: faceData.totalCount > 0 ? Colors.green : Colors.grey,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          
          // Person count line (only show if faces exist)
          if (faceData.totalCount > 0) ...[
            const SizedBox(height: 4),
            personObjectsAsync.when(
              data: (data) {
                if (data != null) {
                  return Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.people,
                        size: 16,
                        color: Colors.blue,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Persons: ${data.totalPersons}',
                        style: TextStyle(
                          color: Colors.blue,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  );
                } else if (workflowState == legacy.PersonObjectsWorkflowState.processing ||
                           workflowState == legacy.PersonObjectsWorkflowState.triggering) {
                  return Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.orange),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Grouping persons...',
                        style: TextStyle(
                          color: Colors.orange,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  );
                } else {
                  return Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.people_outline,
                        size: 16,
                        color: Colors.grey.shade400,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Person grouping available',
                        style: TextStyle(
                          color: Colors.grey.shade400,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  );
                }
              },
              loading: () => Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.grey),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Loading persons...',
                    style: TextStyle(
                      color: Colors.grey,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
              error: (error, stack) => const SizedBox.shrink(),
            ),
          ],
        ],
      ),
    );
  }
}

/// Compact face and person count display for tight spaces
/// NOW USES PPL THREAD SERVICE for real person counts!
class CompactFaceAndPersonCountWidget extends ConsumerWidget {
  final String mediaId;
  final Color? color;

  const CompactFaceAndPersonCountWidget({
    super.key,
    required this.mediaId,
    this.color,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final faceData = ref.watch(mediaFaceDataProvider(mediaId));
    final personObjectsAsync = ref.watch(personObjectsDataProvider(mediaId));
    
    // DEBUG: Force logging when widget builds
    developer.log('CompactFaceAndPersonCountWidget build: mediaId=$mediaId, personObjectsAsync.hasValue=${personObjectsAsync.hasValue}', name: 'CompactWidget');
    
    // Add comprehensive debugging for provider states
    personObjectsAsync.when(
      data: (data) {
        if (data != null) {
          print('🎯 COMPACT WIDGET DEBUG: PersonObjects data received: totalPersons=${data.totalPersons}, success=${data.success}');
          developer.log('🎯 COMPACT: PersonObjects data received: totalPersons=${data.totalPersons}, success=${data.success}', name: 'CompactWidget');
        } else {
          print('🎯 COMPACT WIDGET DEBUG: PersonObjects data is null');
        }
      },
      loading: () {
        print('🎯 COMPACT WIDGET DEBUG: PersonObjects provider is loading');
      },
      error: (error, stackTrace) {
        print('🎯 COMPACT WIDGET DEBUG: PersonObjects provider error: $error');
      },
    );
    
    final effectiveTextColor = color ?? Colors.white70;
    final effectiveIconColor = color ?? Colors.white70;

    if (faceData.isLoading) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 12,
            height: 12,
            child: CircularProgressIndicator(
              strokeWidth: 1.5,
              valueColor: AlwaysStoppedAnimation<Color>(effectiveIconColor),
            ),
          ),
          const SizedBox(width: 4),
          Text(
            'Loading...',
            style: TextStyle(
              color: effectiveTextColor,
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      );
    }

    if (faceData.hasError) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.error_outline,
            size: 12,
            color: Colors.red[300],
          ),
          const SizedBox(width: 4),
          Text(
            'Error',
            style: TextStyle(
              color: Colors.red[300],
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      );
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Face count
        Icon(
          Icons.face,
          size: 10,
          color: effectiveIconColor,
        ),
        const SizedBox(width: 2),
        Text(
          '${faceData.totalCount}F',
          style: TextStyle(
            color: effectiveTextColor,
            fontSize: 8,
            fontWeight: FontWeight.w600,
          ),
        ),
        
        // Person count (only if faces > 0)
        if (faceData.totalCount > 0) ...[
          const SizedBox(width: 6),
          personObjectsAsync.when(
            data: (personObjectsData) {
              final personCount = personObjectsData?.totalPersons ?? 0;
              developer.log('PPL Thread Data SUCCESS: personCount=$personCount for mediaId=$mediaId', name: 'CompactWidget');
              print('🎯 COMPACT RENDERING: totalPersons=$personCount');
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.people,
                    size: 10,
                    color: Colors.blue.shade300,
                  ),
                  const SizedBox(width: 2),
                  Text(
                    personCount == 0 ? '0P' : '${personCount}P',
                    style: TextStyle(
                      color: Colors.blue.shade300,
                      fontSize: 8,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              );
            },
            loading: () {
              developer.log('PPL Thread LOADING for mediaId=$mediaId', name: 'CompactWidget');
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 6,
                    height: 6,
                    child: CircularProgressIndicator(
                      strokeWidth: 0.8,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.blue.shade300),
                    ),
                  ),
                  const SizedBox(width: 2),
                  Text(
                    '?P',
                    style: TextStyle(
                      color: Colors.blue.shade300,
                      fontSize: 8,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              );
            },
            error: (error, stack) {
              developer.log('PPL Thread ERROR for mediaId=$mediaId: $error', name: 'CompactWidget', error: error, stackTrace: stack);
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.error,
                    size: 8,
                    color: Colors.red.shade400,
                  ),
                  const SizedBox(width: 2),
                  Text(
                    '!P',
                    style: TextStyle(
                      color: Colors.red.shade400,
                      fontSize: 8,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              );
            },
          ),
        ],
      ],
    );
  }
}

/// NEW: Simple PPL Thread-based person count widget
/// This widget uses the new READ-ONLY PPL Thread service integration
class SimplePPLPersonCountWidget extends ConsumerWidget {
  final String mediaId;
  final Color? color;

  const SimplePPLPersonCountWidget({
    super.key,
    required this.mediaId,
    this.color,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final faceData = ref.watch(mediaFaceDataProvider(mediaId));
    
    return CompactFaceAndPersonCountWidget(
      mediaId: mediaId,
      color: color,
    );
  }
}

/// Face and person count badge for overlay display
class FaceAndPersonCountBadge extends ConsumerWidget {
  final String mediaId;
  final Color? backgroundColor;
  final Color? textColor;

  const FaceAndPersonCountBadge({
    super.key,
    required this.mediaId,
    this.backgroundColor,
    this.textColor,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final faceData = ref.watch(mediaFaceDataProvider(mediaId));
    final personObjectsAsync = ref.watch(personObjectsDataProvider(mediaId));
    
    if (faceData.isLoading) {
      return Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: backgroundColor ?? Colors.blue.withOpacity(0.8),
          borderRadius: BorderRadius.circular(12),
        ),
        child: SizedBox(
          width: 12,
          height: 12,
          child: CircularProgressIndicator(
            strokeWidth: 1.5,
            valueColor: AlwaysStoppedAnimation<Color>(
              textColor ?? Colors.white,
            ),
          ),
        ),
      );
    }

    if (faceData.hasError) {
      return Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: backgroundColor ?? Colors.red.withOpacity(0.8),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(
          Icons.error_outline,
          size: 12,
          color: textColor ?? Colors.white,
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: backgroundColor ?? Colors.black.withOpacity(0.7),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Face count
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.face,
                size: 10,
                color: textColor ?? Colors.white,
              ),
              const SizedBox(width: 2),
              Text(
                '${faceData.totalCount}',
                style: TextStyle(
                  color: textColor ?? Colors.white,
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          
          // Person count (if available)
          if (faceData.totalCount > 0)
            personObjectsAsync.when(
              data: (data) {
                if (data != null) {
                  // Check if this is the "unavailable" placeholder
                  final isUnavailable = data.sessionUuid == 'unavailable';
                  
                  return Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.people,
                        size: 8,
                        color: (textColor ?? Colors.white).withOpacity(isUnavailable ? 0.5 : 0.8),
                      ),
                      const SizedBox(width: 1),
                      Text(
                        isUnavailable ? '?' : '${data.totalPersons}',
                        style: TextStyle(
                          color: (textColor ?? Colors.white).withOpacity(isUnavailable ? 0.5 : 0.8),
                          fontSize: 8,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  );
                } else {
                  return const SizedBox.shrink();
                }
              },
              loading: () => Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.people,
                    size: 8,
                    color: (textColor ?? Colors.white).withOpacity(0.5),
                  ),
                  const SizedBox(width: 1),
                  Text(
                    '...',
                    style: TextStyle(
                      color: (textColor ?? Colors.white).withOpacity(0.5),
                      fontSize: 8,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              error: (error, stack) => Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.people,
                    size: 8,
                    color: (textColor ?? Colors.white).withOpacity(0.3),
                  ),
                  const SizedBox(width: 1),
                  Text(
                    '!',
                    style: TextStyle(
                      color: (textColor ?? Colors.white).withOpacity(0.3),
                      fontSize: 8,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}