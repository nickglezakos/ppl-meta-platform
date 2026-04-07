import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/theme/app_theme.dart';
import '../models/media_models.dart';
import '../core/models/collection_models.dart';
import '../core/providers/search_providers.dart';
import '../services/media_api_client.dart';
import '../core/api/api_client.dart';

/// Advanced search interface with filters and suggestions
class AdvancedSearchInterface extends StatefulWidget {
  final MediaSearchFilters? initialFilters;
  final Function(String, MediaSearchFilters?) onSearch;
  final Function()? onClear;
  final List<String>? availableTags;
  final List<String>? availableCollections; // Deprecated - use dynamic loading
  final bool showAdvancedFilters;
  final bool enableCameraFilters;
  final bool showVirtualCollections;
  final ApiClient? apiClient; // For dynamic collection loading

  const AdvancedSearchInterface({
    super.key,
    this.initialFilters,
    required this.onSearch,
    this.onClear,
    this.availableTags,
    this.availableCollections,
    this.showAdvancedFilters = false,
    this.enableCameraFilters = false,
    this.showVirtualCollections = false,
    this.apiClient,
  });

  @override
  State<AdvancedSearchInterface> createState() => _AdvancedSearchInterfaceState();
}

class _AdvancedSearchInterfaceState extends State<AdvancedSearchInterface>
    with TickerProviderStateMixin {
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();
  
  late AnimationController _filtersAnimationController;
  late Animation<double> _filtersAnimation;
  
  bool _showAdvancedFilters = false;
  MediaSearchFilters _filters = MediaSearchFilters();
  List<String> _searchSuggestions = [];
  bool _showSuggestions = false;
  
  // Multi-select collections state
  List<String> _selectedCollectionIds = [];
  
  // Dynamic collection loading
  MediaApiClient? _mediaApiClient;
  List<MediaCollection> _availableCollections = [];
  bool _loadingCollections = false;

  @override
  void initState() {
    super.initState();
    
    _filtersAnimationController = AnimationController(
      duration: AppDurations.normal,
      vsync: this,
    );
    
    _filtersAnimation = CurvedAnimation(
      parent: _filtersAnimationController,
      curve: AppCurves.easeInOut,
    );
    
    // Initialize with provided filters
    if (widget.initialFilters != null) {
      _filters = widget.initialFilters!;
      _searchController.text = _filters.query ?? '';
      
      // Initialize selected collections from filters
      if (_filters.collectionIds != null) {
        _selectedCollectionIds = List.from(_filters.collectionIds!);
      } else if (_filters.collectionId != null) {
        // Backward compatibility: convert single collection to list
        _selectedCollectionIds = [_filters.collectionId!];
      }
    }
    
    _showAdvancedFilters = widget.showAdvancedFilters;
    if (_showAdvancedFilters) {
      _filtersAnimationController.forward();
    }
    
    // Initialize API client for dynamic collection loading
    if (widget.apiClient != null) {
      _mediaApiClient = MediaApiClient(widget.apiClient!);
      _loadCollections();
    }
    
    _searchFocusNode.addListener(_onFocusChanged);
    _searchController.addListener(_onSearchChanged);
  }

  @override
  void dispose() {
    _filtersAnimationController.dispose();
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  /// Load collections dynamically from API
  Future<void> _loadCollections() async {
    if (_mediaApiClient == null) return;
    
    setState(() {
      _loadingCollections = true;
    });
    
    try {
      final response = await _mediaApiClient!.getCollections();
      if (response.success) {
        setState(() {
          _availableCollections = response.data ?? [];
          _loadingCollections = false;
          
          // Validate and clean up selected collections after loading
          _validateSelectedCollections();
        });
      } else {
        print('Failed to load collections: ${response.error}');
        setState(() {
          _loadingCollections = false;
        });
      }
    } catch (e) {
      print('Error loading collections: $e');
      setState(() {
        _loadingCollections = false;
      });
    }
  }

  void _validateSelectedCollections() {
    // Remove any selected collection IDs that don't exist in available collections
    final availableIds = _availableCollections.map((c) => c.id).toSet();
    final initialCount = _selectedCollectionIds.length;
    _selectedCollectionIds.removeWhere((id) => !availableIds.contains(id));
    
    if (_selectedCollectionIds.length != initialCount) {
      print('Removed ${initialCount - _selectedCollectionIds.length} invalid collection IDs');
    }
  }

  /// Handle search focus changes
  void _onFocusChanged() {
    if (!_searchFocusNode.hasFocus) {
      setState(() {
        _showSuggestions = false;
      });
    }
  }

  /// Handle search text changes
  void _onSearchChanged() {
    final query = _searchController.text;
    _updateSearchSuggestions(query);
    
    // Auto-search after 500ms delay
    Future.delayed(const Duration(milliseconds: 500), () {
      if (_searchController.text == query) {
        _performSearch();
      }
    });
  }

  /// Update search suggestions
  void _updateSearchSuggestions(String query) {
    if (query.isEmpty) {
      setState(() {
        _searchSuggestions.clear();
        _showSuggestions = false;
      });
      return;
    }

    // Generate suggestions based on available tags and common terms
    final suggestions = <String>[];
    
    // Add tag suggestions
    if (widget.availableTags != null) {
      suggestions.addAll(
        widget.availableTags!
            .where((tag) => tag.toLowerCase().contains(query.toLowerCase()))
            .take(5),
      );
    }
    
    // Add common search terms
    final commonTerms = [
      'image', 'photo', 'picture', 'video', 'movie', 'clip',
      'audio', 'music', 'sound', 'document', 'pdf', 'text',
      'recent', 'today', 'yesterday', 'this week', 'this month',
    ];
    
    suggestions.addAll(
      commonTerms
          .where((term) => term.toLowerCase().contains(query.toLowerCase()))
          .take(3),
    );
    
    setState(() {
      _searchSuggestions = suggestions.take(8).toList();
      _showSuggestions = suggestions.isNotEmpty && _searchFocusNode.hasFocus;
    });
  }

  /// Toggle advanced filters visibility
  void _toggleAdvancedFilters() {
    setState(() {
      _showAdvancedFilters = !_showAdvancedFilters;
    });
    
    if (_showAdvancedFilters) {
      _filtersAnimationController.forward();
    } else {
      _filtersAnimationController.reverse();
    }
  }

  /// Perform search with current filters
  void _performSearch() {
    final query = _searchController.text;
    final updatedFilters = _filters.copyWith(
      query: query.isNotEmpty ? query : null,
    );
    
    widget.onSearch(query, updatedFilters);
    
    // Hide suggestions and unfocus
    setState(() {
      _showSuggestions = false;
    });
    _searchFocusNode.unfocus();
  }

  /// Clear all filters
  void _clearFilters() {
    setState(() {
      _searchController.clear();
      _filters = MediaSearchFilters();
      _selectedCollectionIds.clear();
      _searchSuggestions.clear();
      _showSuggestions = false;
    });
    
    widget.onClear?.call();
  }

  /// Apply suggestion
  void _applySuggestion(String suggestion) {
    setState(() {
      _searchController.text = suggestion;
      _showSuggestions = false;
    });
    
    _performSearch();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.6, // Max 60% of screen height
      ),
      child: Card(
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Main search bar
              Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: _buildSearchBar(),
              ),
              
              // Search suggestions
              if (_showSuggestions)
                _buildSuggestions(),
              
              // Advanced filters
              AnimatedBuilder(
                animation: _filtersAnimation,
                builder: (context, child) {
                  return SizeTransition(
                    sizeFactor: _filtersAnimation,
                    child: _buildAdvancedFilters(),
                  );
                },
              ),
              
              // Action buttons
              _buildActionButtons(),
            ],
          ),
        ),
      ),
    );
  }

  /// Build main search bar
  Widget _buildSearchBar() {
    return Row(
      children: [
        // Search field
        Expanded(
          child: TextField(
            controller: _searchController,
            focusNode: _searchFocusNode,
            decoration: InputDecoration(
              hintText: 'Search media files...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchController.text.isNotEmpty
                  ? IconButton(
                      onPressed: () {
                        _searchController.clear();
                        _performSearch();
                      },
                      icon: const Icon(Icons.clear),
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
            ),
            onSubmitted: (_) => _performSearch(),
          ),
        ),
        
        const SizedBox(width: AppSpacing.sm),
        
        // Advanced filters toggle
        IconButton(
          onPressed: _toggleAdvancedFilters,
          icon: Icon(
            _showAdvancedFilters ? Icons.expand_less : Icons.tune,
          ),
          tooltip: 'Advanced filters',
        ),
      ],
    );
  }

  /// Build search suggestions
  Widget _buildSuggestions() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      constraints: const BoxConstraints(maxHeight: 200), // Limit height
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(AppRadius.sm),
        boxShadow: const [AppShadows.md],
      ),
      child: ListView.builder(
        shrinkWrap: true,
        physics: const BouncingScrollPhysics(), // Add scrolling physics
        itemCount: _searchSuggestions.length,
        itemBuilder: (context, index) {
          final suggestion = _searchSuggestions[index];
          
          return ListTile(
            dense: true,
            leading: const Icon(
              Icons.search,
              size: 20,
              color: AppColors.textTertiary,
            ),
            title: Text(
              suggestion,
              style: AppTextStyles.bodyMedium,
            ),
            onTap: () => _applySuggestion(suggestion),
          );
        },
      ),
    );
  }

  /// Build advanced filters
  Widget _buildAdvancedFilters() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: AppColors.border),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Advanced Filters',
            style: AppTextStyles.h6,
          ),
          
          const SizedBox(height: AppSpacing.md),
          
          // Media type filter
          _buildMediaTypeFilter(),
          
          const SizedBox(height: AppSpacing.md),
          
          // Date range filter
          _buildDateRangeFilter(),
          
          const SizedBox(height: AppSpacing.md),
          
          // Tags filter
          if (widget.availableTags != null)
            _buildTagsFilter(),
          
          const SizedBox(height: AppSpacing.md),
          
          // Collection filter
          if (widget.availableCollections != null || _availableCollections.isNotEmpty)
            _buildCollectionFilter(),
          
          const SizedBox(height: AppSpacing.md),
          
          // Sort options
          _buildSortOptions(),
          
          const SizedBox(height: AppSpacing.md),
          
          // Archive filter
          _buildArchiveFilter(),
        ],
      ),
    );
  }

  /// Build media type filter
  Widget _buildMediaTypeFilter() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Media Type',
          style: AppTextStyles.labelLarge,
        ),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm,
          children: MediaType.values.map((type) {
            final isSelected = _filters.mediaType == type;
            
            return FilterChip(
              label: Text(type.name.toUpperCase()),
              selected: isSelected,
              onSelected: (selected) {
                setState(() {
                  _filters = _filters.copyWith(
                    mediaType: selected ? type : null,
                  );
                });
              },
              selectedColor: _getMediaTypeColor(type).withOpacity(0.2),
              checkmarkColor: _getMediaTypeColor(type),
              avatar: Icon(
                _getMediaTypeIcon(type),
                size: 16,
                color: isSelected 
                    ? _getMediaTypeColor(type) 
                    : AppColors.textSecondary,
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Build date range filter
  Widget _buildDateRangeFilter() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Date Range',
          style: AppTextStyles.labelLarge,
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            // Start date
            Expanded(
              child: OutlinedButton(
                onPressed: () => _selectDate(true),
                child: Text(
                  _filters.startDate != null
                      ? '${_filters.startDate!.month}/${_filters.startDate!.day}/${_filters.startDate!.year}'
                      : 'Start Date',
                  style: AppTextStyles.bodyMedium,
                ),
              ),
            ),
            
            const SizedBox(width: AppSpacing.sm),
            
            const Text('to'),
            
            const SizedBox(width: AppSpacing.sm),
            
            // End date
            Expanded(
              child: OutlinedButton(
                onPressed: () => _selectDate(false),
                child: Text(
                  _filters.endDate != null
                      ? '${_filters.endDate!.month}/${_filters.endDate!.day}/${_filters.endDate!.year}'
                      : 'End Date',
                  style: AppTextStyles.bodyMedium,
                ),
              ),
            ),
          ],
        ),
        
        // Quick date filters
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm,
          children: [
            _QuickDateFilter(
              label: 'Today',
              onTap: () => _setQuickDateRange(0),
            ),
            _QuickDateFilter(
              label: 'This Week',
              onTap: () => _setQuickDateRange(7),
            ),
            _QuickDateFilter(
              label: 'This Month',
              onTap: () => _setQuickDateRange(30),
            ),
            _QuickDateFilter(
              label: 'This Year',
              onTap: () => _setQuickDateRange(365),
            ),
          ],
        ),
      ],
    );
  }

  /// Build tags filter
  Widget _buildTagsFilter() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Tags',
          style: AppTextStyles.labelLarge,
        ),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm,
          children: widget.availableTags!.map((tag) {
            final isSelected = _filters.tags?.contains(tag) ?? false;
            
            return FilterChip(
              label: Text(tag),
              selected: isSelected,
              onSelected: (selected) {
                setState(() {
                  final currentTags = _filters.tags?.toList() ?? [];
                  
                  if (selected) {
                    currentTags.add(tag);
                  } else {
                    currentTags.remove(tag);
                  }
                  
                  _filters = _filters.copyWith(
                    tags: currentTags.isNotEmpty ? currentTags : null,
                  );
                });
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Build collection filter
  Widget _buildCollectionFilter() {
    // Use dynamic collections if available, otherwise fall back to static list
    final collections = _availableCollections.isNotEmpty 
        ? _availableCollections 
        : (widget.availableCollections ?? []);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Collections',
              style: AppTextStyles.labelLarge,
            ),
            if (_loadingCollections) ...[
              const SizedBox(width: AppSpacing.sm),
              const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        
        // Multi-select collections container
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: Column(
            children: [
              // Selected collections display
              if (_selectedCollectionIds.isNotEmpty) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  child: Wrap(
                    spacing: AppSpacing.xs,
                    runSpacing: AppSpacing.xs,
                    children: _selectedCollectionIds.map((collectionId) {
                      final collection = _availableCollections
                          .firstWhere((c) => c.id == collectionId, 
                                    orElse: () => MediaCollection(
                                      id: collectionId, 
                                      name: collectionId,
                                      createdBy: '',
                                      isPublic: false,
                                      createdAt: DateTime.now(),
                                    ));
                      return Chip(
                        label: Text(
                          collection.name,
                          style: const TextStyle(fontSize: 12),
                        ),
                        deleteIcon: const Icon(Icons.close, size: 16),
                        onDeleted: () {
                          setState(() {
                            _selectedCollectionIds.remove(collectionId);
                            _updateFiltersWithCollections();
                          });
                        },
                        backgroundColor: AppColors.primary.withOpacity(0.1),
                        side: BorderSide(color: AppColors.primary.withOpacity(0.3)),
                      );
                    }).toList(),
                  ),
                ),
                const Divider(height: 1),
              ],
              
              // Collection selection interface
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Add collections section
                    if (_availableCollections.isNotEmpty || widget.availableCollections != null) ...[
                      Text(
                        'Available Collections',
                        style: const TextStyle(
                          fontWeight: FontWeight.w500,
                          color: AppColors.textSecondary,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      
                      // Available collections grid
                      Wrap(
                        spacing: AppSpacing.sm,
                        runSpacing: AppSpacing.sm,
                        children: [
                          // Dynamic collections from MediaCollection objects
                          if (_availableCollections.isNotEmpty)
                            ..._availableCollections
                                .where((collection) => !_selectedCollectionIds.contains(collection.id))
                                .map((collection) {
                              return _buildCollectionChip(
                                id: collection.id,
                                name: collection.name,
                                isSelected: false,
                                onTap: () {
                                  setState(() {
                                    _selectedCollectionIds.add(collection.id);
                                    _updateFiltersWithCollections();
                                  });
                                },
                              );
                            })
                          
                          // Fallback to static list for backward compatibility
                          else if (widget.availableCollections != null)
                            ...widget.availableCollections!
                                .where((collection) => !_selectedCollectionIds.contains(collection))
                                .map((collection) {
                              return _buildCollectionChip(
                                id: collection,
                                name: collection,
                                isSelected: false,
                                onTap: () {
                                  setState(() {
                                    _selectedCollectionIds.add(collection);
                                    _updateFiltersWithCollections();
                                  });
                                },
                              );
                            }),
                        ],
                      ),
                    ],
                    
                    // Clear all button
                    if (_selectedCollectionIds.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.md),
                      TextButton.icon(
                        onPressed: () {
                          setState(() {
                            _selectedCollectionIds.clear();
                            _updateFiltersWithCollections();
                          });
                        },
                        icon: const Icon(Icons.clear_all, color: Colors.red),
                        label: const Text('Clear all collections', style: TextStyle(color: Colors.red)),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
  
  /// Update filters with current collection selections
  void _updateFiltersWithCollections() {
    _filters = _filters.copyWith(
      collectionIds: _selectedCollectionIds.isEmpty ? null : List.from(_selectedCollectionIds),
      // Clear single collectionId when using multi-select
      collectionId: null,
    );
    
    // Trigger search with updated filters
    _performSearch();
  }

  /// Build sort options
  Widget _buildSortOptions() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Sort By',
          style: AppTextStyles.labelLarge,
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            // Sort field
            Expanded(
              flex: 2,
              child: DropdownButtonFormField<String>(
                value: _filters.sortBy ?? 'created_at',
                decoration: InputDecoration(
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.sm),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.sm,
                  ),
                ),
                items: const [
                  DropdownMenuItem(
                    value: 'created_at',
                    child: Text('Date Created'),
                  ),
                  DropdownMenuItem(
                    value: 'filename',
                    child: Text('Name'),
                  ),
                  DropdownMenuItem(
                    value: 'file_size',
                    child: Text('Size'),
                  ),
                  DropdownMenuItem(
                    value: 'media_type',
                    child: Text('Type'),
                  ),
                ],
                onChanged: (value) {
                  setState(() {
                    _filters = _filters.copyWith(sortBy: value);
                  });
                },
              ),
            ),
            
            const SizedBox(width: AppSpacing.sm),
            
            // Sort order
            Expanded(
              child: DropdownButtonFormField<String>(
                value: _filters.sortOrder ?? 'desc',
                decoration: InputDecoration(
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.sm),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.sm,
                  ),
                ),
                items: const [
                  DropdownMenuItem(
                    value: 'desc',
                    child: Text('Descending'),
                  ),
                  DropdownMenuItem(
                    value: 'asc',
                    child: Text('Ascending'),
                  ),
                ],
                onChanged: (value) {
                  setState(() {
                    _filters = _filters.copyWith(sortOrder: value);
                  });
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Build archive filter toggle
  Widget _buildArchiveFilter() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Archive',
          style: AppTextStyles.labelLarge,
        ),
        const SizedBox(height: AppSpacing.sm),
        FilterChip(
          label: const Text('Show Archived'),
          selected: _filters.isArchived == true,
          onSelected: (selected) {
            setState(() {
              _filters = _filters.copyWith(
                isArchived: selected ? true : null,
              );
            });
          },
          selectedColor: Colors.orange.withOpacity(0.2),
          checkmarkColor: Colors.orange,
          avatar: Icon(
            Icons.archive_outlined,
            size: 16,
            color: _filters.isArchived == true
                ? Colors.orange
                : AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  /// Build action buttons
  Widget _buildActionButtons() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Row(
        children: [
          // Clear button
          OutlinedButton(
            onPressed: _clearFilters,
            child: const Text('Clear'),
          ),
          
          const Spacer(),
          
          // Search button
          ElevatedButton(
            onPressed: _performSearch,
            child: const Text('Search'),
          ),
        ],
      ),
    );
  }

  /// Select date for range filter
  Future<void> _selectDate(bool isStartDate) async {
    final selectedDate = await showDatePicker(
      context: context,
      initialDate: isStartDate
          ? (_filters.startDate ?? DateTime.now())
          : (_filters.endDate ?? DateTime.now()),
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
    );

    if (selectedDate != null) {
      setState(() {
        if (isStartDate) {
          _filters = _filters.copyWith(startDate: selectedDate);
        } else {
          _filters = _filters.copyWith(endDate: selectedDate);
        }
      });
    }
  }

  /// Set quick date range
  void _setQuickDateRange(int days) {
    final now = DateTime.now();
    final startDate = days == 0 
        ? DateTime(now.year, now.month, now.day)
        : now.subtract(Duration(days: days));
    
    setState(() {
      _filters = _filters.copyWith(
        startDate: startDate,
        endDate: now,
      );
    });
  }

  /// Get media type icon
  IconData _getMediaTypeIcon(MediaType type) {
    switch (type) {
      case MediaType.image:
        return Icons.image;
      case MediaType.video:
        return Icons.videocam;
      case MediaType.audio:
        return Icons.audiotrack;
      case MediaType.document:
        return Icons.description;
      case MediaType.pdf:
        return Icons.picture_as_pdf;
      case MediaType.text:
        return Icons.text_snippet;
      case MediaType.archive:
        return Icons.archive;
      case MediaType.other:
        return Icons.insert_drive_file;
    }
  }

  /// Get media type color
  Color _getMediaTypeColor(MediaType type) {
    switch (type) {
      case MediaType.image:
        return AppColors.imageColor;
      case MediaType.video:
        return AppColors.videoColor;
      case MediaType.audio:
        return AppColors.audioColor;
      case MediaType.document:
        return AppColors.documentColor;
      case MediaType.pdf:
        return AppColors.documentColor; // Use same color as document
      case MediaType.text:
        return AppColors.documentColor; // Use same color as document
      case MediaType.archive:
        return AppColors.documentColor; // Use same color as document
      case MediaType.other:
        return AppColors.documentColor; // Use same color as document
    }
  }

  /// Build collection chip
  Widget _buildCollectionChip({
    required String id,
    required String name,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return ActionChip(
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.folder,
            size: 16,
            color: isSelected ? Colors.white : AppColors.textSecondary,
          ),
          const SizedBox(width: AppSpacing.xs),
          Flexible(
            child: Text(
              name,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: isSelected ? Colors.white : AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
      onPressed: onTap,
      backgroundColor: isSelected 
          ? AppColors.primary 
          : AppColors.surfaceVariant,
    );
  }
}

/// Quick date filter chip
class _QuickDateFilter extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const _QuickDateFilter({
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      label: Text(label),
      onPressed: onTap,
      backgroundColor: AppColors.surfaceVariant,
    );
  }
}
