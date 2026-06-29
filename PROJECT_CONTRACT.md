# PROJECT CONTRACT — AI SaaS Backend
# Version: 1.0
# Stack: Python / FastAPI / PostgreSQL / SQLAlchemy Async / Pydantic v2
# ─────────────────────────────────────────────────────────────────────────────
# READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE
# This is the single source of truth across all Claude accounts
# ─────────────────────────────────────────────────────────────────────────────

---

## 1. CURRENT MODULE SCOPE

**Active module: Authentication + OTP**
Only these endpoints exist. Do NOT build outside this scope.

```
POST /api/v1/auth/register
POST /api/v1/auth/verify-otp
POST /api/v1/auth/resend-otp
POST /api/v1/auth/login
POST /api/v1/auth/forgot-password
POST /api/v1/auth/verify-forgot-otp
POST /api/v1/auth/reset-password
POST /api/v1/auth/logout
POST /api/v1/auth/refresh-token
GET  /api/v1/users/me
GET  /health
```

---

## 2. PROJECT STRUCTURE

```
BackendSetup/
├── core/
│   ├── config.py           ✅ DONE — settings object
│   ├── database.py         ✅ DONE — Base, get_db, engine
│   ├── exceptions.py       ✅ DONE — all custom exceptions
│   ├── security.py         ✅ DONE — JWT, password, OTP generation
│   ├── cookies.py          ✅ DONE — set/clear/get cookie helpers
│   ├── email.py            ✅ DONE — EmailService
│   ├── dependencies.py     ✅ DONE — get_current_user
│   └── logging_config.py   ✅ DONE — setup_logging()
├── models/
│   ├── __init__.py         ✅ DONE
│   ├── user.py             ✅ DONE
│   ├── tenant.py           ✅ DONE
│   ├── otp_verification.py ✅ DONE — table=otp_verifications
│   └── refresh_token.py    ✅ DONE — table=refresh_tokens
├── schemas/
│   ├── __init__.py         ✅ DONE
│   ├── auth.py             ✅ DONE — all request schemas
│   ├── response.py         ✅ DONE — all response schemas
│   └── user.py             ✅ DONE — UserResponse only
├── services/
│   ├── __init__.py         ✅ DONE
│   ├── auth_service.py     ✅ DONE
│   ├── otp_service.py      ✅ DONE
│   └── token_service.py    ✅ DONE
├── routes/
│   ├── __init__.py         ✅ DONE — EMPTY FILE
│   ├── auth.py             ✅ DONE — 9 auth endpoints
│   └── users.py            ✅ DONE — GET /users/me only
├── main.py                 ✅ DONE
├── alembic/
│   └── env.py              ⏳ PENDING
├── .env.example            ⏳ PENDING
└── PROJECT_CONTRACT.md     ✅ THIS FILE
```

---

## 3. DATABASE TABLES (exact names)

```
users              → models/user.py             → class User
tenants            → models/tenant.py           → class Tenant
otp_verifications  → models/otp_verification.py → class OTPVerification
refresh_tokens     → models/refresh_token.py    → class RefreshToken
```

---

## 4. MODEL FIELD CONTRACTS

### users
```
id            : str UUID pk
full_name     : str not null
email         : str unique not null indexed
password_hash : str not null
account_type  : enum(individual, organization) not null
is_active     : bool default=False
is_admin      : bool default=False
created_at    : datetime UTC
updated_at    : datetime UTC nullable
```

### tenants
```
id                : str UUID pk
organization_name : str not null
owner_user_id     : str FK→users.id unique not null
status            : enum(active,inactive,suspended) default=active
created_at        : datetime UTC
updated_at        : datetime UTC nullable
```

### otp_verifications
```
id                : str UUID pk
email             : str not null indexed
otp               : str not null
purpose           : enum(registration, forgot_password) not null
expires_at        : datetime UTC not null
verified          : bool default=False
retry_count       : int default=0
organization_name : str nullable  ← stores org name for tenant creation
created_at        : datetime UTC
```

### refresh_tokens
```
id         : str UUID pk
user_id    : str FK→users.id not null indexed
token      : str unique not null indexed
expires_at : datetime UTC not null
is_revoked : bool default=False
created_at : datetime UTC
```

---

## 5. SETTINGS (core/config.py)

```python
from core.config import settings

settings.DATABASE_URL
settings.JWT_SECRET_KEY
settings.JWT_ALGORITHM                  # "HS256"
settings.ACCESS_TOKEN_EXPIRE_MINUTES   # 30
settings.REFRESH_TOKEN_EXPIRE_DAYS     # 7
settings.OTP_TOKEN_EXPIRE_MINUTES      # 5
settings.OTP_LENGTH                    # 6
settings.OTP_MAX_RETRY                 # 5
settings.OTP_RESEND_COOLDOWN_SECONDS   # 60
settings.COOKIE_SECURE                 # False dev / True prod
settings.COOKIE_SAMESITE               # "lax"
settings.COOKIE_HTTPONLY               # True
settings.ACCESS_TOKEN_COOKIE           # "access_token"
settings.REFRESH_TOKEN_COOKIE          # "refresh_token"
settings.OTP_TOKEN_COOKIE              # "otp_token"
settings.ENVIRONMENT                   # "development"
settings.DEBUG                         # True
settings.APP_NAME
settings.APP_VERSION
settings.ALLOWED_ORIGINS
```

---

## 6. SECURITY FUNCTIONS (core/security.py)

```python
from core.security import (
    hash_password,          # (plain: str) -> str
    verify_password,        # (plain: str, hashed: str) -> bool
    generate_otp,           # () -> str  e.g. "482910"
    create_access_token,    # (user_id, email, account_type) -> str
    create_refresh_token,   # (user_id) -> str
    create_otp_token,       # (email, purpose) -> str
    decode_access_token,    # (token) -> dict
    decode_refresh_token,   # (token) -> dict
    decode_otp_token,       # (token) -> dict
)
```

---

## 7. COOKIE FUNCTIONS (core/cookies.py)

```python
from core.cookies import (
    set_access_token_cookie,        # (response, token) -> None
    set_refresh_token_cookie,       # (response, token) -> None
    set_otp_token_cookie,           # (response, token) -> None
    clear_access_token_cookie,      # (response) -> None
    clear_refresh_token_cookie,     # (response) -> None
    clear_otp_token_cookie,         # (response) -> None
    clear_all_auth_cookies,         # (response) -> None
    get_access_token_from_cookie,   # (request) -> str | None
    get_refresh_token_from_cookie,  # (request) -> str | None
    get_otp_token_from_cookie,      # (request) -> str | None
)
```

---

## 8. EXCEPTIONS (core/exceptions.py)

```python
from core.exceptions import (
    EmailAlreadyExistsError,     # 409
    InvalidCredentialsError,     # 401
    AccountNotActiveError,       # 403
    AccountNotFoundError,        # 404
    OTPInvalidError,             # 400
    OTPExpiredError,             # 400
    OTPMaxRetryError,            # 429
    OTPCooldownError,            # 429 → takes seconds: int
    OTPAlreadyVerifiedError,     # 400
    TokenMissingError,           # 401 → takes token_name: str
    TokenInvalidError,           # 401
    TokenExpiredError,           # 401
    RefreshTokenInvalidError,    # 401
    PermissionDeniedError,       # 403
    ValidationError,             # 422 → takes detail: str
)
# NEVER use raw HTTPException — always use above classes
```

---

## 9. EMAIL SERVICE (core/email.py)

```python
from core.email import email_service

email_service.send_registration_otp(to_email, full_name, otp)
email_service.send_forgot_password_otp(to_email, full_name, otp)
email_service.send_resend_otp(to_email, full_name, otp, purpose)
```

---

## 10. DEPENDENCIES (core/dependencies.py)

```python
from core.dependencies import get_current_user
# Usage: current_user: User = Depends(get_current_user)
# Reads access_token from cookie first, then Authorization header
# Raises TokenMissingError, TokenExpiredError, AccountNotActiveError
```

---

## 11. SERVICE CALL FLOW

```
POST /auth/register
  AuthService.register(db, response, payload)

POST /auth/verify-otp
  OTPService.verify_registration_otp(db, response, request, otp)
    → returns email
  AuthService.activate_account(db, response, email)

POST /auth/resend-otp
  OTPService.resend_otp(db, response, request)

POST /auth/login
  AuthService.login(db, response, payload)

POST /auth/forgot-password
  AuthService.forgot_password(db, response, email)

POST /auth/verify-forgot-otp
  OTPService.verify_forgot_password_otp(db, response, request, otp)

POST /auth/reset-password
  TokenService.extract_email_from_otp_cookie(request, "forgot_password")
    → returns email
  AuthService.reset_password(db, response, email, new_password)

POST /auth/logout
  get_refresh_token_from_cookie(request)
  AuthService.logout(db, response, refresh_token, user_id)

POST /auth/refresh-token
  TokenService.extract_refresh_token_from_cookie(request)
    → returns raw token
  AuthService.refresh_access_token(db, response, refresh_token)
```

---

## 12. CODING RULES (enforce in every session)

```
1. All IDs are UUID strings — never integers
2. All datetimes: datetime.now(timezone.utc) — always timezone-aware
3. All DB queries: async/await + SQLAlchemy 2.x select() style
4. Use db.flush() not db.commit() — get_db owns the commit
5. Never log passwords, OTP values, or full tokens
6. Never accept email from request body in verify-otp or reset-password
7. Always use exceptions from core.exceptions — never raw HTTPException
8. All imports: absolute paths only
9. Pydantic v2 syntax: model_config = ConfigDict(...)
10. routes/__init__.py must remain EMPTY
```

---

## 13. SESSION OPENING TEMPLATE

Paste this at the top of EVERY new Claude account session:

```
## SESSION CONTEXT — AI SaaS Backend (Auth Module)

Stack: Python / FastAPI / PostgreSQL / SQLAlchemy Async / Pydantic v2

## MY TASK THIS SESSION
[describe your specific task]

## WHAT IS BUILT — DO NOT REBUILD
core/: config, database, exceptions, security, cookies, email,
       dependencies, logging_config
models/: user, tenant, otp_verification, refresh_token
schemas/: auth, response, user
services/: auth_service, otp_service, token_service
routes/: auth (9 endpoints), users (GET /me only)
main.py: active

## RULES
- Read PROJECT_CONTRACT.md section 4-12 before writing any code
- Use exact field names from section 4
- Use exact function signatures from sections 6-10
- Never use raw HTTPException
- db.flush() not db.commit()
- routes/__init__.py must stay empty
- Never accept email from frontend in verify-otp or reset-password
```

---

## 14. GIT BRANCH STRATEGY

```
main
├── feat/auth-core       ← core/ files
├── feat/auth-models     ← models/
├── feat/auth-schemas    ← schemas/
├── feat/auth-services   ← services/
└── feat/auth-routes     ← routes/ + main.py
```