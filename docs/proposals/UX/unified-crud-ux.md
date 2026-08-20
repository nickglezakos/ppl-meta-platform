# Unified CRUD UX for Data Objects — Frontend UX Proposal

**Date**: 18 August 2026
**Status**: Draft
**Target**: `ppl-meta-frontend` (Flutter / Riverpod / GoRouter — web + mobile)

---

## Purpose

The PPL Meta frontend exposes four management screens that all operate on the
same conceptual thing — a **"data object"** with a list view, a detail view, and
create / edit / delete actions:

| Screen | Route | Current Screen |
|--------|-------|----------------|
| **Cameras** | `/#/cameras` | `lib/presentation/screens/cameras/cameras_screen.dart` |
| **Collections** | `/#/collections` | `lib/screens/collections_screen.dart` |
| **Individual Groups** | `/#/individual-groups` (+ `/individual-groups/:groupId`) | `lib/screens/individual_groups_screen.dart` |
| **Triggers** | `/#/triggers` | `lib/screens/triggers_screen.dart` |

Today these four screens were built independently and follow **different** UX
patterns: some list cards in a grid, some use dialogs for input, some put
toggles in the AppBar, some render status as badge toggles, and responsive
behavior is re-implemented ad-hoc per screen (`MediaQuery`, `LayoutBuilder`).
This inconsistency is most visible on smaller screens, where the same action
often requires different gestures/paths depending on which object you are editing.

This document is a **high-level UX proposal**. It defines the target user
experience (not the implementation) — a single, unified, mobile-first mental
model for how users create, read, update, search, sort, filter and delete these
objects, and how settings and toggle controls behave identically on a phone and
on a large desktop viewport. Implementation details, component APIs and task
breakdowns are intentionally out of scope here and will be covered in follow-up
technical documents.

---

## 1. Design Principles

The unified UX is grounded in six principles. Every screen, control and
transition must honour them.

1. **One mental model, everywhere.** All four screens share the same anatomy:
   List → Search/Filter → Create → Open → Edit → Save/Delete. What the user
   learns in *Cameras* must transfer, untouched, to *Individual Groups*,
   *Collections* and *Triggers*: same buttons, same placements, same gestures.

2. **Mobile-first, desktop-complete.** Layouts are designed for a narrow thumb
   reach first (full-width list rows, tappable cards, bottom-sheet / full-screen
   editors, bottom action bar), then *progressively enhance* for wide screens
   (multi-column grids, side-by-side master/detail, inline editors, persistent
   toolbars). One code path, one set of widgets — never two different screens.

3. **Clear, consistent object lifecycle.** Every object has an unambiguous
   status flow (e.g. draft ↔ active ↔ archived). Status is always rendered the
   same way and toggled the same way across all four screens.

4. **Direct manipulation + confirmation.** Toggles flip optimistically with
   visible feedback; destructive actions (delete, archive, replace members)
   always require a confirmation step.

5. **State is the source of truth, not the DOM.** Loading, empty, error and
   offline states are first-class, uniform components — not per-screen hacks.

6. **Settings and toggles are one control type.** A "toggle" is always the same
   widget (same shape, same semantics, same minimum touch target) whether it is
   a boolean field, an enable/disable badge, or a per-row action — across mobile
   and desktop.

---
## 2. Target Information Architecture

Each of the four screens is a **"resource home"** built from the same building
blocks. A resource home has exactly three levels:

```
Resource Home (level 1)                 e.g. /cameras
├─ Toolbar  — global actions (create, refresh, layout, filters)
├─ List / Grid — many objects, tappable
│      ├─ Item row/card → tap opens ...
└─ Detail (level 2)                     e.g. /cameras/:id
       ├─ Header: identity + status + primary actions
       ├─ Tabs / sections: settings, relationships, activity
       └─ Editor (level 3)  — inline panel, dialog, bottom sheet, or full-screen
            │  Create / Edit form
            └─ Delete / deactivate
```

Navigation rules:

- **List ⇄ Detail**: tapping an item opens its detail. On mobile the detail
  pushes a new screen (with back). On desktop (wide) the detail opens in a
  persistent master/detail split within the same screen — the list stays
  visible and selectable.
- **List ⇄ Create**: a **primary Create** action (FAB on mobile, prominent
  button on desktop) opens the editor. After save, the new object appears in
  the list, and the user returns to the list (create‑then‑continue), not to the
  detail, to support rapid batch entry.
- **Detail ⇄ Edit**: Edit is a single, always-visible action on the detail
  header; it never hides behind the AppBar "more" menu.
- **Delete is never inline-immediate**: it is always the final action of an
  editor, or a two-step confirm from a row/detail menu.

Each resource home exposes the same, consistent toolbar and gestures described
in the next sections.

---

## 3. Unified List & Discovery

The list is the home of every resource and behaves identically everywhere.

- **View & layout**: Grid (visual objects: cameras, groups, collections) vs
  List (structured/verbose objects: triggers, actions). A layout toggle is
  available where both make sense (like Individual Groups has today). On
  mobile both are single-column; grids become multi-column on wide screens.
- **Search**: A search field pinned at the top of the list area (not only in a
  dialog) performs server/client filtering, debounced. Consistent search
  across screens behaves the same.
- **Filter & sort**: A filter affordance opens a consistent filter panel (see
  §5); sort is part of the same panel. Filters chosen are shown as dismissible
  chips above the list.
- **Refresh**: Pull-to-refresh on touch, plus a refresh icon in the toolbar on
  all sizes.
- **Row actions**: Each item exposes a stable 3-dot overflow menu (Edit, Toggle,
  Duplicate if applicable, Delete) — identical placement on mobile and desktop.
  Primary per-row toggle (e.g. enable/disable trigger, archive camera) renders
  as the unified toggle control (§5), not a text link.
- **Bulk actions** (where applicable — e.g. Collections multi-select) use
  selection mode: checkmarks appear, the toolbar swaps to a contextual bar with
  count + bulk actions, never mixing with normal actions.

### L-E-R state (Loading / Empty / Error)

A single set of states, used by all four screens:

- **Loading**: skeleton placeholders (never a bare spinner covering the screen).
- **Empty**: a friendly illustration + title + the primary Create call-to-action.
- **Error**: message + a single **Retry** action. Network/offline uses a shared
  offline notice (the app already deals with online/offline for media).

---
## 4. Detail View

The detail level presents one object and its management actions.

- **Header** (identical anatomy on all four screens): identity/avatar/thumbnail,
  name/time, a prominent **status** readout, and primary action buttons.
- **Primary actions** sit at the top, always visible: **Edit** (primary) and
  **Toggle/Activate**; destructive **Delete** sits last, visually separated.
- **Body**: tabs or sections appropriate to the object (e.g. Triggers →
  *Conditions / Schedule / Actions*; Cameras → *Preview / Pipeline / Settings*;
  Groups → *Members / Metadata*; Collections → *Media / Organization*).
- **Desktop**: detail renders beside the list (master/detail) with the list
  still tappable. **Mobile**: detail is a pushed route; the same widget tree is
  reused so there is a single source of truth for the layout.

**Content-first right pane (refinement).** On wide master/detail, the right pane
does **not** default to a settings/detail form. It renders the **active item's
content**:

| Resource | Right pane (resting state) |
|----------|---------------------------|
| Cameras | Live/preview of the active camera |
| Collections | Video/media of the active collection |
| Individual Groups | Members of the active group |
| Triggers & Actions | Settings only (they own no media) |

The left list never changes. Settings stay out of the way: a **settings icon**
(always visible on the content bar, and reachable from the row's overflow menu)
opens the settings editor on the right; closing/saving returns to the content
view.

---

## 5. Unified Input: The Editor + Settings & Toggles

This is the core ask: a **single, unified way to capture user input** (forms,
settings and toggles) that is identical on mobile and on large screens.

### 5.1 The Editor surface

Object creation and editing always use the **same editor body**. Only the
*surface* it sits in changes with viewport size:

- **Mobile** (narrow): editor opens **full-screen** (or a near-full bottom
  sheet) with its own header row: title, **Save** (primary), **Cancel**; a
  sticky **Save/Cancel** bar at the bottom for thumb reach.
- **Tablet** (medium): editor is a **centered dialog/bottom sheet** with the
  same body and the same sticky footer actions.
- **Desktop** (wide): editor is a **modal dialog or right-hand side panel**,
  or (for Edit) an **inline expanding panel** within the master/detail split.

Regardless of surface, these are constant:

- A single reusable field model: inputs, dropdowns, date/time pickers,
  multi-select chips, and toggles render identically everywhere.
- **Save** is disabled/validating until the object is valid; validation errors
  appear inline next to the field.
- **Create vs Edit** share one form; only the header copy and the delete
  affordance differ (delete only appears when editing an existing object).
- Draft state: the form remembers unsaved input if navigation is attempted,
  prompting the user to discard.

### 5.2 The unified Toggle / Settings control

Settings and boolean actions collapse into **one toggle widget** used for every
"on/off" across the app — in settings sections, on rows, and on detail headers.
Its behaviour is uniform:

| Aspect | Behaviour |
|--------|-----------|
| **Visual** | One component: thumb-switch or toggle-chips; consistent color coding (off = muted, on = semantic color). |
| **Reachability** | Minimum 44–48px tap target on both mobile and desktop (desktop keeps it comfortable, not micro). |
| **Optimistic** | Flips immediately; reverts on server error with a snackbar; in-flight state shows while saving. |
| **Label + helper** | Each toggle carries an accessible label and (tooltip at least) helper text. |
| **Confirm** | "Dangerous" toggles (e.g. deactivate camera, disable a trigger) require the same confirm step as deletes. |
| **Placement** | A toggle keeps the same relative position on mobile and desktop (leading/secondary, not moved between surfaces). |

Thus "enable/disable trigger", "archive camera", "show live streams", "group
visibility" and any settings boolean are the *same component* in the *same
spot* regardless of device — the exact unification requested.

### 5.3 Filter panel

Search/filter settings use the same panel pattern: chips for quick filters,
then an expandable section for the full filter form (which is itself the editor
field model). It renders as a bottom sheet on mobile and as a popover/left panel
on desktop, sharing one body.

## 6. Responsive Behaviour Summary

| Breakpoint (width) | Layout | Editor surface | Toolbar | Row actions |
|--------------------|--------|----------------|---------|-------------|
| < 600px (mobile) | Single-column list / 2-col grid; pull-to-refresh | Full-screen / bottom sheet | Icon-first, FAB for Create | Overflow menu + unified toggle |
| 600–1024px (tablet) | Multi-column grid; master/detail becomes available | Dialog / bottom sheet | Condensed toolbar buttons | Overflow menu + unified toggle |
| > 1024px (desktop) | Multi-column grid + master/detail split | Modal dialog / inline panel | Persistent labeled buttons | Overflow menu + unified toggle (+ inline quick actions) |

One shared breakpoint utility drives all four screens; no screen computes its
own widths.

---

## 7. The Four Screens Mapped to the Target

Concrete target view for each screen (what changes vs. today):

- **Cameras**: adopt list/grid + content-first master/detail — the right pane
  shows the **active camera preview**; unify AppBar toggles ("live streams",
  "archived") as settings toggles behind the settings icon; add/edge/RTSP
  capture via the unified editor; keep live status as a status readout; move
  row-level archive to the unified toggle.
- **Collections**: decompose the ~2300-line screen into the resource-home
  anatomy (Toolbar / List / Detail / Editor) — the right pane lists the active
  collection's **media/videos**; selection mode for bulk actions; reuse the
  unified editor (behind the settings icon) for properties and the
  privacy/settings toggles; move date/search filters into the unified filter
  panel.
- **Individual Groups**: already the closest match — keep grid/list toggle,
  search, visibility filter, pull-to-refresh; the right pane now shows the
  active group's **members**; map create/edit + member workflows onto the
  unified editor behind the settings icon; swap ad-hoc visibility control to the
  unified control.
- **Triggers**: keep Triggers/Actions tabs; replace status-badge toggles with
  the unified toggle; rebuild the complex create/edit forms on the unified
  editor; reuse the filter panel for trigger conditions; align row menus.

---

## 8. Reusable "Data Object" Kit (conceptual, not yet API details)

To avoid re-implementations, the proposal introduces a small set of shared
conceptual UI kits (their exact APIs are out of scope):

1. **ResourceScaffold** — the standard list/empty/loading/error scaffold.
2. **ResourceListView / ResourceGridView** — layout + selection mode + refresh.
3. **ResourceFieldset** — the reusable form field model (inputs, pickers,
   chips, toggles) used by every editor surface.
4. **UnifiedToggle** — the single toggle control with optimistic/confirm
   behaviour.
5. **FilterPanel** — the shared search/filter/sort surface.
6. **EditorSurface** — one body, responsive wrappers (full screen / sheet / dialog / inline).
7. **MasterDetail / Breadcrumb** — desktop split container.
8. **Feedback primitives** — one snackbar/toast + inline validation language.

---

## 9. Mockup Validation (Phase 0 — throwaway Flutter prototype)

Before touching the real screens, build a **short-lived, UI-only Flutter
prototype** in `autonomous/mockups` to validate the interaction model cheaply.

- **Scope**: fake-data only (no real API, no auth, no business-logic state);
  model just the parts under debate: list/grid, search+filter panel, detail
  header, the three editor surfaces per breakpoint, and the unified toggle.
- **Goal**: empirically settle the responsive table (§6) and the editor-surface
  matrix from §5, and confirm 44–48px touch targets and master/detail feel.
- **Exit criteria**: the working patterns are ported back into this proposal
  and eventually into `ppl-meta-frontend`, then the prototype is archived or
  deleted. It is explicitly **not** a deliverable and must not drift into a
  second real frontend.

### 9.1 High-level Roadmap

1. **Phase 0 — Mockup** (`autonomous/mockups`): validate the interaction model.
2. **Phase 1 — Foundation**: build the shared kit (ResourceScaffold,
   UnifiedToggle, Fieldset, EditorSurface, breakpoint utility) with widget
   tests; no screen changes yet.
3. **Phase 2 — Reference screen: Individual Groups**: migrate first as it already
   matches the target; becomes the pattern-forcing example and testing harness.
4. **Phase 3 — Cameras**: migrate list/detail + settings toggles.
5. **Phase 4 — Triggers**: rebuild forms/editor + unify toggles; keep tabs.
6. **Phase 5 — Collections**: decompose the monolithic screen into the
   resource-home anatomy; largest effort, done last once patterns are proven.

---

## 10. Open Questions (to resolve in the mockup / follow-ups)

- Do Collections need both "data-object management" and the full media gallery,
  or should the gallery remain a separate surface?
- Should Triggers and Actions remain a two-tab Automation screen, or become two
  resource homes?
- Are offline/queued create/edit edits required (BackgroundSync exists), or is
  create/edit strictly online?
- Which per-object fields should expose **inline** (quick) editing on desktop
  vs. always the full editor?
- Does the mockup validate the §6 breakpoints as proposed, or do they need
  adjustment (e.g. master/detail landing earlier/later)?

---

## References

- Related current screens: `cameras_screen.dart`, `collections_screen.dart`,
  `individual_groups_screen.dart`, `triggers_screen.dart` / `triggers_tab.dart`.
- Shared app bar: `lib/widgets/custom_app_bar.dart`.
- Existing responsive examples: `home_screen.dart` (MediaQuery-based compact
  layout), responsiveness handled ad-hoc across other widgets.
- Mockup location: `autonomous/mockups` (throwaway Flutter prototype).
---