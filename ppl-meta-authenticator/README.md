# EyeNet Authenticator (`ppl_meta_authenticator`)

Flutter Android app for Presence grants without registering the phone as a cameras-console device.

## Features

- **Plan A login** — Discovery port `8006` on LAN, or VPN mesh via Authority enrollment token, then local username/password
- **One-time face enroll** — Presence → vmeta creates one MVR person bound to your user PPP
- **Presence actions** — Owner QR, Scan station QR, Video match, QR + Video (live verify against enrolled MVR)

## Run

```bash
cd ppl-meta-authenticator
flutter pub get
flutter run
```

Requires a running EyeNet install with Presence and vmeta (`VMETA_SERVICE_URL` reachable from Presence, default `http://localhost:8003` or compose service name).

## Architecture notes

See [docs/proposals/authenticator/ppl-meta-authenticator-plan-a-enrolled-mvr.md](../docs/proposals/authenticator/ppl-meta-authenticator-plan-a-enrolled-mvr.md).
