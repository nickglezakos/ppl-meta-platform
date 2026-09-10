import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/services/models_catalog_client.dart';
import '../core/theme/app_theme.dart';
import '../widgets/custom_app_bar.dart';

class ModelsScreen extends ConsumerStatefulWidget {
  const ModelsScreen({super.key, this.initialTab = 0});

  final int initialTab;

  @override
  ConsumerState<ModelsScreen> createState() => _ModelsScreenState();
}

class _ModelsScreenState extends ConsumerState<ModelsScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  Object? _error;
  List<dynamic> _models = const [];
  List<dynamic> _assignments = const [];
  List<dynamic> _recipes = const [];
  List<dynamic> _goldenSets = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 4, vsync: this, initialIndex: widget.initialTab.clamp(0, 3));
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final client = ref.read(modelsCatalogClientProvider);
      final models = await client.listModels();
      final assignments = await client.listAssignments();
      final recipes = await client.listRecipes();
      final goldenSets = await client.listGoldenSets();
      if (!mounted) return;
      setState(() {
        _models = models;
        _assignments = assignments;
        _recipes = recipes;
        _goldenSets = goldenSets;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Models',
        showBackButton: true,
        showHomeButton: true,
      ),
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          TabBar(
            controller: _tabs,
            isScrollable: true,
            tabs: const [
              Tab(text: 'Catalog'),
              Tab(text: 'Pipelines'),
              Tab(text: 'Assignments'),
              Tab(text: 'Golden sets'),
            ],
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(child: Text('Could not load catalog: $_error'))
                    : TabBarView(
                        controller: _tabs,
                        children: [
                          _CatalogTab(models: _models, onOpen: _openModel, onRefresh: _load),
                          _PipelinesTab(
                            recipes: _recipes,
                            models: _models,
                            onActivateRecipe: _activateRecipe,
                            onCreateRecipe: _createRecipe,
                          ),
                          _AssignmentsTab(
                            assignments: _assignments,
                            models: _models,
                            recipes: _recipes,
                            onActivate: _activateAssignment,
                            onActivateRecipe: _activateRecipe,
                          ),
                          _GoldenSetsTab(sets: _goldenSets),
                        ],
                      ),
          ),
        ],
      ),
    );
  }

  void _openModel(Map<String, dynamic> model) {
    context.go('/models/${model['model_id']}');
  }

  Future<void> _activateAssignment({
    required String modelId,
    required String version,
    required String path,
    required String scopeType,
    required String scopeId,
    bool shadow = false,
  }) async {
    try {
      await ref.read(modelsCatalogClientProvider).activate(
            modelId: modelId,
            version: version,
            path: path,
            scopeType: scopeType,
            scopeId: scopeId,
            shadow: shadow,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Activated $modelId on $path')),
      );
      await _load();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Activate failed: $error')),
      );
    }
  }

  Future<void> _activateRecipe({
    required String recipeId,
    required String path,
    required String scopeType,
    required String scopeId,
    String capability = 'face_detection',
    bool shadow = false,
  }) async {
    try {
      await ref.read(modelsCatalogClientProvider).activateRecipe(
            recipeId: recipeId,
            path: path,
            scopeType: scopeType,
            scopeId: scopeId,
            capability: capability,
            shadow: shadow,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Activated pipeline $recipeId on $path')),
      );
      await _load();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Pipeline activate failed: $error')),
      );
    }
  }

  Future<void> _createRecipe({
    required String recipeId,
    required String displayName,
    required String kind,
    required List<Map<String, String>> steps,
    String capability = 'face_detection',
  }) async {
    try {
      await ref.read(modelsCatalogClientProvider).createRecipe(
            recipeId: recipeId,
            displayName: displayName,
            kind: kind,
            steps: steps,
            capability: capability,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Created pipeline $recipeId')),
      );
      await _load();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Create pipeline failed: $error')),
      );
    }
  }
}

class _CatalogTab extends ConsumerWidget {
  const _CatalogTab({
    required this.models,
    required this.onOpen,
    required this.onRefresh,
  });

  final List<dynamic> models;
  final void Function(Map<String, dynamic> model) onOpen;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: () => _showUploadDialog(context, ref),
              icon: const Icon(Icons.upload_file),
              label: const Text('Upload model'),
            ),
          ),
        ),
        Expanded(
          child: models.isEmpty
              ? const Center(child: Text('No models registered.'))
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: models.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final model = Map<String, dynamic>.from(models[index] as Map);
                    final versions =
                        List<dynamic>.from(model['versions'] as List? ?? const []);
                    return Card(
                      child: ListTile(
                        title: Text(
                          model['display_name']?.toString() ??
                              model['model_id'].toString(),
                        ),
                        subtitle: Text(
                          '${model['capability']} · ${model['origin']} · ${versions.length} version(s)',
                        ),
                        trailing: versions.isEmpty
                            ? null
                            : TextButton(
                                onPressed: () async {
                                  final version = Map<String, dynamic>.from(
                                    versions.first as Map,
                                  );
                                  final status = version['status']?.toString() ?? '';
                                  if (status == 'uploaded' || status == 'failed') {
                                    try {
                                      await ref
                                          .read(modelsCatalogClientProvider)
                                          .validateVersion(
                                            modelId: model['model_id'].toString(),
                                            version: version['version'].toString(),
                                          );
                                      if (context.mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          const SnackBar(content: Text('Validate complete')),
                                        );
                                      }
                                      await onRefresh();
                                    } catch (error) {
                                      if (context.mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(content: Text('Validate failed: $error')),
                                        );
                                      }
                                    }
                                  } else {
                                    onOpen(model);
                                  }
                                },
                                child: Text(
                                  (Map<String, dynamic>.from(versions.first as Map)['status']
                                              ?.toString() ==
                                          'uploaded')
                                      ? 'Validate'
                                      : 'Open',
                                ),
                              ),
                        onTap: () => onOpen(model),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Future<void> _showUploadDialog(BuildContext context, WidgetRef ref) async {
    final modelIdCtrl = TextEditingController(text: 'user-face-haar');
    final nameCtrl = TextEditingController(text: 'Uploaded Haar');
    final versionCtrl = TextEditingController(text: '1.0.0');
    String? pickedName;
    Uint8List? pickedBytes;
    var runtime = 'haar';
    var busy = false;

    await showDialog<void>(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setLocal) {
            return AlertDialog(
              title: const Text('Upload model'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: modelIdCtrl,
                    decoration: const InputDecoration(labelText: 'model_id'),
                  ),
                  TextField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(labelText: 'Display name'),
                  ),
                  TextField(
                    controller: versionCtrl,
                    decoration: const InputDecoration(labelText: 'Version'),
                  ),
                  DropdownButtonFormField<String>(
                    value: runtime,
                    decoration: const InputDecoration(labelText: 'Runtime'),
                    items: const [
                      DropdownMenuItem(value: 'haar', child: Text('Haar XML')),
                      DropdownMenuItem(value: 'onnx', child: Text('ONNX / YOLO')),
                    ],
                    onChanged: (value) {
                      if (value != null) setLocal(() => runtime = value);
                    },
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: busy
                        ? null
                        : () async {
                            final result = await FilePicker.platform.pickFiles(
                              withData: true,
                              type: FileType.custom,
                              allowedExtensions: const ['xml', 'onnx'],
                            );
                            if (result == null || result.files.isEmpty) return;
                            final file = result.files.first;
                            setLocal(() {
                              pickedName = file.name;
                              pickedBytes = file.bytes;
                              if ((file.extension ?? '').toLowerCase() == 'onnx') {
                                runtime = 'onnx';
                              } else if ((file.extension ?? '').toLowerCase() == 'xml') {
                                runtime = 'haar';
                              }
                            });
                          },
                    icon: const Icon(Icons.attach_file),
                    label: Text(pickedName ?? 'Pick Haar XML or ONNX'),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: busy ? null : () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                TextButton(
                  onPressed: busy
                      ? null
                      : () async {
                          final bytes = pickedBytes;
                          final filename = pickedName;
                          if (bytes == null || filename == null) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Pick a file first')),
                            );
                            return;
                          }
                          setLocal(() => busy = true);
                          try {
                            final client = ref.read(modelsCatalogClientProvider);
                            final modelId = modelIdCtrl.text.trim();
                            try {
                              await client.createModel(
                                modelId: modelId,
                                displayName: nameCtrl.text.trim(),
                              );
                            } catch (_) {
                              // Model may already exist; continue to version upload.
                            }
                            await client.uploadVersion(
                              modelId: modelId,
                              version: versionCtrl.text.trim(),
                              runtime: runtime,
                              bytes: bytes,
                              filename: filename,
                              latencyClass:
                                  runtime == 'haar' ? 'preview' : 'bulk',
                              compatiblePaths: runtime == 'haar'
                                  ? 'preview,instant,bulk'
                                  : 'bulk',
                            );
                            if (context.mounted) Navigator.pop(context);
                            await onRefresh();
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(
                                    'Uploaded $filename — use Validate when status is uploaded',
                                  ),
                                ),
                              );
                            }
                          } catch (error) {
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Upload failed: $error')),
                              );
                            }
                          } finally {
                            setLocal(() => busy = false);
                          }
                        },
                  child: Text(busy ? 'Uploading…' : 'Upload'),
                ),
              ],
            );
          },
        );
      },
    );
  }
}

class _PipelinesTab extends StatefulWidget {
  const _PipelinesTab({
    required this.recipes,
    required this.models,
    required this.onActivateRecipe,
    required this.onCreateRecipe,
  });

  final List<dynamic> recipes;
  final List<dynamic> models;
  final Future<void> Function({
    required String recipeId,
    required String path,
    required String scopeType,
    required String scopeId,
    String capability,
    bool shadow,
  }) onActivateRecipe;
  final Future<void> Function({
    required String recipeId,
    required String displayName,
    required String kind,
    required List<Map<String, String>> steps,
    String capability,
  }) onCreateRecipe;

  @override
  State<_PipelinesTab> createState() => _PipelinesTabState();
}

class _PipelinesTabState extends State<_PipelinesTab> {
  String _kind = 'single';
  String? _proposalModel;
  String? _refineModel;
  final _recipeId = TextEditingController();
  final _displayName = TextEditingController();

  @override
  void dispose() {
    _recipeId.dispose();
    _displayName.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get _faceModels {
    return widget.models
        .map((item) => Map<String, dynamic>.from(item as Map))
        .where((model) => model['capability'] == 'face_detection')
        .toList();
  }

  String _versionFor(String modelId) {
    final match = _faceModels.where((model) => model['model_id'] == modelId);
    if (match.isEmpty) return '1.0.0';
    final versions = List<dynamic>.from(match.first['versions'] as List? ?? const []);
    if (versions.isEmpty) return '1.0.0';
    return Map<String, dynamic>.from(versions.first as Map)['version']?.toString() ??
        '1.0.0';
  }

  @override
  Widget build(BuildContext context) {
    final models = _faceModels;
    _proposalModel ??= models.isEmpty ? null : models.first['model_id']?.toString();
    _refineModel ??= models.length > 1
        ? models[1]['model_id']?.toString()
        : _proposalModel;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Pipelines are single-stage or two-stage (proposal → refine). '
          'Same template applies to face and body.',
        ),
        const SizedBox(height: 12),
        ...widget.recipes.map((raw) {
          final recipe = Map<String, dynamic>.from(raw as Map);
          final stages = List<dynamic>.from(recipe['stages'] as List? ?? const []);
          final stageText = stages
              .map((s) {
                final stage = Map<String, dynamic>.from(s as Map);
                return '${stage['role']}:${stage['model_id']}';
              })
              .join(' → ');
          return Card(
            child: ListTile(
              title: Text(recipe['display_name']?.toString() ?? recipe['recipe_id'].toString()),
              subtitle: Text(
                '${recipe['capability']} · ${recipe['kind']} · $stageText',
              ),
              trailing: Wrap(
                spacing: 4,
                children: [
                  TextButton(
                    onPressed: () => widget.onActivateRecipe(
                      recipeId: recipe['recipe_id'].toString(),
                      path: 'instant',
                      scopeType: 'platform',
                      scopeId: '',
                      capability: recipe['capability']?.toString() ?? 'face_detection',
                    ),
                    child: const Text('Instant'),
                  ),
                  TextButton(
                    onPressed: () => widget.onActivateRecipe(
                      recipeId: recipe['recipe_id'].toString(),
                      path: 'bulk',
                      scopeType: 'platform',
                      scopeId: '',
                      capability: recipe['capability']?.toString() ?? 'face_detection',
                    ),
                    child: const Text('Bulk'),
                  ),
                ],
              ),
            ),
          );
        }),
        const Divider(height: 32),
        const Text('Create pipeline', style: TextStyle(fontWeight: FontWeight.bold)),
        TextField(
          controller: _recipeId,
          decoration: const InputDecoration(labelText: 'recipe_id'),
        ),
        TextField(
          controller: _displayName,
          decoration: const InputDecoration(labelText: 'Display name'),
        ),
        DropdownButtonFormField<String>(
          value: _kind,
          decoration: const InputDecoration(labelText: 'Kind'),
          items: const [
            DropdownMenuItem(value: 'single', child: Text('Single stage')),
            DropdownMenuItem(value: 'two_stage', child: Text('Two-stage')),
          ],
          onChanged: (value) => setState(() => _kind = value ?? 'single'),
        ),
        DropdownButtonFormField<String>(
          value: models.any((m) => m['model_id'] == _proposalModel) ? _proposalModel : null,
          decoration: InputDecoration(
            labelText: _kind == 'single' ? 'Model' : 'Proposal (light)',
          ),
          items: models
              .map(
                (model) => DropdownMenuItem(
                  value: model['model_id']?.toString(),
                  child: Text(
                    model['display_name']?.toString() ?? model['model_id'].toString(),
                  ),
                ),
              )
              .toList(),
          onChanged: (value) => setState(() => _proposalModel = value),
        ),
        if (_kind == 'two_stage')
          DropdownButtonFormField<String>(
            value: models.any((m) => m['model_id'] == _refineModel) ? _refineModel : null,
            decoration: const InputDecoration(labelText: 'Refine (quality)'),
            items: models
                .map(
                  (model) => DropdownMenuItem(
                    value: model['model_id']?.toString(),
                    child: Text(
                      model['display_name']?.toString() ?? model['model_id'].toString(),
                    ),
                  ),
                )
                .toList(),
            onChanged: (value) => setState(() => _refineModel = value),
          ),
        const SizedBox(height: 12),
        FilledButton(
          onPressed: _proposalModel == null
              ? null
              : () {
                  final steps = <Map<String, String>>[
                    {
                      'role': _kind == 'single' ? 'single' : 'proposal',
                      'model_id': _proposalModel!,
                      'version': _versionFor(_proposalModel!),
                    },
                  ];
                  if (_kind == 'two_stage' && _refineModel != null) {
                    steps.add({
                      'role': 'refine',
                      'model_id': _refineModel!,
                      'version': _versionFor(_refineModel!),
                    });
                  }
                  widget.onCreateRecipe(
                    recipeId: _recipeId.text.trim().isEmpty
                        ? 'custom-${DateTime.now().millisecondsSinceEpoch}'
                        : _recipeId.text.trim(),
                    displayName: _displayName.text.trim().isEmpty
                        ? 'Custom $_kind pipeline'
                        : _displayName.text.trim(),
                    kind: _kind,
                    steps: steps,
                  );
                },
          child: const Text('Create pipeline'),
        ),
      ],
    );
  }
}

class _AssignmentsTab extends StatefulWidget {
  const _AssignmentsTab({
    required this.assignments,
    required this.models,
    required this.recipes,
    required this.onActivate,
    required this.onActivateRecipe,
  });

  final List<dynamic> assignments;
  final List<dynamic> models;
  final List<dynamic> recipes;
  final Future<void> Function({
    required String modelId,
    required String version,
    required String path,
    required String scopeType,
    required String scopeId,
    bool shadow,
  }) onActivate;
  final Future<void> Function({
    required String recipeId,
    required String path,
    required String scopeType,
    required String scopeId,
    String capability,
    bool shadow,
  }) onActivateRecipe;

  @override
  State<_AssignmentsTab> createState() => _AssignmentsTabState();
}

class _AssignmentsTabState extends State<_AssignmentsTab> {
  String _path = 'instant';
  String _scopeType = 'camera';
  String? _recipeId;
  bool _shadow = false;
  final _cameraId = TextEditingController();

  @override
  void dispose() {
    _cameraId.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get _faceRecipes {
    return widget.recipes
        .map((item) => Map<String, dynamic>.from(item as Map))
        .where((recipe) => recipe['capability'] == 'face_detection')
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final recipes = _faceRecipes;
    _recipeId ??= recipes.isEmpty ? null : recipes.first['recipe_id']?.toString();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Assign a single/two-stage pipeline to a camera or platform path. '
          'Shadow keeps detections out of MVR.',
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          value: recipes.any((r) => r['recipe_id'] == _recipeId) ? _recipeId : null,
          decoration: const InputDecoration(labelText: 'Pipeline'),
          items: recipes
              .map(
                (recipe) => DropdownMenuItem(
                  value: recipe['recipe_id']?.toString(),
                  child: Text(
                    '${recipe['display_name']} (${recipe['kind']})',
                  ),
                ),
              )
              .toList(),
          onChanged: (value) => setState(() => _recipeId = value),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          value: _path,
          decoration: const InputDecoration(labelText: 'Path'),
          items: const [
            DropdownMenuItem(value: 'instant', child: Text('Instant')),
            DropdownMenuItem(value: 'bulk', child: Text('Bulk / recording')),
            DropdownMenuItem(value: 'preview', child: Text('Preview')),
          ],
          onChanged: (value) => setState(() => _path = value ?? 'instant'),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          value: _scopeType,
          decoration: const InputDecoration(labelText: 'Scope'),
          items: const [
            DropdownMenuItem(value: 'camera', child: Text('Camera')),
            DropdownMenuItem(value: 'platform', child: Text('Platform default')),
          ],
          onChanged: (value) => setState(() => _scopeType = value ?? 'camera'),
        ),
        if (_scopeType == 'camera') ...[
          const SizedBox(height: 8),
          TextField(
            controller: _cameraId,
            decoration: const InputDecoration(labelText: 'Camera device ID'),
          ),
        ],
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Shadow (serving=false)'),
          value: _shadow,
          onChanged: (value) => setState(() => _shadow = value),
        ),
        const SizedBox(height: 12),
        FilledButton(
          onPressed: _recipeId == null
              ? null
              : () => widget.onActivateRecipe(
                    recipeId: _recipeId!,
                    path: _path,
                    scopeType: _scopeType,
                    scopeId: _scopeType == 'camera' ? _cameraId.text.trim() : '',
                    shadow: _shadow,
                  ),
          child: const Text('Activate pipeline'),
        ),
        const Divider(height: 32),
        const Text('Current assignments', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        ...widget.assignments.map((raw) {
          final row = Map<String, dynamic>.from(raw as Map);
          final target = row['recipe_id']?.toString().isNotEmpty == true
              ? 'recipe:${row['recipe_id']}'
              : '${row['model_id']}@${row['version']}';
          return ListTile(
            dense: true,
            title: Text('$target'),
            subtitle: Text(
              '${row['capability']} · ${row['path']} · ${row['scope_type']}:${row['scope_id']} '
              '${row['shadow'] == true ? '· shadow' : ''}',
            ),
          );
        }),
      ],
    );
  }
}

class _GoldenSetsTab extends StatelessWidget {
  const _GoldenSetsTab({required this.sets});

  final List<dynamic> sets;

  @override
  Widget build(BuildContext context) {
    if (sets.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Text('No golden sets registered yet.'),
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: sets.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final set = Map<String, dynamic>.from(sets[index] as Map);
        final items = List<dynamic>.from(set['items'] as List? ?? const []);
        return Card(
          child: ListTile(
            title: Text(set['display_name']?.toString() ?? set['set_id'].toString()),
            subtitle: Text(
              '${set['capability']} · ${set['scope']} · ${items.length} item(s)',
            ),
          ),
        );
      },
    );
  }
}

class ModelDetailScreen extends ConsumerStatefulWidget {
  const ModelDetailScreen({super.key, required this.modelId});

  final String modelId;

  @override
  ConsumerState<ModelDetailScreen> createState() => _ModelDetailScreenState();
}

class _ModelDetailScreenState extends ConsumerState<ModelDetailScreen> {
  Map<String, dynamic>? _model;
  Object? _error;
  bool _loading = true;
  final Map<String, List<dynamic>> _runsByVersion = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final client = ref.read(modelsCatalogClientProvider);
      final models = await client.listModels();
      final match = models.where((item) => (item as Map)['model_id'] == widget.modelId);
      if (match.isEmpty) {
        if (!mounted) return;
        setState(() {
          _model = null;
          _loading = false;
        });
        return;
      }
      final model = Map<String, dynamic>.from(match.first as Map);
      final versions = List<dynamic>.from(model['versions'] as List? ?? const []);
      final runsByVersion = <String, List<dynamic>>{};
      for (final raw in versions) {
        final version = Map<String, dynamic>.from(raw as Map);
        final versionId = version['version']?.toString() ?? '';
        if (versionId.isEmpty) continue;
        try {
          runsByVersion[versionId] = await client.listValidationRuns(
            modelId: widget.modelId,
            version: versionId,
          );
        } catch (_) {
          runsByVersion[versionId] = const [];
        }
      }
      if (!mounted) return;
      setState(() {
        _model = model;
        _runsByVersion
          ..clear()
          ..addAll(runsByVersion);
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error;
        _loading = false;
      });
    }
  }

  Future<void> _validate(String version) async {
    try {
      await ref.read(modelsCatalogClientProvider).validateVersion(
            modelId: widget.modelId,
            version: version,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Validated $version')),
      );
      await _load();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Validate failed: $error')),
      );
    }
  }

  Future<void> _activate(String version, String path, {bool shadow = false}) async {
    try {
      await ref.read(modelsCatalogClientProvider).activate(
            modelId: widget.modelId,
            version: version,
            path: path,
            scopeType: 'platform',
            scopeId: '',
            shadow: shadow,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Activated ${widget.modelId}@$version on $path')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Activate failed: $error')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: widget.modelId,
        showBackButton: true,
        showHomeButton: true,
      ),
      backgroundColor: AppColors.background,
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text('Could not load model: $_error'))
              : _model == null
                  ? const Center(child: Text('Model not found'))
                  : _buildBody(),
    );
  }

  Widget _buildBody() {
    final model = _model!;
    final versions = List<dynamic>.from(model['versions'] as List? ?? const []);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          model['display_name']?.toString() ?? widget.modelId,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 8),
        Text('Capability: ${model['capability']}'),
        Text('Origin: ${model['origin']}'),
        const SizedBox(height: 8),
        const Text('Instant p95 budget: < 400 ms/frame when path includes instant.'),
        const SizedBox(height: 16),
        if (versions.isEmpty)
          const Text('No versions uploaded yet.')
        else
          ...versions.map((raw) {
            final version = Map<String, dynamic>.from(raw as Map);
            final versionId = version['version']?.toString() ?? '';
            final status = version['status']?.toString() ?? '';
            final artifacts =
                List<dynamic>.from(version['artifacts'] as List? ?? const []);
            final runs = _runsByVersion[versionId] ?? const [];
            final latestRun = runs.isEmpty
                ? null
                : Map<String, dynamic>.from(runs.first as Map);
            final p95 = latestRun?['p95_latency_ms'];
            final meanIou = latestRun?['mean_iou'];
            return Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'v$versionId · ${version['runtime']} · $status',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'latency ${version['latency_class']} · paths ${version['compatible_paths']}',
                    ),
                    if (p95 != null || meanIou != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        'validation p95=${p95 ?? '—'} ms · IoU=${meanIou ?? '—'}',
                      ),
                    ],
                    if (artifacts.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      const Text('Artifacts'),
                      ...artifacts.map((rawArtifact) {
                        final artifact =
                            Map<String, dynamic>.from(rawArtifact as Map);
                        final sha = artifact['sha256']?.toString() ?? '';
                        final shortSha =
                            sha.length > 12 ? '${sha.substring(0, 12)}…' : sha;
                        return Text(
                          '• ${artifact['filename']} · $shortSha · ${artifact['size_bytes']} bytes',
                        );
                      }),
                    ],
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        if (status == 'uploaded' || status == 'failed')
                          TextButton(
                            onPressed: () => _validate(versionId),
                            child: const Text('Validate'),
                          ),
                        if (status == 'ready') ...[
                          TextButton(
                            onPressed: () => _activate(versionId, 'instant'),
                            child: const Text('Activate instant'),
                          ),
                          TextButton(
                            onPressed: () => _activate(versionId, 'bulk'),
                            child: const Text('Activate bulk'),
                          ),
                          TextButton(
                            onPressed: () =>
                                _activate(versionId, 'instant', shadow: true),
                            child: const Text('Shadow instant'),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            );
          }),
        const SizedBox(height: 12),
        TextButton(
          onPressed: () => context.go('/models'),
          child: const Text('Back to catalog'),
        ),
      ],
    );
  }
}
