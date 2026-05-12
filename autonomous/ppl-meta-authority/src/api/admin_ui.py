from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["admin-ui"])


@router.get("/admin", response_class=HTMLResponse)
async def admin_ui() -> str:
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PPL Meta Authority Admin</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4efe6;
      --panel: #fffaf3;
      --panel-strong: #f2e3cf;
      --text: #2d241d;
      --muted: #6b5b4d;
      --accent: #a44b2f;
      --accent-dark: #7f341d;
      --border: #dbc7ae;
      --success: #2f6b45;
      --error: #8f2d2d;
      --shadow: 0 20px 50px rgba(80, 48, 20, 0.12);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
      background:
        radial-gradient(circle at top left, rgba(164, 75, 47, 0.12), transparent 30%),
        linear-gradient(180deg, #f8f2e8 0%, var(--bg) 100%);
      color: var(--text);
    }

    .shell {
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }

    .hero {
      margin-bottom: 24px;
      padding: 28px;
      border: 1px solid var(--border);
      border-radius: 24px;
      background: linear-gradient(135deg, rgba(255, 250, 243, 0.95), rgba(242, 227, 207, 0.92));
      box-shadow: var(--shadow);
    }

    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 10px;
    }

    h1 {
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 3.4rem);
      line-height: 1;
    }

    .lede {
      margin: 0;
      color: var(--muted);
      max-width: 780px;
      font-size: 1.05rem;
    }

    .grid {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 20px;
    }

    .card {
      border: 1px solid var(--border);
      border-radius: 22px;
      background: var(--panel);
      box-shadow: var(--shadow);
      padding: 22px;
    }

    .card h2 {
      margin-top: 0;
      margin-bottom: 16px;
      font-size: 1.35rem;
    }

    label {
      display: block;
      margin-bottom: 12px;
      font-size: 0.95rem;
      color: var(--muted);
    }

    input, textarea, select {
      width: 100%;
      margin-top: 6px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: #fff;
      color: var(--text);
      font: inherit;
    }

    textarea {
      min-height: 96px;
      resize: vertical;
    }

    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 16px;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      background: var(--accent);
      color: #fffaf3;
      font: inherit;
      cursor: pointer;
      transition: transform 120ms ease, background 120ms ease;
    }

    button.secondary {
      background: #dfcfba;
      color: var(--text);
    }

    button:hover { transform: translateY(-1px); background: var(--accent-dark); }
    button.secondary:hover { background: #cfb89a; }

    .status {
      min-height: 24px;
      margin-top: 14px;
      font-size: 0.95rem;
    }

    .status.ok { color: var(--success); }
    .status.error { color: var(--error); }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }

    th, td {
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid rgba(219, 199, 174, 0.7);
      vertical-align: top;
    }

    th {
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }

    .pill {
      display: inline-block;
      padding: 4px 9px;
      border-radius: 999px;
      background: var(--panel-strong);
      font-size: 0.8rem;
    }

    .small {
      color: var(--muted);
      font-size: 0.88rem;
    }

    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      .row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="eyebrow">Private Operations Surface</div>
      <h1>PPL Meta Authority Admin</h1>
      <p class="lede">Manage pending entitlements, approved owner emails, generated application keys, and activation state for the Hetzner authority service. This page uses the admin bearer token you provide below and calls the protected admin API directly.</p>
    </section>

    <section class="grid">
      <div class="card">
        <h2>Admin Token</h2>
        <label>
          Bearer token
          <input id="token" type="password" placeholder="Paste AUTHORITY_ADMIN_TOKEN">
        </label>
        <div class="actions">
          <button type="button" id="loadInstallations">Load installations</button>
        </div>
        <div id="status" class="status"></div>
      </div>

      <div class="card">
        <h2>Upsert Entitlement</h2>
        <div class="row">
          <label>
            Application key
            <input id="application_key" placeholder="Leave blank to auto-generate">
          </label>
          <label>
            Installation UUID
            <input id="installation_uuid" placeholder="Optional. Bound automatically on first activation.">
          </label>
        </div>
        <div class="row">
          <label>
            Approved owner email
            <input id="approved_owner_email" type="email" value="nick.glezakos@gmail.com">
          </label>
          <label>
            Licence status
            <select id="licence_status">
              <option value="active">active</option>
              <option value="grace">grace</option>
              <option value="expired">expired</option>
              <option value="suspended">suspended</option>
            </select>
          </label>
        </div>
        <div class="row">
          <label>
            Offline grace days
            <input id="offline_grace_days" type="number" min="0" value="21">
          </label>
          <label>
            Owner enabled
            <select id="owner_enabled">
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
        </div>
        <label>
          Tenant name
          <input id="tenant_name" value="New Tenant">
        </label>
        <label>
          Notes
          <textarea id="notes">Created from the private admin entitlement surface.</textarea>
        </label>
        <div class="actions">
          <button type="button" id="saveInstallation">Save installation</button>
          <button type="button" class="secondary" id="resetForm">Reset form</button>
        </div>
      </div>
    </section>

    <section class="card" style="margin-top: 20px;">
      <h2>Entitlement Registry</h2>
      <div class="small">Use the token above to load the current authority records.</div>
      <div style="overflow:auto; margin-top: 16px;">
        <table>
          <thead>
            <tr>
              <th>Installation</th>
              <th>Activation</th>
              <th>Owner</th>
              <th>Licence</th>
              <th>Key / Grace</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody id="installationsBody">
            <tr><td colspan="6" class="small">No data loaded yet.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>

  <script>
    const statusEl = document.getElementById('status');
    const tokenEl = document.getElementById('token');
    const bodyEl = document.getElementById('installationsBody');

    function setStatus(message, isError = false) {
      statusEl.textContent = message;
      statusEl.className = isError ? 'status error' : 'status ok';
    }

    function authHeaders() {
      const token = tokenEl.value.trim();
      if (!token) {
        throw new Error('Enter the admin bearer token first.');
      }
      return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      };
    }

    async function loadInstallations() {
      try {
        const response = await fetch('/api/v1/admin/installations', {
          headers: authHeaders(),
        });
        if (!response.ok) {
          const detail = await response.text();
          throw new Error(`Load failed (${response.status}): ${detail}`);
        }

        const installations = await response.json();
        if (!installations.length) {
          bodyEl.innerHTML = '<tr><td colspan="6" class="small">No entitlements found.</td></tr>';
        } else {
          bodyEl.innerHTML = installations.map((item) => `
            <tr>
              <td><strong>${item.installation_uuid ?? 'Pending bind'}</strong><div class="small">${item.tenant_name ?? 'No tenant name'}</div></td>
              <td><span class="pill">${item.activation_status}</span><div class="small">${item.entitlement_uuid}</div></td>
              <td>${item.approved_owner_email}<div class="small">enabled: ${item.owner_enabled}</div></td>
              <td><span class="pill">${item.licence_status}</span></td>
              <td>${item.application_key}<div class="small">${item.offline_grace_days} days</div></td>
              <td>${item.notes ?? ''}</td>
            </tr>
          `).join('');
        }
        setStatus('Entitlement registry loaded.');
      } catch (error) {
        setStatus(error.message, true);
      }
    }

    async function saveInstallation() {
      try {
        const payload = {
          approved_owner_email: document.getElementById('approved_owner_email').value.trim(),
          owner_enabled: document.getElementById('owner_enabled').value === 'true',
          licence_status: document.getElementById('licence_status').value,
          offline_grace_days: Number(document.getElementById('offline_grace_days').value),
          tenant_name: document.getElementById('tenant_name').value.trim() || null,
          notes: document.getElementById('notes').value.trim() || null,
        };
        const applicationKey = document.getElementById('application_key').value.trim();
        const installationUuid = document.getElementById('installation_uuid').value.trim();
        if (applicationKey) {
          payload.application_key = applicationKey;
        }
        if (installationUuid) {
          payload.installation_uuid = installationUuid;
        }

        const response = await fetch('/api/v1/admin/installations', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          const detail = await response.text();
          throw new Error(`Save failed (${response.status}): ${detail}`);
        }

        await loadInstallations();
        setStatus('Entitlement saved.');
      } catch (error) {
        setStatus(error.message, true);
      }
    }

    document.getElementById('loadInstallations').addEventListener('click', loadInstallations);
    document.getElementById('saveInstallation').addEventListener('click', saveInstallation);
    document.getElementById('resetForm').addEventListener('click', () => window.location.reload());
  </script>
</body>
</html>
    """