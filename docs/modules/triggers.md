# triggers module

## Introduction

### How Triggers Work (high level)
- The page at /#/triggers is a management UI with two parts: a Triggers tab (rules) and an Actions tab (reusable action definitions), wired from [ppl-meta-frontend/lib/presentation/navigation/app_router.dart](ppl-meta-frontend/lib/presentation/navigation/app_router.dart#L257-L260) and implemented in [ppl-meta-frontend/lib/screens/triggers_screen.dart](ppl-meta-frontend/lib/screens/triggers_screen.dart#L6-L11).
- In the Triggers tab, each trigger is a rule scoped to a camera plus an AND-list of demographic conditions, a time span, cooldown, active flag, and optional linked action UUID; CRUD/toggle/filter/paging are handled in [ppl-meta-frontend/lib/widgets/triggers_tab.dart](ppl-meta-frontend/lib/widgets/triggers_tab.dart#L90-L201) and [ppl-meta-frontend/lib/widgets/triggers_tab.dart](ppl-meta-frontend/lib/widgets/triggers_tab.dart#L520-L923).
- Actions are created separately in the Actions tab and then attached to triggers; those user actions are managed via [ppl-meta-media/src/routes/user_trigger_actions.py](ppl-meta-media/src/routes/user_trigger_actions.py#L14-L179) and linked on the trigger model via [ppl-meta-media/src/models/trigger.py](ppl-meta-media/src/models/trigger.py#L71-L85).

### Runtime Flow
- Camera detections are produced in Cameras service and sent for trigger evaluation (legacy HTTP path and Redis path exist), see [ppl-meta-cameras/src/services/instant_detection.py](ppl-meta-cameras/src/services/instant_detection.py#L1207-L1274).
- Media service runs a Redis subscriber on startup, evaluates active triggers for that camera, checks cooldown, evaluates all conditions, updates last_fired_at, then executes the linked action type (digital signage, email, webhook, log, alert), see [ppl-meta-media/src/main.py](ppl-meta-media/src/main.py#L188-L206) and [ppl-meta-media/src/services/redis_subscriber.py](ppl-meta-media/src/services/redis_subscriber.py#L160-L343).
- There are also HTTP endpoints for CRUD and explicit evaluation/webhook processing in [ppl-meta-media/src/routes/triggers.py](ppl-meta-media/src/routes/triggers.py#L26-L348) and [ppl-meta-media/src/routes/triggers.py](ppl-meta-media/src/routes/triggers.py#L351-L708).

## Current implementation (concise)

### Module boundaries
- Frontend (`/triggers`) owns trigger/action configuration UX.
- Media service owns trigger persistence, evaluation, and action dispatch.
- Cameras service publishes demographic detection events.
- Communications/Signage services are downstream executors for side effects.

### Data model summary
- Trigger core fields: `camera_device_id`, `demographic_conditions[]`, `time_span`, `cooldown_seconds`, `is_active`, `last_fired_at`, optional `action_uuid`.
- Conditions are evaluated with AND semantics.
- `action_uuid` maps a trigger to a reusable user action (`alert`, `email`, `webhook`, `log`, `digital_signage`).

### Execution paths
- Primary operational path: Redis pub/sub event -> media subscriber -> condition check -> action execution.
- Secondary/legacy path: HTTP evaluate/webhook endpoints still exist for compatibility and manual calls.

### Technical analysis (concise)
- Strength: clear separation between rule definition and action definition improves reuse.
- Strength: cooldown and `last_fired_at` provide basic anti-spam control.
- Strength: multi-action-type dispatch supports both signage and communications workflows.
- Caveat: duplicate evaluation paths (Redis + HTTP) increase behavior drift risk if logic diverges.
- Caveat: condition/time parsing is functional but not a fully centralized rules engine.
