import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/mvr_people_body_api_client.dart';

/// Minimal MVR People Body list for a media item (posture / height / colors).
class MvrPeopleBodyDetailPanel extends ConsumerStatefulWidget {
  final String mediaUuid;

  const MvrPeopleBodyDetailPanel({super.key, required this.mediaUuid});

  @override
  ConsumerState<MvrPeopleBodyDetailPanel> createState() =>
      _MvrPeopleBodyDetailPanelState();
}

class _MvrPeopleBodyDetailPanelState
    extends ConsumerState<MvrPeopleBodyDetailPanel> {
  List<Map<String, dynamic>> _items = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(MvrPeopleBodyDetailPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.mediaUuid != widget.mediaUuid) {
      _load();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final client = ref.read(mvrPeopleBodyApiClientProvider);
      final items = await client.listForMedia(widget.mediaUuid);
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  static Color? _colorFromHex(String? hex) {
    if (hex == null) return null;
    var s = hex.trim();
    if (s.startsWith('#')) s = s.substring(1);
    if (s.length == 6) s = 'FF$s';
    if (s.length != 8) return null;
    final value = int.tryParse(s, radix: 16);
    if (value == null) return null;
    return Color(value);
  }

  Widget _buildColorRow(dynamic colors) {
    if (colors is! List || colors.isEmpty) {
      return const Text('colors: not computed');
    }
    final chips = <Widget>[];
    for (final c in colors) {
      if (c is! Map || c['hex'] == null) continue;
      final hex = c['hex'].toString();
      final fill = _colorFromHex(hex) ?? Colors.grey;
      final frac = c['fraction'];
      final label = frac is num
          ? '$hex (${(frac * 100).round()}%)'
          : hex;
      chips.add(
        Padding(
          padding: const EdgeInsets.only(right: 10, top: 2, bottom: 2),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 14,
                height: 14,
                decoration: BoxDecoration(
                  color: fill,
                  borderRadius: BorderRadius.circular(3),
                  border: Border.all(color: Colors.black26, width: 1),
                ),
              ),
              const SizedBox(width: 6),
              Text(label, style: const TextStyle(fontSize: 12)),
            ],
          ),
        ),
      );
    }
    if (chips.isEmpty) {
      return Text('colors: $colors');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('colors:', style: TextStyle(fontSize: 12)),
        const SizedBox(height: 4),
        Wrap(children: chips),
      ],
    );
  }

  String _postureLabel(Map<String, dynamic> item) {
    final posture = item['posture']?.toString() ?? 'uncertain';
    final conf = item['posture_confidence'];
    if (conf is num && conf > 0) {
      return '$posture (${(conf * 100).round()}%)';
    }
    return posture;
  }

  bool _showFallen(Map<String, dynamic> item) {
    final fallen = item['fallen']?.toString() ?? 'unknown';
    final conf = item['fallen_confidence'];
    if (fallen != 'unknown') return true;
    return conf is num && conf > 0;
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: Text('Failed to load MVR People Body: $_error'),
      );
    }
    if (_items.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Text(
          'No MVR People Body records for this video yet. Enable Body detection on the camera or run Compute.',
        ),
      );
    }
    return Column(
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh body data',
            onPressed: _load,
          ),
        ),
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: _items.length,
          separatorBuilder: (_, __) => const Divider(height: 1),
          itemBuilder: (context, index) {
            final item = _items[index];
            final heightPx = item['height_px'];
            final fallen = item['fallen']?.toString() ?? 'unknown';
            final colors = item['dominant_colors'];
            final meta = StringBuffer('Posture: ${_postureLabel(item)}');
            if (heightPx != null) {
              meta.write(' · height_px: $heightPx');
            }
            if (_showFallen(item)) {
              meta.write(' · fallen: $fallen');
            }
            return ListTile(
              leading: const Icon(Icons.accessibility_new),
              title: Text(
                'Body ${item['mvr_people_body_uuid']?.toString().substring(0, 8) ?? index}',
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(meta.toString()),
                  const SizedBox(height: 6),
                  _buildColorRow(colors),
                ],
              ),
              isThreeLine: true,
            );
          },
        ),
      ],
    );
  }
}
