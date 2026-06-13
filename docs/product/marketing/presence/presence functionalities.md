# Presence Functionalities

## Overview

PPL Meta Presence is a presence verification and attendance orchestration module that combines mobile interactions, station-side scanning, QR flows, camera-based detection, policy-driven decisions, and operational reporting. The service is implemented by the presence backend at `ppl-meta-presence` and exposed through the `/api/v1/presence` API surface.

At a functional level, the module is designed to issue verified presence outcomes for check-in and related workflows by combining:

- Mobile device participation
- Station-side QR interactions
- Camera or face-detection based validation
- Configurable installation and group policies
- Automation-ready trigger and action mapping
- Session traces, analytics, and reporting data

## Core Presence Modes

The module currently supports three session modes:

- `qr_only`: a QR-driven presence flow used for direct check-in style scenarios
- `camera_only`: a camera-driven flow where detection can begin without a QR scan
- `qr_plus_camera`: a combined flow that uses QR plus camera verification for higher assurance

These modes map to different assurance and grant outcomes:

- QR only supports simple presence confirmation and check-in flows
- Camera only supports presence match flows
- QR plus camera supports verified presence flows with stronger assurance

## Supported Check-In And Verification Flows

Based on the current implementation and the existing presence notes, the module supports the following operational patterns:

- Station QR: the mobile app scans a station-side QR challenge
- Mobile QR: the station scans a user-owned mobile QR
- Face detection: the system runs instant detection against a bound or auto-selected camera
- Mobile QR plus face detection: QR initiates or resolves the session, then the camera completes verification
- QR-first then camera-follow-up: the installation settings include a configurable QR-to-camera transition window for upgrading a QR-only event into a stronger verified presence flow
- Owner QR identification: an approved owner or user can present an owner identity QR that resolves the QR leg of the session

In the current backend, each session tracks status transitions such as creation, burst receipt, QR resolution, completion, retry, and failure.

## Session Orchestration

The module provides full presence session orchestration for mobile and station interactions:

- Create a presence session per device and user context
- Return the current session state at any point in the flow
- Generate an action plan for the session
- Upload front camera burst frames from the mobile device
- Retry burst uploads when another attempt is allowed
- Poll instant detection status
- Resolve QR scan hits against a session
- Bind reserved camera and collection resources to a session
- Produce a final result containing decision, reason code, grant type, policy source, and execution metadata

Session controls are configurable per installation, including:

- Session timeout
- Maximum unsuccessful attempts
- Concurrent trigger operation behavior
- QR-to-camera transition window

## QR Capabilities

The presence module includes multiple QR capabilities:

- Render station challenge QR payloads
- Render owner identity QR payloads
- Return the current QR associated with the latest device session
- Validate QR tokens before use
- Accept station QR hits from the mobile side
- Accept owner QR hits and complete QR-only sessions immediately when policy allows

The QR payload structure carries installation reference data, device context, actor information, timestamps, and integrity metadata so the flow can be resolved consistently across devices.

## Camera And Resource Management

Presence can operate against real platform resources and includes reservation handling for the installation:

- List available cameras from the platform
- Reserve a camera for presence use
- Auto-bind the related collection when a reserved camera has a linked collection
- Reserve a collection directly
- Unreserve cameras and clear linked collection reservations
- Reset installation reservations in one step
- Auto-select a real registered camera when no manual reservation exists
- Apply preferred camera names, preferred camera types, and allowed camera statuses during camera selection

This makes the module suitable for deployments where presence needs a dedicated camera path but must still tolerate real-world device availability changes.

## Policy And Automation Behavior

Presence decisions are policy-driven. The current module supports:

- Installation-level group policy configuration
- Group-specific policy overrides
- Active presence group selection per installation
- Policy precedence between default, installation, and group policy sources
- Decision handling for `granted`, `denied`, `retry_required`, and `failed`
- Trigger and action mapping per decision state and per session mode

The service also provisions and synchronizes external automation assets used by the wider platform, including:

- Presence individual groups
- Presence triggers
- Presence actions

This is the implementation basis for the marketing positioning around instant notifications and downstream integrations. In practice, the current backend exposes trigger/action orchestration and audit logging that can support channels such as email, Slack, Teams, webhooks, or other business systems depending on the connected platform services.

## Traceability, Audit, And Decision History

The module includes strong operational traceability:

- Decision history per session
- Queryable decision history across sessions
- Full session trace view
- Action plan inspection
- Audit log trace lookup for executed actions
- Policy source visibility in results and trace records
- External asset visibility for the linked group, trigger, and action UUIDs

This gives operators and product teams a way to understand not only whether presence was granted, but why it was granted, which policy applied, and which downstream automation assets were involved.

## Reporting And Analytics

The existing presence notes call for a complete reporting suite, and the current module already exposes a meaningful analytics surface:

- Analytics summary
- Analytics by user
- Analytics by device
- Analytics by installation
- Analytics by session mode
- Analytics by grant type
- Analytics by policy source
- Analytics by reserved collection
- Analytics by outcome and action outcome
- Session trace queries with filtering by session, user, installation, policy, camera, grant type, and date range
- User-per-day presence award summaries with date filtering and pagination

This supports the documented reporting use cases such as recent sessions, totals, recent grants, and user/day summaries. The notes also reference spreadsheet exports, which can be layered on top of these reporting endpoints.

## Privacy And Data Handling

The notes position the module as GDPR-compliant even for face-detection-enabled flows. The current service design supports that positioning by separating:

- Presence session and grant records
- Analytics and decision history
- External automation metadata
- Installation and user profile references

Operationally, the module focuses on presence outcomes, session metadata, and automation traces rather than exposing raw face data through the presence API itself.

## Functional Summary

In its current form, PPL Meta Presence provides:

- Automatic check-in and verified presence workflows
- QR-only, camera-only, and QR-plus-camera modes
- Mobile and station coordinated verification
- Camera reservation and collection binding
- Configurable installation and group policies
- Trigger/action based automation readiness
- Session traceability and audit visibility
- Presence analytics and user/day reporting
- A deployment model suitable for secure, enterprise-style environments

This makes the module suitable for workplaces, controlled premises, and other environments where presence confirmation must be reliable, explainable, configurable, and ready for operational integration.
