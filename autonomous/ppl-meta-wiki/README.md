# EyeNet Wiki (static host package)

Thin deploy package for the public EyeNet online wiki. **Not** an application server.

## What this is

- Caddy site snippet for `wiki.eyenet-vision.com`
- Shared CSS for the static HTML build
- Operator runbook for one-time Hetzner + DNS setup

## What this is not

- Not a FastAPI / Docker service
- Not part of Authority (`authority.eyenet-vision.com`)
- Not coupled to `authority-release.yml`, `authority-deploy-hetzner.yml`, or `platform-release.yml`

## Content source

Markdown lives under [`docs/documentation/wiki/`](../../docs/documentation/wiki/). Build and deploy:

```sh
python3 scripts/validate_wiki_software_ref.py docs/documentation/wiki/what-is-eyenet
python3 scripts/validate_wiki_software_ref.py docs/documentation/wiki/owners-admins
python3 scripts/validate_wiki_software_ref.py docs/documentation/wiki/distributors
python3 scripts/build_wiki_static.py
./scripts/deploy-wiki-to-hetzner.sh
```

CI: [`.github/workflows/docs-wiki-deploy.yml`](../../.github/workflows/docs-wiki-deploy.yml)

## Live URLs

| Section | URL |
|---|---|
| Home | https://wiki.eyenet-vision.com/ |
| What is EyeNet | https://wiki.eyenet-vision.com/what-is-eyenet/ |
| User guide | https://wiki.eyenet-vision.com/owners-admins/ |
| Distributors guide | https://wiki.eyenet-vision.com/distributors/ |

See [DEPLOYMENT.md](./DEPLOYMENT.md) for DNS and Caddy.
