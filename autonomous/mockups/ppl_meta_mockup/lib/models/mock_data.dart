/// UI-only fake data. No API, no persistence — just enough to validate the
/// unified CRUD interaction model. Anything here is throwaway.
library;

import 'package:flutter/material.dart';

class MockItem {
  MockItem({
    required this.id,
    required this.name,
    required this.subtitle,
    required this.icon,
    this.enabled = true,
    Map<String, bool>? toggles,
    this.tags = const [],
    required this.created,
    this.primarySetting,
  }) : toggles = toggles ?? {};

  final String id;
  String name;
  String subtitle;
  final IconData icon;
  bool enabled; // header status (on/off)
  final Map<String, bool> toggles; // boolean settings edited in the editor
  List<String> tags;
  final String created;
  final String? primarySetting; // a sample read-only field for the editor

  MockItem copy() => MockItem(
        id: id,
        name: name,
        subtitle: subtitle,
        icon: icon,
        enabled: enabled,
        toggles: Map.of(toggles),
        tags: List.of(tags),
        created: created,
        primarySetting: primarySetting,
      );
}

class MockResource {
  MockResource({
    required this.id,
    required this.name,
    required this.icon,
    required this.defaultGrid,
    required this.items,
    required this.emptyText,
    required this.listHint,
  });

  final String id;
  final String name;
  final IconData icon;
  final bool defaultGrid; // visual objects default to grid, verbose to list
  List<MockItem> items;
  final String emptyText;
  final String listHint;
}

/// The four resources the unified UX targets.
final Map<String, MockResource> kResources = {
  'cameras': MockResource(
    id: 'cameras',
    name: 'Cameras',
    icon: Icons.videocam_outlined,
    defaultGrid: true,
    emptyText: 'No cameras yet. Connect one to get started.',
    listHint: 'Tap a camera to manage its pipeline and settings.',
    items: [
      MockItem(
        id: 'c1',
        name: 'Lobby — Entrance',
        subtitle: 'IP · RTSP · Connected',
        icon: Icons.videocam_outlined,
        enabled: true,
        toggles: {'Live streaming': true, 'Recording': true, 'Auto-detect events': true},
        tags: ['entrance', 'HD'],
        created: '3 days ago',
        primarySetting: 'rtsp://cam.lobby.local:554',
      ),
      MockItem(
        id: 'c2',
        name: 'Warehouse — Bay 1',
        subtitle: 'Edge · Offline',
        icon: Icons.security_outlined,
        enabled: false,
        toggles: {'Live streaming': false, 'Recording': false, 'Auto-detect events': true},
        tags: ['warehouse'],
        created: '1 week ago',
        primarySetting: 'edge://bay1',
      ),
      MockItem(
        id: 'c3',
        name: 'Parking — North',
        subtitle: 'IP · Connected',
        icon: Icons.camera_outlined,
        enabled: true,
        toggles: {'Live streaming': true, 'Recording': false, 'Auto-detect events': true},
        tags: ['outdoor'],
        created: '2 weeks ago',
        primarySetting: 'rtsp://parking.north:554',
      ),
      MockItem(
        id: 'c4',
        name: 'Reception',
        subtitle: 'Microservice · Streaming',
        icon: Icons.videocam_outlined,
        enabled: true,
        toggles: {'Live streaming': true, 'Recording': true, 'Auto-detect events': false},
        tags: ['indoor'],
        created: '1 month ago',
        primarySetting: 'rtsp://reception:554',
      ),
      MockItem(
        id: 'c5',
        name: 'Loading Dock',
        subtitle: 'Edge · Connected',
        icon: Icons.sensors_outlined,
        enabled: true,
        toggles: {'Live streaming': true, 'Recording': false, 'Auto-detect events': true},
        tags: ['docker', 'outdoor'],
        created: '1 month ago',
        primarySetting: 'edge://dock',
      ),
    ],
  ),
  'collections': MockResource(
    id: 'collections',
    name: 'Collections',
    icon: Icons.folder_copy_outlined,
    defaultGrid: true,
    emptyText: 'No collections yet. Create one to organize your media.',
    listHint: 'Tap a collection to open its media and organization settings.',
    items: [
      MockItem(
        id: 'col1',
        name: 'Investigation — July',
        subtitle: '142 items · 6 cameras',
        icon: Icons.folder_outlined,
        enabled: true,
        toggles: {'Privacy guard': true, 'Public': false, 'Auto-organize': true},
        tags: ['active'],
        created: '2 days ago',
        primarySetting: '142 items',
      ),
      MockItem(
        id: 'col2',
        name: 'Marketing Shoots',
        subtitle: '58 items · 2 cameras',
        icon: Icons.folder_open_outlined,
        enabled: true,
        toggles: {'Privacy guard': false, 'Public': true, 'Auto-organize': false},
        tags: ['shared'],
        created: '1 week ago',
        primarySetting: '58 items',
      ),
      MockItem(
        id: 'col3',
        name: 'Archive 2025',
        subtitle: '1 204 items · 12 cameras',
        icon: Icons.inventory_2_outlined,
        enabled: false,
        toggles: {'Privacy guard': true, 'Public': false, 'Auto-organize': false},
        tags: ['archive'],
        created: '8 months ago',
        primarySetting: '1 204 items',
      ),
    ],
  ),
  'groups': MockResource(
    id: 'groups',
    name: 'Individual Groups',
    icon: Icons.groups_outlined,
    defaultGrid: true,
    emptyText: 'No groups yet. Create one to track known individuals.',
    listHint: 'Tap a group to manage its members and analysis.',
    items: [
      MockItem(
        id: 'g1',
        name: 'Presence Individuals 7',
        subtitle: '12 members · Public',
        icon: Icons.groups_outlined,
        enabled: true,
        toggles: {'Visibility (public)': true, 'Auto-merge duplicates': false, 'Notify on new member': true},
        tags: ['presence'],
        created: 'yesterday',
        primarySetting: '12 members',
      ),
      MockItem(
        id: 'g2',
        name: 'Staff — Day Shift',
        subtitle: '34 members · Private',
        icon: Icons.badge_outlined,
        enabled: true,
        toggles: {'Visibility (public)': false, 'Auto-merge duplicates': true, 'Notify on new member': false},
        tags: ['staff'],
        created: '1 month ago',
        primarySetting: '34 members',
      ),
      MockItem(
        id: 'g3',
        name: 'Frequent Visitors',
        subtitle: '8 members · Private',
        icon: Icons.person_search_outlined,
        enabled: true,
        toggles: {'Visibility (public)': false, 'Auto-merge duplicates': true, 'Notify on new member': true},
        tags: ['analysis'],
        created: '2 months ago',
        primarySetting: '8 members',
      ),
    ],
  ),
  'triggers': MockResource(
    id: 'triggers',
    name: 'Triggers & Actions',
    icon: Icons.precision_manufacturing_outlined,
    defaultGrid: false,
    emptyText: 'No triggers yet. Create one to automate alerts.',
    listHint: 'Triggers are verbose — they default to a list layout.',
    items: [
      MockItem(
        id: 't1',
        name: 'After-hours motion',
        subtitle: 'Cameras: all · 22:00–06:00 · alert',
        icon: Icons.alarm_on_outlined,
        enabled: true,
        toggles: {'Enabled': true, 'Email alert': true, 'Webhook': false, 'Cooldown 5 min': true},
        tags: ['motion'],
        created: '3 days ago',
        primarySetting: 'people > 0',
      ),
      MockItem(
        id: 't2',
        name: 'Age-sensitive zones',
        subtitle: 'Camera: lobby · always · log',
        icon: Icons.child_care_outlined,
        enabled: false,
        toggles: {'Enabled': false, 'Email alert': false, 'Webhook': true, 'Cooldown 5 min': false},
        tags: ['demographics'],
        created: '1 week ago',
        primarySetting: 'age < 16',
      ),
      MockItem(
        id: 't3',
        name: 'Crowd threshold',
        subtitle: 'Cameras: warehouse · always · email',
        icon: Icons.people_alt_outlined,
        enabled: true,
        toggles: {'Enabled': true, 'Email alert': true, 'Webhook': true, 'Cooldown 5 min': true},
        tags: ['count'],
        created: '2 weeks ago',
        primarySetting: 'people > 25',
      ),
    ],
  ),
};