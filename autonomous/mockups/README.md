# PPL Meta — CRUD UX Mockup (throwaway)

## What & why
UI-only Flutter prototype validating the **Unified CRUD UX** for the frontend
(plan: `docs/proposals/UX/unified-crud-ux.md`, §9 mockup phase).

- Fake local state only — no real APIs, auth, or persistence.
- **Not a deliverable.** Port validated patterns to `ppl-meta-frontend`, then delete.

## Run
```bash
cd autonomous/mockups/ppl_meta_mockup
flutter pub get
flutter run -d chrome     # resize window to test mobile / tablet / desktop
# also: flutter run -d macos|android   and: flutter test
```

## Validate
1. **Unified list/toolbar**: grid⇄list toggle, search, refresh.
2. **Filter & sort** (icon): bottom sheet on mobile, popover on desktop; active
   filters show as dismissible chips + a badge dot on the filter icon.
3. **Master/detail is CONTENT-first.** The list stays on the left. The right
   pane shows the **active item's content**, NOT its settings:
   - **Cameras** → live/preview of the active camera.
   - **Collections** → video thumbnails of the active collection.
   - **Individual Groups** → members of the active group.
   - **Triggers & Actions** → stay settings-only (no media).
   Tapping the **settings icon** (on the content bar or the row menu) opens the
   settings editor in the right pane; closing it returns to the content view.
4. **The single UnifiedToggle** (rows, detail header, settings, inside editor):
   flips optimistically; enable *Simulate commit failure* (kebab menu) then flip
   a switch to see the optimistic flip → revert → snackbar; *dangerous* toggles
   ask to confirm first.
5. **Editor surfaces**: Create/Edit → full-screen (narrow), dialog (tablet),
   inline right panel (desktop). The sticky Save/Cancel footer is identical.
6. **L-E-R states**: kebab menu → Loading (skeleton) / Empty / Error (Retry).
7. All four resources share one `ResourceHome` — **a single mental model**.
8. **Light ⇄ Dark theme**: the sun/moon icon in the top-right AppBar toggles
   themes instantly (same seed color, Material 3 dark scheme).

## Layout
```
lib/
  main.dart                            # launcher → pick a resource
  models/mock_data.dart                # fake items + resource descriptors
  screens/resource_home_screen.dart    # unified list + content-first right pane + editor
  screens/editor.dart                  # shared editor body + 3 surfaces
  screens/filter_panel.dart            # shared filter/sort panel
  screens/item_views.dart              # grid/list cards + settings detail view
  ux/breakpoints.dart                  # single breakpoint utility
  ux/unified_toggle.dart               # the one toggle control
```