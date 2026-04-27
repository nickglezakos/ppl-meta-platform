# Webhooks & Messaging Apps — Integration Guide

This guide covers how to connect the Automation module to external systems using the **`webhook`** and **`messaging_app`** action types. Both types are configured inside the **Actions tab** of the Automation screen and require no code changes to the platform.

---

## Table of Contents

1. [How the webhook payload works](#1-how-the-webhook-payload-works)
2. [Webhook → n8n](#2-webhook--n8n)
   - 2.1 [Set up the n8n Webhook node](#21-set-up-the-n8n-webhook-node)
   - 2.2 [Google Sheets — append a row on every trigger fire](#22-google-sheets--append-a-row-on-every-trigger-fire)
   - 2.3 [Google Sheets — increment a counter cell](#23-google-sheets--increment-a-counter-cell)
   - 2.4 [Using template variables in n8n expressions](#24-using-template-variables-in-n8n-expressions)
3. [Messaging App — Slack](#3-messaging-app--slack)
   - 3.1 [Create a Slack Incoming Webhook](#31-create-a-slack-incoming-webhook)
   - 3.2 [Configure the action in the platform](#32-configure-the-action-in-the-platform)
   - 3.3 [Slack action config reference](#33-slack-action-config-reference)
4. [Messaging App — Microsoft Teams](#4-messaging-app--microsoft-teams)
   - 4.1 [Create a Teams Workflows webhook](#41-create-a-teams-workflows-webhook)
   - 4.2 [Configure the action in the platform](#42-configure-the-action-in-the-platform)
   - 4.3 [Teams action config reference](#43-teams-action-config-reference)
5. [Template variables reference](#5-template-variables-reference)
6. [Combining actions on one trigger](#6-combining-actions-on-one-trigger)

---

## 1. How the webhook payload works

When a trigger fires and executes a `webhook` action, the platform POSTs the following JSON body to the configured URL via the Communications Service:

```json
{
  "event": "trigger_fired",
  "trigger_id": "550e8400-e29b-41d4-a716-446655440000",
  "trigger_name": "VIP Entrance Match",
  "timestamp": "2026-04-25T10:00:00.000000+00:00",
  "data": {
    // contents of payload_data from action_config — your custom fields
  },
  "reason": "Matched Group Member 01 (score=0.91)",
  "match": {
    "mode": "ppl_match",
    "matched": true,
    "best_match": {
      "individual_uuid": "abc123",
      "member_name": "Group Member 01",
      "similarity_score": 0.91
    },
    "all_candidates": [...]
  }
}
```

**Key points:**
- `data` is populated from `payload_data` in your `action_config` — put any custom tags or labels here.
- `reason` is a human-readable string describing why the trigger fired.
- `match` is present for `ppl_match` and `search` triggers; it is `null` for demographic triggers.
- The `messaging_app` action type builds its own Slack/Teams-specific payload internally and does **not** use this envelope — it only sends the formatted message.

---

## 2. Webhook → n8n

[n8n](https://n8n.io) is an open-source workflow automation tool. It can receive the platform's webhook and fan out to hundreds of services including Google Sheets, Docs, Slack, databases, HTTP APIs, and more — with no code and a full execution log.

### 2.1 Set up the n8n Webhook node

1. Open your n8n instance (self-hosted or cloud).
2. Create a new **Workflow**.
3. Add a **Webhook** trigger node.
   - **HTTP Method**: `POST`
   - **Path**: choose anything, e.g. `ppl-meta-trigger`
   - **Response Mode**: `Immediately` (so the platform does not time out waiting)
4. Click **Listen for test event**, then fire the trigger from the platform once to capture a sample payload. n8n will auto-detect all fields.
5. Copy the **Production URL** from the Webhook node (shown at the top after activation).

Create a `webhook` action in the platform with this URL:

```json
{
  "url": "https://your-n8n.example.com/webhook/ppl-meta-trigger",
  "method": "POST",
  "payload_data": {
    "source": "ppl_meta",
    "location": "Entrance A"
  }
}
```

Any fields you put in `payload_data` land inside `{{ $json.data }}` in n8n expressions.

---

### 2.2 Google Sheets — append a row on every trigger fire

**Use case:** Every time a trigger fires, record the timestamp, trigger name, reason, and similarity score in a Google Sheet log.

**Sheet structure (example):**

| Timestamp | Trigger Name | Reason | Score | Location |
|-----------|-------------|--------|-------|----------|

**n8n workflow steps:**

1. **Webhook** node (configured as above)
2. **Google Sheets** node
   - **Operation**: `Append Row`
   - **Spreadsheet**: select your Google Sheet
   - **Sheet**: select the target sheet/tab
   - **Columns** mapping:

| Sheet Column | n8n Expression |
|---|---|
| Timestamp | `{{ $json.timestamp }}` |
| Trigger Name | `{{ $json.trigger_name }}` |
| Reason | `{{ $json.reason }}` |
| Score | `{{ $json.match?.best_match?.similarity_score ?? '' }}` |
| Location | `{{ $json.data.location }}` |

**Result:** Each trigger fire appends one row to the sheet in real time. The sheet becomes a permanent audit log viewable by anyone with access, with no backend changes.

**Action config example:**

```json
{
  "url": "https://your-n8n.example.com/webhook/ppl-meta-trigger",
  "method": "POST",
  "payload_data": {
    "location": "Entrance A",
    "site": "Main Building"
  }
}
```

---

### 2.3 Google Sheets — increment a counter cell

**Use case:** Maintain a running count of how many times each trigger has fired today, displayed in a live dashboard sheet.

**Sheet structure (example):**

| Trigger Name | Count Today | Last Fired |
|---|---|---|
| VIP Entrance Match | 7 | 2026-04-25T10:00:00Z |

**n8n workflow steps:**

1. **Webhook** node
2. **Google Sheets** node — **Read Rows** to find the row for this trigger:
   - **Operation**: `Lookup`
   - **Lookup Column**: `Trigger Name`
   - **Lookup Value**: `{{ $json.trigger_name }}`
3. **IF** node — check if a row was found: `{{ $items().length > 0 }}`
4. **Branch A (row exists) → Google Sheets** node — **Update Row**:
   - **Row Number**: `{{ $json['row_number'] }}`
   - `Count Today` = `{{ Number($json['Count Today']) + 1 }}`
   - `Last Fired` = `{{ $('Webhook').item.json.timestamp }}`
5. **Branch B (no row) → Google Sheets** node — **Append Row**:
   - `Trigger Name` = `{{ $('Webhook').item.json.trigger_name }}`
   - `Count Today` = `1`
   - `Last Fired` = `{{ $('Webhook').item.json.timestamp }}`

**Result:** A real-time counter per trigger, visible in Google Sheets, suitable for a dashboard or daily operations report.

---

### 2.4 Using template variables in n8n expressions

The platform supports interpolating template variables inside `payload_data` values **before** the webhook is sent. This means you can bake resolved values directly into your custom fields, making n8n expressions simpler.

**Example `action_config`:**

```json
{
  "url": "https://your-n8n.example.com/webhook/ppl-meta-trigger",
  "method": "POST",
  "payload_data": {
    "resolved_name": "{matched_member_name}",
    "resolved_score": "{similarity_score}",
    "notes": "Match by {trigger_name}"
  }
}
```

In n8n you can then simply use:
- `{{ $json.data.resolved_name }}` → already contains the matched member's name
- `{{ $json.data.resolved_score }}` → already contains the score as a string

**Available variables inside `payload_data`:**

| Variable | Value |
|---|---|
| `{trigger_name}` | Name of the trigger |
| `{trigger_id}` | UUID of the trigger |
| `{reason}` | Full evaluation reason string |
| `{match_reason}` | Formatted match reason (ppl_match only) |
| `{matched_member_name}` | Name of the matched group member |
| `{matched_member_uuid}` | UUID of the matched individual |
| `{group_member_number}` | Ordinal of the member within the group |
| `{similarity_score}` | Decimal similarity score (e.g. `0.91`) |

> **Note:** Variables that have no value for the current trigger (e.g. `{similarity_score}` on a demographic trigger) are left as empty strings.

---

## 3. Messaging App — Slack

The `messaging_app` action type handles Slack natively. You only need a Slack Incoming Webhook URL — no adapter, no n8n, no extra server.

### 3.1 Create a Slack Incoming Webhook

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From Scratch**.
2. Name it (e.g. `PPL Meta Alerts`) and choose your workspace.
3. In the left sidebar, click **Incoming Webhooks** → toggle **Activate Incoming Webhooks** to ON.
4. Click **Add New Webhook to Workspace** → choose a channel (e.g. `#detections`) → **Allow**.
5. Copy the generated URL:
   ```
   https://hooks.slack.com/services/T.../B.../XXXXXXXXXXXX
   ```

### 3.2 Configure the action in the platform

In the **Actions tab**, click **Create Action**:

- **Action Type**: `Messaging App (Slack / Teams)`
- **Platform**: `Slack`
- **Webhook URL**: paste the URL from step above
- **Message Template**: your message with optional template variables
- **Mention** (optional): `@channel` or `@here` to ping the channel

**Example — PPL match alert:**

| Field | Value |
|---|---|
| Name | `Slack — VIP Match Alert` |
| Platform | Slack |
| Webhook URL | `https://hooks.slack.com/services/T.../B.../...` |
| Message Template | `🔔 *{trigger_name}* fired\n>{match_reason}\nScore: \`{similarity_score}\`` |
| Mention | `@channel` |

**What Slack receives:**

```json
{
  "text": "@channel 🔔 *VIP Entrance Match* fired\n>Matched Group Member 01 (score=0.91)\nScore: `0.91`"
}
```

Slack renders the `>` prefix as a blockquote and `*...*` as bold, so the message displays cleanly.

**Example — demographic threshold alert:**

| Field | Value |
|---|---|
| Message Template | `📊 High traffic detected on {trigger_name}\n{reason}` |
| Mention | `@here` |

---

### 3.3 Slack action config reference

The platform stores the following JSON in `action_config` for `messaging_app` / Slack:

```json
{
  "platform": "slack",
  "webhook_url": "https://hooks.slack.com/services/T.../B.../...",
  "message_template": "🔔 *{trigger_name}* fired\n>{match_reason}\nScore: `{similarity_score}`",
  "mention": "@channel"
}
```

| Field | Required | Description |
|---|---|---|
| `platform` | Yes | Must be `"slack"` |
| `webhook_url` | Yes | Slack Incoming Webhook URL |
| `message_template` | Yes | Message body. Supports all template variables and Slack markdown (`*bold*`, `_italic_`, `` `code` ``, `>quote`) |
| `mention` | No | Prepended to the message. Use `@channel`, `@here`, or a user like `<@U12345>` |
| `title` | No | Not used for Slack — include any title text directly in `message_template` |

**Slack markdown quick reference:**

| Effect | Syntax |
|---|---|
| Bold | `*text*` |
| Italic | `_text_` |
| Code | `` `text` `` |
| Code block | ```` ```text``` ```` |
| Blockquote | `>text` |
| Link | `<https://example.com\|label>` |
| Mention channel | `@channel` or `@here` |
| Mention user | `<@UXXXXXXXX>` |

---

## 4. Messaging App — Microsoft Teams

The `messaging_app` action type sends to Teams via **Power Automate Workflows** — the current replacement for the deprecated Office 365 Connectors. When a `title` is set the platform sends a rich Adaptive Card; without a title it sends a plain text message that the Workflow can map freely.

### 4.1 Create a Teams Workflows webhook

1. In Teams, open the target channel (e.g. `#detections`).
2. Click the **+** (Apps) button next to the message compose box → search **Workflows**.
3. Select the template: **"Post to a channel when a webhook request is received"**.
4. Name the workflow (e.g. `PPL Meta Alerts`) → **Next** → confirm the channel → **Add Workflow**.
5. Copy the generated webhook URL:
   ```
   https://prod-xx.westus.logic.azure.com:443/workflows/...
   ```

> **Note:** With the Workflows approach Teams accepts any JSON body. When the platform sends an Adaptive Card (i.e. when `title` is set), Teams renders it natively. When no `title` is set, the Workflow's Power Automate steps parse and format the body using expressions like `@{triggerBody()?['trigger_name']}`.

### 4.2 Configure the action in the platform

In the **Actions tab**, click **Create Action**:

- **Action Type**: `Messaging App (Slack / Teams)`
- **Platform**: `Microsoft Teams`
- **Webhook URL**: paste the Workflow URL
- **Message Template**: the body text of the message (or card body)
- **Card Title** (optional): when set, triggers Adaptive Card format

**Example — PPL match as Adaptive Card:**

| Field | Value |
|---|---|
| Name | `Teams — VIP Match Alert` |
| Platform | Microsoft Teams |
| Webhook URL | `https://prod-xx.logic.azure.com:443/workflows/...` |
| Message Template | `{match_reason}\nScore: {similarity_score}` |
| Card Title | `🔔 {trigger_name} fired` |

**What Teams receives:**

```json
{
  "type": "message",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.4",
      "body": [
        {
          "type": "TextBlock",
          "size": "Medium",
          "weight": "Bolder",
          "text": "🔔 VIP Entrance Match fired"
        },
        {
          "type": "TextBlock",
          "text": "Matched Group Member 01 (score=0.91)\nScore: 0.91",
          "wrap": true
        }
      ]
    }
  }]
}
```

Teams displays this as a structured card with a bold title and wrapped body text.

**Example — plain text (no card title):**

| Field | Value |
|---|---|
| Message Template | `🔔 {trigger_name} fired — {reason}` |
| Card Title | *(leave blank)* |

The platform sends `{"text": "🔔 VIP Entrance Match fired — Matched Group Member 01"}`. The Workflow's Power Automate step maps `@{triggerBody()?['text']}` directly to the Teams message.

---

### 4.3 Teams action config reference

```json
{
  "platform": "teams",
  "webhook_url": "https://prod-xx.logic.azure.com:443/workflows/...",
  "message_template": "{match_reason}\nScore: {similarity_score}",
  "title": "🔔 {trigger_name} fired"
}
```

| Field | Required | Description |
|---|---|---|
| `platform` | Yes | Must be `"teams"` |
| `webhook_url` | Yes | Power Automate Workflow webhook URL |
| `message_template` | Yes | Card body text (when `title` is set) or the full `text` payload. Supports all template variables |
| `title` | No | When set, the platform sends an Adaptive Card with this as the bold heading. Supports template variables. Without this, a plain `{"text": "..."}` is sent |

---

## 5. Template variables reference

All fields marked as supporting template variables in the action config are interpolated by the platform before sending. The same variable set is available in `webhook.payload_data` values, `messaging_app.message_template`, `messaging_app.title`, `email.subject`, `email.body`, `alert.message`, and `log.message`.

| Variable | Description | Available for |
|---|---|---|
| `{trigger_name}` | Display name of the trigger | All trigger modes |
| `{trigger_id}` | UUID of the trigger | All trigger modes |
| `{reason}` | Full evaluation reason string | All trigger modes |
| `{match_reason}` | Concise formatted match reason | `ppl_match`, `search` |
| `{matched_member_name}` | Name/label of matched group member | `ppl_match`, `search` |
| `{matched_member_uuid}` | UUID of the matched individual | `ppl_match`, `search` |
| `{group_member_number}` | Ordinal position of member within the group | `ppl_match`, `search` |
| `{similarity_score}` | Decimal score, e.g. `0.91` | `ppl_match`, `search` |

Variables with no value for the current event are replaced with an empty string. If no template variables are used in a `ppl_match`/`search` context, the platform auto-appends the match reason to the message.

---

## 6. Combining actions on one trigger

A single trigger supports multiple linked actions. Common combinations:

| Trigger | Actions |
|---|---|
| VIP face match | `messaging_app` (Slack `#vip-alerts`) + `alert` (on-screen) + `webhook` (n8n → Google Sheets log) |
| High crowd count | `messaging_app` (Teams `#operations`) + `email` (shift supervisor) |
| Unknown person at restricted zone | `messaging_app` (Slack `@channel`) + `digital_signage` (switch lobby screen to warning playlist) |
| Daily traffic summary (search_demographic) | `webhook` (n8n → Google Sheets counter) + `log` (audit trail) |

To configure multiple actions:

1. Create each action individually in the **Actions tab**.
2. In the **Triggers tab**, open the trigger's edit dialog.
3. In the **Linked Actions** chip selector, check all desired actions.
4. Save — all selected actions execute independently every time the trigger fires.

If one action fails (e.g. the webhook URL is unreachable), the others still execute.
