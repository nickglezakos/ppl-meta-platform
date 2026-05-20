# Digital Signage Guide

> **Audience:** Owners, managers, marketing professionals, and employee users  
> **Primary route:** `http://localhost:3000/#/signage`  
> **Related modules:** Triggers, Instant Detection, Analytics  
> **Primary screen:** `SignageManagementScreen`

---

## 1. Introduction

The Digital Signage module helps retail and other customer-facing businesses operate video-based screen communication from a central platform. In the current PPL Meta implementation, the module allows teams to:

- build playlists from existing media collections
- discover available signage devices
- synchronize playlists to those devices
- control playback remotely
- combine signage operations with triggers, instant detection, and analytics workflows

This module is especially valuable in technology retail shops because it replaces rigid booth-style marketing setups with a more flexible software-driven model. Instead of depending on heavy proprietary stacks or fixed-purpose kiosks, teams can use ordinary screens, mixed hardware, and existing store infrastructure.

For technology retail environments, this means digital signage can support:

- entrance campaigns to attract walk-ins
- hero-wall storytelling for flagship products
- assisted selling at counters
- bundle and accessory promotion in micro-zones
- faster campaign switching for launches, offers, or seasonal pushes

The current platform architecture supports a practical workflow:

1. Upload or organize videos in media collections.
2. Build playlists in the Digital Signage module.
3. Discover and manage playback devices.
4. Push playlists to selected screens.
5. Use instant detection and triggers to react to live traffic conditions.
6. Use analytics on the same or related cameras to evaluate traffic, demographics, and campaign effectiveness.

---

## 2. What The Module Does Today

The existing Digital Signage module is an operational control center, not just a content library.

### Core functions

- **Playlist management**: Create a playlist from one or more collections.
- **Device management**: View discovered signage devices and inspect online state.
- **Remote control**: Start, pause, resume, stop, and skip playback.
- **Sync operations**: Push playlists to one or more signage devices.
- **Trigger compatibility**: Use trigger actions of type `digital_signage` to connect camera events to signage playback behavior.
- **Analytics compatibility**: Review people-count, demographic, and behavioral analytics for camera coverage associated with signage zones.

### How it fits into the wider platform

The Digital Signage module is strongest when used with:

- **Media** for video storage and playlist source material
- **Instant Detection** for live demographic-aware events
- **Triggers and Rules** for automated content switching or playback actions
- **Analytics** for performance measurement and audience profiling

---

## 3. Why It Matters In Technology Retail

The technology retail shop marketing material positions Eyenet Digital Signage as an open, adaptive alternative to expensive closed systems.

### Business arguments carried into this guide

- It reduces lock-in to specialized vendors.
- It works across mixed display types, from large wall screens to countertop laptops.
- It supports phased rollout by zone rather than forcing a full-store redesign.
- It gives marketing teams faster campaign control.
- It allows owner-controlled infrastructure and storage choices.
- It opens the door to combining signage with audience intelligence from camera analytics.

### Typical retail deployment examples

- **Entrance conversion zone**: A screen at the entrance runs traffic-driving campaigns.
- **Hero wall**: Large displays tell a product story for premium categories.
- **Sales counters**: Small screens help employees reinforce offers during conversations.
- **Accessories zone**: Nearby screens promote bundles, upgrades, and add-ons.

---

## 4. Persona Benefits

### 4.1 Owners

Owners use the module as a business control and visibility tool.

**Benefits for owners:**

- Lower dependence on proprietary hardware ecosystems.
- Easier scaling from one shop to multiple sites.
- Better control over where data, storage, and operations live.
- Faster experimentation with signage zones without store redesign.
- Ability to connect signage operations with analytics and traffic evidence.
- Better strategic visibility into whether campaigns are aligned with real customer profiles.

**Owner perspective:**

For an owner, Digital Signage is not only about playing videos. It is about controlling in-store communication with less capital lock-in and better business intelligence.

### 4.2 Managers

Managers use the module to coordinate store-floor execution, ensure devices are running, and align daily campaigns with store priorities.

**Benefits for managers:**

- Central oversight of playlist status and device availability.
- Faster campaign swaps for promotions, launches, or events.
- Better coordination between floor operations and marketing goals.
- Ability to review audience behavior through analytics tied to the same camera zones.
- Practical use of automated rules instead of manual screen changes all day.
- Faster response when a display is offline or not playing the intended content.

**Manager perspective:**

For managers, the module reduces day-to-day friction. It helps them keep screens aligned with store goals while also showing what audience patterns are actually occurring in the zone.

### 4.3 Marketing Professionals

Marketing professionals use the module as an execution and optimization layer for campaigns.

**Benefits for marketing professionals:**

- Fast publishing of campaigns to multiple endpoints.
- Support for different retail display formats.
- Easier A/B-style testing across zones or time windows.
- Ability to pair content with demographics, traffic volume, or trigger conditions.
- Better evidence for campaign optimization using analytics.
- Stronger control over launch cadence, accessory upsell content, and zone-based storytelling.

**Marketing perspective:**

For marketing teams, the module creates real campaign agility. It makes it easier to choose which content plays, where it plays, and under what audience conditions it should change.

### 4.4 Employees

Employees use the module more indirectly, but it can significantly improve their sales and communication workflow.

**Benefits for employees:**

- Better support during customer conversations at counters.
- More relevant on-screen content near the active selling zone.
- Less need to explain the same product story manually from scratch.
- Better bundle and accessory reinforcement during live conversations.
- Easier customer guidance using nearby screens.
- Better confidence when screens are aligned with likely customer interest.

**Employee perspective:**

For employees, the module acts as a visual sales assistant. It can reinforce messaging, reduce repetitive explanation, and help customers compare options more effectively.

---

## 5. User Journey Overview

A complete digital signage workflow usually looks like this:

1. Prepare videos in Media collections.
2. Open the Digital Signage module.
3. Create one or more playlists.
4. Discover available signage devices.
5. Sync a selected playlist to selected devices.
6. Start playback on a target screen.
7. Optionally configure trigger-based signage actions.
8. Use instant detection for live audience awareness.
9. Review analytics for the same cameras or zones.
10. Refine content and trigger rules based on observed results.

---

## 6. Before You Start

Before using the Digital Signage module, make sure the following are ready.

### Content prerequisites

- Videos are uploaded into the platform.
- Videos are organized into one or more collections.
- Naming is clear enough for marketers and managers to identify the right assets quickly.

### Device prerequisites

- Signage player devices are running.
- Devices are registered with the Discovery service.
- Devices are reachable on the local network.
- The target screen hardware is connected and functioning.

### Operational prerequisites

- The user has permission to access the platform and related modules.
- If demographic-based automation is planned, camera coverage is already active.
- If analytics will be used, the relevant camera pipeline is recording or using instant detection as needed.

---

## 7. Screen Overview

The current Digital Signage module is divided into three tabs.

### Playlists

Use this tab to:

- search playlists
- create playlists
- review playlist cards
- open playlist details
- edit, sync, duplicate, or delete playlists

### Devices

Use this tab to:

- view discovered signage devices
- check whether devices appear online or offline
- inspect details per device
- jump to sync or control workflows

### Control

Use this tab to:

- select a device
- choose a playlist to play
- start playback
- pause playback
- resume playback
- stop playback
- move to next or previous video

---

## 8. Step-By-Step Guide: Creating A Playlist

### Playlist goal

Create a reusable playlist that can be pushed to one or more signage devices.

### Playlist steps

1. Open the Digital Signage module at `/signage`.
2. Stay on the `Playlists` tab.
3. Click `New Playlist`.
4. Enter a playlist name.
5. Optionally enter a description.
6. Select the source media collections that should feed this playlist.
7. If needed, define a custom video order.
8. Choose the loop mode.
9. Set the transition duration.
10. Save the playlist.

### What happens in the system

- The selected collection UUIDs are sent to the backend.
- The backend validates that those collections are available to the current user.
- Videos are added into ordered playlist items.
- The playlist receives cached stats like total duration and video count.

### Best practice

Use naming conventions that match store zones and campaign intent, for example:

- `Entrance - New Phone Launch`
- `Counter - Protection Plan Upsell`
- `Accessories - Laptop Bundles`

---

## 9. Step-By-Step Guide: Finding And Reviewing Devices

### Device review goal

Confirm which signage endpoints are available before syncing content.

### Device review steps

1. Open the `Devices` tab.
2. Wait for the module to load discovered signage devices.
3. Review the list of devices and their connection state.
4. Open device details for the screen you want to manage.
5. If no devices appear, use refresh and confirm the signage players are running.

### What the system is doing

- The frontend queries the Discovery service for `edge` services.
- It filters those services to names starting with `signage-simple-`.
- It stores each discovered host and port so it can query device-local status later.

### If no devices appear

Check the following:

- the player app is open on the target device
- the device is on the correct network
- the Discovery service is running
- the device has successfully registered

---

## 10. Step-By-Step Guide: Syncing A Playlist To A Device

### Sync goal

Send a chosen playlist to one or more target displays.

### Sync steps

1. Go to the `Playlists` tab.
2. Find the playlist you want to deploy.
3. Open the playlist action menu.
4. Choose `Sync to Devices`.
5. Select one or more target devices.
6. Choose the sync mode:
   - `incremental` for normal updates
   - `full` for a complete refresh
7. Confirm the sync.
8. Review sync history or device state afterward.

### When to use incremental sync

Use incremental sync when:

- only some content changed
- you want faster updates
- you are doing routine campaign refreshes

### When to use full sync

Use full sync when:

- the device is new
- the device had content problems
- the playlist changed substantially
- you want a clean refresh of content state

### Important current note

The direct sync route currently handles only the first target device even if multiple are selected. For operational safety, users should verify outcomes device by device until that behavior is expanded.

---

## 11. Step-By-Step Guide: Starting And Controlling Playback

### Playback control goal

Control what the signage screen is doing right now.

### Playback control steps

1. Open the `Control` tab.
2. Select the target device.
3. Load its current status if needed.
4. Choose the playlist you want to run.
5. Click `Start` to begin playback.
6. Use `Pause` if you need to stop temporarily.
7. Use `Resume` to continue.
8. Use `Stop` to end playback.
9. Use `Next` or `Previous` to move within the playlist.

### Typical use cases

- Start a launch playlist at store opening.
- Pause content during in-store presentations.
- Switch to a different playlist for a flash promotion.
- Skip forward when a specific product segment is more relevant.

### Operational note

The system does not force an immediate device-status refresh after every control action. The platform expects the device to publish updated state through its normal status path.

---

## 12. Step-By-Step Guide: Daily Use By Persona

### 12.1 Owner daily workflow

1. Review whether the correct zones are using the correct playlists.
2. Confirm devices appear online.
3. Review analytics from key traffic cameras.
4. Ask whether current content matches the strongest customer profile in each zone.
5. Approve strategic content changes for promotions or launches.

### 12.2 Manager daily workflow

1. Open the Devices tab in the morning.
2. Confirm key displays are online.
3. Confirm the right playlists are synced.
4. Start or switch playlists based on the day’s store priorities.
5. Review trigger-based behaviors if automated content changes are in use.
6. Check analytics later in the day for traffic and demographic results.

### 12.3 Marketing professional workflow

1. Upload or organize campaign videos in Media.
2. Create zone-specific playlists.
3. Sync playlists to target devices.
4. Configure a digital signage action if automation is needed.
5. Pair that action with a trigger or demographic rule.
6. Use analytics to compare how different zones and audiences respond.
7. Refine content based on traffic mix, gender split, age trends, and time-of-day patterns.

### 12.4 Employee workflow

1. Confirm the nearby device is online.
2. Use the assigned playlist for the current promotion or selling context.
3. Start or resume playback when needed.
4. Use relevant screen content to support customer explanations.
5. Ask a manager or marketer for changes if customer interest patterns shift.

---

## 13. Instant Detection: What It Is And Why It Matters

Instant detection is the live, fast-response camera pipeline that provides near-real-time people and demographic information from active camera feeds.

In the platform, instant detection can provide:

- current person count
- real-time face detection results
- demographic summaries such as gender and age group distributions
- fast refresh behavior suitable for reactive workflows

### Why it matters for digital signage

Digital signage becomes more valuable when it reacts to who is currently in front of the screen or moving through a zone.

Instant detection supports that by providing a live signal that can inform:

- when a campaign should switch
- which playlist is more relevant right now
- whether a zone is busy enough to justify a certain content sequence
- whether a demographic-specific message should be activated

### Practical example

A store may use instant detection in an entrance zone to determine that a larger share of visitors currently matches a younger demographic profile. A trigger can then activate a playlist focused on gaming accessories or a new phone launch instead of a generic branding reel.

### Important scope note

Instant detection is not managed inside the core signage screen itself. It belongs to the camera and detection pipeline, but it can drive signage indirectly through triggers and rules.

---

## 14. Triggers And Rules For Digital Signage Users

Triggers and rules let the platform react automatically to events or audience conditions.

In the current platform model:

- a **trigger** defines the condition to monitor
- an **action** defines what should happen when the trigger passes
- Digital Signage is available as a user action type named `digital_signage`

### What a digital signage action can contain

A digital signage action configuration includes:

- `device_ids`
- `playlist_id`
- `transition_mode`
- `fade_duration_ms`

This means a trigger can be configured to cause signage behavior on one or more target devices using a specific playlist and transition style.

### Trigger modes relevant to signage users

The backend supports several trigger modes:

- `demographic`
- `ppl_match`
- `search`
- `search_demographic`

### 14.1 Demographic triggers

Demographic triggers fire when audience conditions match configured rules.

Examples of fields supported by the trigger schema include:

- `people_count`
- `percent_male`
- `percent_female`
- `age_count_0_12`
- `age_count_13_17`
- `age_count_18_24`
- `age_count_25_34`
- `age_count_35_44`
- `age_count_45_54`
- `age_count_55_64`
- `age_count_65_plus`
- `age_threshold`

Examples of operators include:

- `gt`
- `gte`
- `lt`
- `lte`
- `eq`

### 14.2 Example demographic rule ideas

- If `people_count >= 3`, switch from passive branding to promotional content.
- If `percent_female > 60`, play a playlist targeted to a women-focused product campaign.
- If `age_count_18_24 >= 2`, activate gaming or student device messaging.
- If `age_threshold >= 45`, favor premium service, reliability, or support-oriented content.

### 14.3 People-match triggers

These triggers are designed for workflows where the platform compares observed people to an existing group definition. This is more advanced and usually used where a business has a reason to identify whether a specific audience segment or group appears in a zone.

### 14.4 Search and search-demographic triggers

These modes use scheduled search behavior across one or more cameras. They can be useful when a business wants to look across multiple camera zones and act based on search results or search results combined with demographic constraints.

### 14.5 Cooldown and control

Triggers also support:

- active/inactive state
- time windows through `time_span`
- cooldown protection through `cooldown_seconds`
- tracking/search duration windows

This helps prevent screens from changing too often or firing constantly.

### What signage users should understand

For a signage user, triggers and rules are how the platform moves from static playback to intelligent, audience-aware playback.

---

## 15. How To Think About Triggers In Practice

A simple mental model is:

1. **Observe** the audience through cameras.
2. **Evaluate** whether a condition matches.
3. **Execute** a digital signage action.
4. **Measure** the outcome with analytics.
5. **Refine** the rule and the playlist.

### Good starter rule patterns

- Start with one demographic condition and one playlist action.
- Use clear time windows so triggers are active only when relevant.
- Set cooldowns generously at first.
- Test one zone before rolling out similar rules store-wide.

### Avoid these mistakes

- Too many overlapping rules on the same camera or zone.
- Very short cooldown values that make screens unstable.
- Campaign logic with no clear audience hypothesis.
- Trying to automate every screen before validating one successful pattern.

---

## 16. Using Analytics With The Same Cameras As Signage

The platform can use analytics for the same cameras or related zones that support digital signage. This is one of the strongest ways to create a full traffic and content-performance profile.

### What analytics can add

The Analytics module provides visibility into:

- total people detected
- active cameras or collections
- time-based traffic trends
- gender distribution
- age distribution
- behavioral patterns
- quality metrics for MVR data

### Why this matters for signage

By combining analytics with signage, teams can answer questions like:

- Which zones attract the most traffic?
- What demographic profile appears in front of a given display?
- At what times should certain playlists run?
- Which campaign should be assigned to which zone?
- When should an automated signage rule trigger more aggressive promotional content?

### Practical cross-module workflow

1. Use cameras covering the signage zone.
2. Run analytics for those cameras or collections.
3. Identify the dominant audience profile by time window.
4. Create or refine playlists for that audience.
5. If needed, connect a trigger to a digital signage action.
6. Monitor results again in Analytics.

### Example

A hero wall near laptops may show that weekday afternoon traffic is dominated by adults interested in premium devices. A manager or marketer can then:

- assign a premium laptop playlist during those hours
- keep a separate gaming-focused playlist for younger evening traffic
- use a trigger to switch based on live demographic conditions
- later verify whether the zone’s traffic and engagement pattern supports the decision

---

## 17. Building A Full Analytical Profile Of Traffic And Video Strategy

A full analytical profile combines three layers.

### Layer 1: Traffic profile

Use analytics to understand:

- how many people are in the zone
- when they appear
- whether the zone is busy or quiet by hour or day

### Layer 2: Audience profile

Use instant detection and analytics to understand:

- gender split
- age patterns
- behavioral trends over time

### Layer 3: Content strategy profile

Use signage and trigger logic to decide:

- which playlist should run in the zone
- what content should change by time window
- what content should change by live demographic signal
- which devices should receive which campaigns

### Combined outcome

When all three layers are used together, the business can move from simple looping content to a more intelligent zone strategy where:

- content is tailored to real traffic
- screen decisions are informed by actual audience behavior
- campaign refinement is evidence-based rather than guess-based

---

## 18. Recommended Workflows By Maturity Level

### Level 1: Basic signage operations

Use this if you are just starting.

- Create playlists.
- Sync them to devices.
- Manually control playback.
- Use one playlist per zone.

### Level 2: Analytics-informed signage

Use this after the basic workflow is stable.

- Review traffic and demographic analytics per zone.
- Adjust playlists based on zone audience.
- Introduce time-of-day playlist planning.

### Level 3: Trigger-assisted signage

Use this when you want semi-automated audience responsiveness.

- Create a digital signage action.
- Create one or more demographic triggers.
- Assign triggers to selected cameras.
- Test screen behavior under live conditions.

### Level 4: Multi-zone optimization

Use this after individual zones are stable.

- Coordinate multiple screens.
- Compare traffic patterns across zones.
- Tune playlist strategies by store area.
- Standardize best-performing rule patterns for broader rollout.

---

## 19. Best Practices For Each Persona

### Owners

- Review outcomes by zone, not just by screen.
- Use analytics evidence before expanding hardware investment.
- Favor scalable naming and rollout conventions from the beginning.

### Managers

- Treat morning device checks as a routine.
- Use one responsible owner per zone for daily signage correctness.
- Keep emergency fallback playlists ready.

### Marketing professionals

- Design playlists around audience hypotheses.
- Build separate campaign variants for major audience segments.
- Test and refine with analytics rather than assumptions.

### Employees

- Use nearby screens as selling support, not background noise.
- Report when content feels out of sync with customer interest.
- Escalate device issues early so screens do not remain idle.

---

## 20. Troubleshooting Guide

### Problem: No devices appear

Possible causes:

- player app is not running
- device is not registered with discovery
- network issue
- discovery service is unavailable

What to do:

1. Check the device is powered and the player app is open.
2. Confirm the device is on the network.
3. Refresh the Devices tab.
4. Confirm discovery service availability.

### Problem: Playlist sync does not behave as expected

Possible causes:

- target device unreachable
- playlist not valid for the selected content set
- current sync route only handled the first selected device

What to do:

1. Retry sync for one device first.
2. Verify the playlist contents.
3. Use full sync if incremental behavior seems stale.

### Problem: Playback commands do not seem reflected immediately

Possible causes:

- device status not refreshed yet
- device-local endpoint unreachable
- control command accepted but device state update lagging

What to do:

1. Re-open the device status.
2. Confirm the device is still online.
3. Retry with a single clear command.

### Problem: Trigger-driven signage is not changing content

Possible causes:

- trigger conditions never pass
- linked digital signage action is incomplete
- cooldown or time window is blocking the trigger
- camera coverage does not match the intended zone

What to do:

1. Verify the trigger is active.
2. Check the demographic condition values.
3. Confirm the digital signage action has device and playlist IDs.
4. Review whether instant detection or analytics are producing the expected audience data.

---

## 21. Recommended Adoption Plan

### Phase 1: Operational foundation

- Bring devices online.
- Create zone-specific playlists.
- Validate sync and playback.

### Phase 2: Audience understanding

- Review analytics for signage zones.
- Identify audience differences by time and location.
- Refine playlists by zone.

### Phase 3: Controlled automation

- Create digital signage actions.
- Create selected demographic triggers.
- Test a small number of rule-driven transitions.

### Phase 4: Continuous optimization

- Review analytics regularly.
- Compare zone performance.
- Update playlists and triggers based on traffic evidence.

---

## 22. Summary

The Digital Signage module is more than a screen-control tool. It is a practical operating layer for campaign delivery, store communication, and audience-aware content execution.

For owners, it supports business control and scalability. For managers, it improves operational coordination. For marketing professionals, it enables faster, smarter campaign execution. For employees, it acts as a live communication aid on the floor.

Its full value appears when used together with instant detection, triggers, and analytics:

- **Instant detection** provides the live audience signal.
- **Triggers and rules** turn that signal into automated screen actions.
- **Analytics** show whether the strategy actually matches traffic and demographic reality.
- **Digital signage** delivers the visible customer-facing result.

Used together, these capabilities support a more intelligent retail environment in which content, traffic, and audience insight are connected instead of managed separately.
