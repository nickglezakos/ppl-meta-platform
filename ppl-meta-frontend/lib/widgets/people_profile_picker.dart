import 'package:flutter/material.dart';

import '../models/presence_models.dart';
import '../services/presence_api_client.dart';

/// Picker for linking a Presence People Profile (PPP) to an individual-group
/// member. Shows the current PPP state, lets the operator pick an existing PPP
/// (autocomplete) or create a new one, and links it to this member.
class PeopleProfilePicker extends StatefulWidget {
  final String groupId;
  final String individualId;
  final PresenceApiClient apiClient;
  final VoidCallback? onChanged;

  const PeopleProfilePicker({
    super.key,
    required this.groupId,
    required this.individualId,
    required this.apiClient,
    this.onChanged,
  });

  @override
  State<PeopleProfilePicker> createState() => _PeopleProfilePickerState();
}

class _PeopleProfilePickerState extends State<PeopleProfilePicker> {
  PresencePeopleProfile? _profile;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadCurrent();
  }

  Future<void> _loadCurrent() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final resp = await widget.apiClient.lookupPeopleProfileByMember(widget.individualId);
    if (!mounted) return;
    setState(() {
      _profile = resp.success ? resp.data : _profile;
      _error = resp.success ? null : resp.error;
      _loading = false;
    });
  }

  Future<void> _pick() async {
    final picked = await showDialog<PresencePeopleProfile>(
      context: context,
      builder: (context) => _PeopleProfilePickDialog(
        apiClient: widget.apiClient,
        groupId: widget.groupId,
        individualId: widget.individualId,
      ),
    );
    if (picked != null && mounted) {
      await _loadCurrent();
      widget.onChanged?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Row(
        children: [
          SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 8),
          Text('Loading profile…'),
        ],
      );
    }
    final profile = _profile;
    final label = profile != null ? 'Profile: ${profile.name}' : 'No profile';
    final color = profile != null ? Colors.green : Colors.grey;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.badge_outlined, size: 16, color: color),
            const SizedBox(width: 6),
            Text(label, style: TextStyle(color: color, fontSize: 13)),
          ],
        ),
        OutlinedButton.icon(
          icon: const Icon(Icons.link, size: 16),
          label: Text(profile != null ? 'Change' : 'Link / Create'),
          onPressed: _pick,
        ),
        if (_error != null)
          Text(_error!, style: const TextStyle(color: Colors.orangeAccent, fontSize: 12)),
      ],
    );
  }
}

class _PeopleProfilePickDialog extends StatefulWidget {
  final PresenceApiClient apiClient;
  final String groupId;
  final String individualId;

  const _PeopleProfilePickDialog({
    required this.apiClient,
    required this.groupId,
    required this.individualId,
  });

  @override
  State<_PeopleProfilePickDialog> createState() => _PeopleProfilePickDialogState();
}

class _PeopleProfilePickDialogState extends State<_PeopleProfilePickDialog> {
  List<PresencePeopleProfile> _profiles = [];
  bool _loading = true;
  bool _saving = false;
  String? _error;
  final TextEditingController _search = TextEditingController();
  final TextEditingController _name = TextEditingController();
  PresencePeopleProfile? _selected;

  @override
  void initState() {
    super.initState();
    _searchProfiles('');
  }

  Future<void> _searchProfiles(String query) async {
    setState(() => _loading = true);
    final resp = await widget.apiClient.listPeopleProfiles(query: query);
    if (!mounted) return;
    setState(() {
      _profiles = resp.success ? (resp.data ?? _profiles) : _profiles;
      _error = resp.success ? null : resp.error;
      _loading = false;
    });
  }

  Future<void> _submit() async {
    setState(() => _saving = true);
    try {
      PresencePeopleProfile? profile = _selected;
      final typedName = _name.text.trim();
      if (profile == null && typedName.isEmpty) {
        setState(() {
          _saving = false;
          _error = 'Pick an existing profile or enter a new name.';
        });
        return;
      }
      if (profile == null) {
        final created = await widget.apiClient.createPeopleProfile(name: typedName);
        if (!created.success || created.data == null) {
          setState(() {
            _saving = false;
            _error = created.error ?? 'Failed to create profile';
          });
          return;
        }
        profile = created.data;
      }
      await widget.apiClient.linkMemberToPeopleProfile(
        pppUuid: profile!.pppUuid,
        groupId: widget.groupId,
        individualId: widget.individualId,
      );
      if (mounted) {
        Navigator.pop(context, profile);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _saving = false;
          _error = 'Error: $e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('People Profile'),
      content: SizedBox(
        width: 360,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _search,
              decoration: const InputDecoration(
                labelText: 'Search existing profiles',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onChanged: (v) => _searchProfiles(v),
            ),
            const SizedBox(height: 12),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(12),
                child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
              )
            else ...[
              if (_profiles.isNotEmpty) ...[
                Flexible(
                  child: ListView(
                    shrinkWrap: true,
                    children: _profiles.map((p) {
                      return ListTile(
                        dense: true,
                        title: Text(p.name),
                        subtitle: p.email != null ? Text(p.email!) : null,
                        selected: _selected?.pppUuid == p.pppUuid,
                        trailing: const Icon(Icons.add_link, size: 18),
                        onTap: () => setState(() => _selected = p),
                      );
                    }).toList(),
                  ),
                ),
                const Divider(),
              ] else
                const Padding(
                  padding: EdgeInsets.all(8),
                  child: Text('No profiles found. Create one below.'),
                ),
            ],
            TextField(
              controller: _name,
              decoration: const InputDecoration(
                labelText: 'Or create new profile name',
                prefixIcon: Icon(Icons.person_add),
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 12)),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        FilledButton(
          onPressed: _saving ? null : _submit,
          child: _saving
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Link'),
        ),
      ],
    );
  }
}