# EyeNet Wiki Hetzner Deployment

Static-only runbook. Wiki publish is independent of Authority image pull/restart.

## Public site

- Hostname: `wiki.eyenet-vision.com`
- Same VPS as Authority (currently `138.201.245.219`)
- Document root: `/home/deploy/apps/ppl-meta-wiki/html`
- Edge: Caddy `file_server` (TLS via Caddy / Cloudflare)

## Required GitHub secrets

Reuse the existing Hetzner SSH secrets only:

- `HETZNER_HOST`
- `HETZNER_USER`
- `HETZNER_SSH_KEY`

Do **not** require GHCR, mail, or Authority admin secrets for wiki deploy.

## One-time host setup

### 1. Cloudflare DNS

Create an A record:

- Name: `wiki`
- Target: Hetzner VPS public IP
- Proxy: orange-cloud is fine for static HTTP

### 2. Document root

On the VPS as the deploy user:

```sh
mkdir -p /home/deploy/apps/ppl-meta-wiki/html
# Caddy runs as user `caddy` and must traverse /home/deploy (often mode 750).
chmod o+x /home/deploy
```

Without `o+x` on `/home/deploy`, Caddy returns **403** for every wiki path.

### 3. Caddy site

Append the contents of [`Caddyfile.snippet`](./Caddyfile.snippet) to `/etc/caddy/Caddyfile` (alongside the Authority and VPN blocks from `autonomous/ppl-meta-authority/Caddyfile`).

Then:

```sh
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Caddy issues/renews certificates for `wiki.eyenet-vision.com` once DNS points at the host.

### 4. First content publish

From a machine with SSH access (or via GitHub Actions `Docs Wiki Deploy`):

```sh
python3 scripts/build_wiki_static.py --out artifacts/wiki-site
./scripts/deploy-wiki-to-hetzner.sh artifacts/wiki-site
```

Smoke:

```sh
curl -fsS -o /dev/null -w '%{http_code}\n' https://wiki.eyenet-vision.com/distributors/
curl -fsS -o /dev/null -w '%{http_code}\n' https://wiki.eyenet-vision.com/owners-admins/
```

Expect `200` for both.

## CI behaviour

| Event | Action |
|---|---|
| PR touching `docs/wiki/**` | Existing validate/artifact workflows only — **no** prod rsync |
| Push to `main` under `docs/wiki/**` or this package / build+deploy scripts | Validate both sites → build HTML → rsync |
| `workflow_dispatch` on `docs-wiki-deploy.yml` | Same as main deploy |

Workflow: `.github/workflows/docs-wiki-deploy.yml`

## Decoupling rules

- Wiki deploy must never run as a side effect of Authority or platform image jobs.
- Authority redeploy must not republish wiki files.
- Wiki rsync must not touch `/home/deploy/apps/ppl-meta-authority/`.

## Layout after deploy

```text
/home/deploy/apps/ppl-meta-wiki/html/
  index.html
  assets/site.css
  distributors/...
  owners-admins/...
```
