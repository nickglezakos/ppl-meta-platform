# Email Verification & Password Recovery via Communications Service

**Status:** Proposal  
**Date:** 2026-03-18  
**Priority:** High  

---

## 1. Executive Summary

Now that the Communications Service (port 8009) has working SMTP email delivery — including database-configurable settings, HTML templates, and communication logging — we can activate two user-facing flows that are currently broken:

1. **Email Verification** — Users receive a verification link after registration; clicking it marks their account as verified.
2. **Password Recovery** — Users request a reset link from the login screen; clicking it opens a form to set a new password.

Both flows already have partial backend endpoints in the Node service, but they call a disabled stub (`mail.py` → always returns `False`). The fix is to route email delivery through the Communications Service API instead.

---

## 2. Current State Audit

### What Already Works
| Component | Status | Location |
|-----------|--------|----------|
| Communications Service SMTP delivery | **Working** | `ppl-meta-communications/src/services/email_service.py` |
| Email settings API (GET/PUT) | **Working** | `ppl-meta-communications/src/routes/email_settings.py` |
| Email send endpoint `POST /api/v1/email/send` | **Working** | `ppl-meta-communications/src/routes/email.py` |
| Template-based email `POST /api/v1/email/send/template` | **Working** | `ppl-meta-communications/src/routes/email.py` |
| Communication audit logs | **Working** | `CommunicationLog` model with status tracking |
| User model `email_verified` field | **Exists** | `ppl-meta-node/src/models/user.py` |
| JWT verification token generation | **Exists** | `verify-email` endpoint uses `SECRET_KEY` |
| JWT password-reset token generation | **Exists** | `create_password_reset_token()` in `user_service.py` |
| Gateway proxy for verify-email | **Exists** | `POST /users/verify-email` (wrong HTTP method, should be GET) |
| Gateway proxy for reset-password | **Exists** | `POST /users/reset-password` |
| Frontend login screen "Forgot Password?" link | **Exists** | `login_screen.dart` line 234 (shows "coming soon" snackbar) |

### What Is Broken

#### Bug 1: Node `mail.py` is a disabled stub
```python
# ppl-meta-node/src/mail.py
async def send_email(subject, email_to, body) -> bool:
    logger.warning("Email sending is currently disabled")
    return False  # ← Always fails
```
All endpoints that call `send_email()` silently fail.

#### Bug 2: `forgot-password` endpoint — wrong function signature
```python
# ppl-meta-node/src/api/v1/users.py line 821
token = create_password_reset_token(db, request.email)
# ↑ BUG: function signature is (user_id, email), not (db, email)
# Should be: create_password_reset_token(user.id, request.email)
```

#### Bug 3: `reset-password` endpoint — wrong function signatures
```python
# Line 832: passes db but function only takes (token)
email = verify_password_reset_token(db, request.token)
# Should be: verify_password_reset_token(request.token)

# Line 841: passes email but function expects (db, user_id, new_password)
set_new_password(db, email, request.new_password)
# Should be: set_new_password(db, user.id, request.new_password)
```

#### Bug 4: Gateway missing `/forgot-password` proxy route
The gateway has `verify-email` and `reset-password` but not `forgot-password`.

#### Bug 5: Gateway `verify-email` uses POST but endpoint is GET
The node endpoint is `@router.get("/verify-email")` but the gateway has `@api_router.post("/users/verify-email")`.

#### Missing: No verification email sent on registration
The `/register` endpoint creates the user but never sends a verification email.

#### Missing: No frontend screens for forgot-password flow
The login screen has a "Forgot Password?" link that shows a "coming soon" snackbar.

#### Missing: No frontend email verification confirmation screen
No screen exists for `/#/verify-email?token=...`.

---

## 3. Architecture

### Email Delivery Flow

```
Node Service (8001)              Communications Service (8009)
┌────────────────┐               ┌──────────────────────────┐
│ /register      │──HTTP POST──→ │ POST /api/v1/email/send  │
│ /forgot-password│──HTTP POST──→ │                          │──→ SMTP Server
│ /verify-email  │──HTTP POST──→ │   EmailService           │
└────────────────┘               │   CommunicationLog       │
                                 └──────────────────────────┘
```

The Node service constructs the email content (subject, body, recipients) and POSTs it to the Communications Service for actual SMTP delivery. This keeps email infrastructure centralized and auditable.

### Token Strategy (unchanged)
- **Email verification**: JWT signed with `SECRET_KEY`, action `"verify_email"`, 24-hour expiry
- **Password reset**: JWT signed with `RESET_PASSWORD_SECRET`, action `"reset_password"`, 1-hour expiry

Both are stateless (no database token storage needed).

---

## 4. Implementation Plan

### Phase 1: Backend Fixes (Node Service)

#### 4.1 Replace `mail.py` stub with Communications Service client

Replace the disabled `send_email()` in `ppl-meta-node/src/mail.py` with an HTTP call to the Communications Service:

```python
# ppl-meta-node/src/mail.py
import httpx
import logging
from src.config import settings

logger = logging.getLogger(__name__)

COMMUNICATIONS_URL = getattr(settings, 'COMMUNICATIONS_SERVICE_URL', 'http://localhost:8009')

async def send_email(subject: str, email_to: str, body: str) -> bool:
    """Send email via Communications Service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{COMMUNICATIONS_URL}/api/v1/email/send",
                json={
                    "to": [email_to],
                    "subject": subject,
                    "text_body": body,
                    "html_body": body,
                    "triggered_by": "node-service",
                    "trigger_type": "system",
                }
            )
            if response.status_code == 200:
                logger.info(f"Email sent to {email_to} via Communications Service")
                return True
            else:
                logger.error(f"Communications Service returned {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send email via Communications Service: {e}")
        return False
```

#### 4.2 Fix `forgot-password` endpoint signature bug

```python
# ppl-meta-node/src/api/v1/users.py — forgot_password()
# Change:
token = create_password_reset_token(db, request.email)
# To:
token = create_password_reset_token(user.id, request.email)
```

#### 4.3 Fix `reset-password` endpoint signature bugs

```python
# Change:
email = verify_password_reset_token(db, request.token)
# To:
payload = verify_password_reset_token(request.token)
if not payload:
    raise HTTPException(status_code=400, detail="Invalid or expired token")
email = payload.get("email")

# Change:
set_new_password(db, email, request.new_password)
# To:
user = get_user_by_email(db, email)
if not user:
    raise HTTPException(status_code=404, detail="User not found")
set_new_password(db, user.id, request.new_password)
log_user_action(db, user.username, user.email, "password_reset")
```

#### 4.4 Send verification email on registration

After `create_user()` in the `/register` endpoint, generate a verification token and send it:

```python
# After: created_user = create_user(db, validated_user)
verification_token = jwt.encode(
    {"sub": created_user.id, "action": "verify_email",
     "exp": datetime.utcnow() + timedelta(hours=24)},
    settings.SECRET_KEY, algorithm=settings.ALGORITHM
)
verify_link = f"{settings.FRONTEND_URL}/#/verify-email?token={verification_token}"
await send_email(
    subject="Verify your EyeNet account",
    email_to=created_user.email,
    body=f"""
    <h3>Welcome to EyeNet, {created_user.username}!</h3>
    <p>Please verify your email by clicking the link below:</p>
    <a href="{verify_link}" style="padding:12px 24px;background:#1a73e8;color:white;
       text-decoration:none;border-radius:6px;display:inline-block;">
       Verify Email
    </a>
    <p>This link expires in 24 hours.</p>
    """
)
```

#### 4.5 Update password reset email link to use frontend URL

Currently the reset link points to the backend API endpoint directly. It should point to a frontend screen:

```python
# Change:
reset_link = f"http://{settings.HOST}:{settings.PORT}/api/v1/users/reset-password?token={token}"
# To:
reset_link = f"{settings.FRONTEND_URL}/#/reset-password?token={token}"
```

#### 4.6 Add `FRONTEND_URL` to Node config

Add to `ppl-meta-node/src/config.py`:
```python
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
COMMUNICATIONS_SERVICE_URL: str = os.getenv("COMMUNICATIONS_SERVICE_URL", "http://localhost:8009")
```

### Phase 2: Gateway Fixes

#### 4.7 Fix gateway routes

```python
# Add missing forgot-password route:
@api_router.post("/users/forgot-password")
async def forgot_password(request: Request):
    """Proxy forgot password to Node service."""
    return await _proxy_to_node_service(request)

# Fix verify-email — change from POST to GET:
@api_router.get("/users/verify-email")  # Was POST
async def verify_email(request: Request):
    """Proxy email verification to Node service."""
    return await _proxy_to_node_service(request)
```

### Phase 3: Frontend — Forgot Password Flow

#### 4.8 Create `ForgotPasswordScreen`

New file: `ppl-meta-frontend/lib/presentation/screens/auth/forgot_password_screen.dart`

- Single email input field
- "Send Reset Link" button → `POST /api/v1/users/forgot-password` with `{"email": "..."}`
- On success: show confirmation message "Check your email for a reset link"
- On error: show error (user not found, etc.)

#### 4.9 Create `ResetPasswordScreen`

New file: `ppl-meta-frontend/lib/presentation/screens/auth/reset_password_screen.dart`

- Reads `token` from URL query parameter (`/#/reset-password?token=...`)
- Two fields: New Password + Confirm Password
- Strong password validation (8+ chars, 1 digit, 1 upper, 1 lower, 1 special)
- "Reset Password" button → `POST /api/v1/users/reset-password` with `{"token": "...", "new_password": "..."}`
- On success: navigate to login with success message

#### 4.10 Create `VerifyEmailScreen`

New file: `ppl-meta-frontend/lib/presentation/screens/auth/verify_email_screen.dart`

- Reads `token` from URL query parameter (`/#/verify-email?token=...`)
- Auto-calls `GET /api/v1/users/verify-email?token=...` on load
- Shows success/failure message
- Link to login page

#### 4.11 Wire up login screen "Forgot Password?" link

Replace the "coming soon" snackbar with navigation:

```dart
// Change:
onTap: () {
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('Forgot password feature coming soon')),
  );
},
// To:
onTap: () => context.go('/forgot-password'),
```

#### 4.12 Add routes to `app_router.dart`

```dart
GoRoute(
  path: '/forgot-password',
  builder: (context, state) => const ForgotPasswordScreen(),
),
GoRoute(
  path: '/reset-password',
  builder: (context, state) {
    final token = state.uri.queryParameters['token'] ?? '';
    return ResetPasswordScreen(token: token);
  },
),
GoRoute(
  path: '/verify-email',
  builder: (context, state) {
    final token = state.uri.queryParameters['token'] ?? '';
    return VerifyEmailScreen(token: token);
  },
),
```

### Phase 4: Auth Service Frontend Methods

#### 4.13 Add methods to `auth_service.dart`

```dart
Future<void> forgotPassword(String email) async {
  await _apiClient.post('/api/v1/users/forgot-password', data: {'email': email});
}

Future<void> resetPassword(String token, String newPassword) async {
  await _apiClient.post('/api/v1/users/reset-password', data: {
    'token': token,
    'new_password': newPassword,
  });
}

Future<void> verifyEmail(String token) async {
  await _apiClient.get('/api/v1/users/verify-email', queryParameters: {'token': token});
}
```

---

## 5. Email Templates

### Verification Email
- **Subject:** "Verify your EyeNet account"
- **Body:** Welcome message + prominent "Verify Email" button linking to `/#/verify-email?token=...`
- **Expiry note:** "This link expires in 24 hours"

### Password Reset Email
- **Subject:** "Reset your EyeNet password"
- **Body:** "We received a password reset request" + "Reset Password" button linking to `/#/reset-password?token=...`
- **Expiry note:** "This link expires in 1 hour"
- **Security note:** "If you didn't request this, you can safely ignore this email"

### Post-Verification Thank You (already exists in code)
- **Subject:** "Thank you for verifying your email"
- **Body:** Confirmation that account is now fully active

---

## 6. Security Considerations

- **Token expiry:** Verification tokens expire in 24 hours; reset tokens in 1 hour
- **Stateless tokens:** JWT-based, no database storage (no token revocation table needed)
- **Rate limiting:** The gateway already rate-limits `/api/v1/users` at 50/minute
- **No user enumeration:** The `/forgot-password` endpoint currently returns 404 for unknown emails. Consider always returning success to prevent email enumeration (Phase 2 hardening)
- **HTTPS in production:** All email links must use HTTPS base URLs in production deployments
- **Strong password enforcement:** The existing `is_strong_password()` check (8+ chars, digit, upper, lower, special) applies to reset passwords

---

## 7. Service Dependencies

| Service | Port | Role |
|---------|------|------|
| Node (ppl-meta-node) | 8001 | JWT token generation, user management, orchestrates email sending |
| Communications (ppl-meta-communications) | 8009 | SMTP delivery, audit logging, template management |
| Gateway (ppl-meta-gateway) | 8080 | Proxies frontend requests to backend services |
| Frontend (ppl-meta-frontend) | 3000 | UI screens for forgot-password, reset, verification |

---

## 8. Testing Checklist

### Email Verification Flow
- [ ] Register new user → verification email received
- [ ] Click verification link → `email_verified` set to `true`
- [ ] Click expired link (24h+) → "Invalid or expired token" error
- [ ] Click link twice → "Email already verified" message
- [ ] Unverified user can still log in (verification is informational for now)

### Password Recovery Flow
- [ ] Click "Forgot Password?" on login → navigates to forgot-password screen
- [ ] Submit email → reset email received with valid link
- [ ] Submit unknown email → appropriate error
- [ ] Click reset link → opens reset-password screen with token
- [ ] Set new password (meets strength requirements) → success, redirect to login
- [ ] Set weak password → validation error
- [ ] Use expired token (1h+) → "Invalid or expired token" error
- [ ] Login with new password → success
- [ ] Login with old password → failure

### Communications Service Audit
- [ ] Every email (sent or failed) creates a `CommunicationLog` entry
- [ ] Failed SMTP delivery is logged with error message
- [ ] Audit logs visible via Communications API

---

## 9. Implementation Order

| Step | Task | Files Modified |
|------|------|----------------|
| 1 | Replace `mail.py` stub with Communications Service HTTP client | `ppl-meta-node/src/mail.py` |
| 2 | Add `FRONTEND_URL` and `COMMUNICATIONS_SERVICE_URL` to config | `ppl-meta-node/src/config.py` |
| 3 | Fix `forgot-password` function signature bug | `ppl-meta-node/src/api/v1/users.py` |
| 4 | Fix `reset-password` function signature bugs | `ppl-meta-node/src/api/v1/users.py` |
| 5 | Update reset email link to point to frontend | `ppl-meta-node/src/api/v1/users.py` |
| 6 | Add verification email sending to `/register` | `ppl-meta-node/src/api/v1/users.py` |
| 7 | Fix gateway: add `/forgot-password`, fix verify-email method | `ppl-meta-gateway/src/api/v1/router.py` |
| 8 | Frontend: add `forgotPassword`, `resetPassword`, `verifyEmail` to auth service | `ppl-meta-frontend/lib/core/services/auth_service.dart` |
| 9 | Frontend: create `ForgotPasswordScreen` | New file |
| 10 | Frontend: create `ResetPasswordScreen` | New file |
| 11 | Frontend: create `VerifyEmailScreen` | New file |
| 12 | Frontend: add routes to `app_router.dart` | `ppl-meta-frontend/lib/presentation/navigation/app_router.dart` |
| 13 | Frontend: wire login "Forgot Password?" link | `login_screen.dart` |
| 14 | Test end-to-end with Communications Service running | All services |
