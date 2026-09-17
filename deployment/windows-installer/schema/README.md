# Installer schema pack — MUST match repo migrations

This folder is the **only** schema source the Windows/Lima installer applies.

## How “installer always matches repo” works

1. **Source of truth** = SQL under `ppl-meta-vision/migrations`, `ppl-meta-vmeta/...`, `ppl-meta-cameras/migrations`, …
2. **Sync** (from monorepo, before release / Lima setup):

```bash
bash deployment/mac-lima/sync-schema-pack.sh
```

   Writes:
   - `schema/pack/*.sql` (ordered)
   - `schema/pack.tar.gz` (for Windows download — **tracked in git**; root `*.tar.gz` ignore has an exception)
   - `schema/verify.sh`
   - `MANIFEST.txt` (audit trail)

   After sync, commit `schema/pack.tar.gz` (and any new `pack/*.sql`) so
   `raw.githubusercontent.com/.../schema/pack.tar.gz` is not 404 for the installer.

3. **Install** always runs `schema/apply.sh` after Postgres is healthy, then **`verify.sh`** (exit 1 on mismatch).

4. **Never** apply `deployment/mac-lima/sql/archive-stubs/*_minimal.sql`.

## Manual verify (any time)

```bash
# Lima
limactl shell eyenet -- bash /Users/nickgklezakos/Documents/ppl-meta-code/deployment/mac-lima/verify-codebase-schema.sh

# Windows install dir
bash schema/verify.sh
```
