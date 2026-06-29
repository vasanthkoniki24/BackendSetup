# AI SaaS Backend — Authentication & User Management API

A production-grade FastAPI backend with PostgreSQL, async SQLAlchemy, Alembic migrations, HTTP-only cookie-based JWT authentication, OTP email verification, and multi-tenant organization support.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy (Async) |
| Migrations | Alembic |
| Authentication | JWT (python-jose) + HTTP-only Cookies |
| Password Hashing | bcrypt (passlib) |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| Email | SMTP (smtplib / Gmail) |
| Server | Uvicorn |

---

## Project Structure

```text
BackendSetup/
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── cookies.py
│   ├── database.py
│   ├── dependencies.py
│   ├── email.py
│   ├── exceptions.py
│   ├── logging_config.py
│   └── security.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── tenant.py
│   ├── otp_verification.py
│   └── refresh_token.py
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   └── users.py
├── schemas/
│   ├── __init__.py
│   ├── auth.py
│   ├── user.py
│   └── response.py
├── services/
│   ├── __init__.py
│   ├── auth_service.py
│   ├── otp_service.py
│   └── token_service.py
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── main.py
└── requirements.txt
```

---

## Database Tables

| Table | Purpose |
|---|---|
| `users` | Individual and Organization user accounts |
| `tenants` | Organization workspaces — auto-created on org registration |
| `otp_verifications` | OTP records for registration and forgot password flows |
| `refresh_tokens` | Persisted refresh tokens with revocation support |

---

## Authentication Architecture

All authentication uses **HTTP-only cookies** — tokens are never exposed to JavaScript.

| Token | Cookie Name | Expiry | Path | Purpose |
|---|---|---|---|---|
| Access Token | `access_token` | 30 minutes | `/` | Authenticate all protected requests |
| Refresh Token | `refresh_token` | 7 days | `/api/v1/auth/refresh-token` | Issue new access tokens |
| OTP Token | `otp_token` | 5 minutes | `/api/v1/auth` | Bind OTP flow to email session |

### Cookie Security Flags

| Flag | Development | Production |
|---|---|---|
| `HttpOnly` | True | True |
| `Secure` | False | True |
| `SameSite` | Lax | Lax / Strict |

---

## Registration Flow

### Individual User

```
POST /api/v1/auth/register
      ↓
Validate Request (email unique, password policy)
      ↓
Create User (is_active = False)
      ↓
Generate 6-digit OTP
      ↓
Store OTP in otp_verifications table
      ↓
Generate OTP JWT → Set in otp_token HTTP-only Cookie
      ↓
Send OTP to Email
      ↓
POST /api/v1/auth/verify-otp  (OTP from email, email from cookie)
      ↓
Activate Account (is_active = True)
      ↓
Issue Access Token + Refresh Token in HTTP-only Cookies
      ↓
Authenticated Session
```

### Organization User

Same as Individual, with two additional steps on activation:

```
      ↓
Activate Account (is_active = True)
      ↓
Auto-Create Tenant (organization_name from OTP record)
      ↓
Assign Tenant Admin Role
      ↓
Issue Access Token + Refresh Token in HTTP-only Cookies
```

---

## Complete Auth Flow

```
Registration
      ↓
OTP Verification
      ↓
Account Activation
      ↓
Login
      ↓
Access Token + Refresh Token
      ↓
HTTP-Only Cookies
      ↓
Authenticated Session
      ↓
Application Access
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- PostgreSQL installed and running
- Git
- Gmail account with App Password enabled (for OTP emails)

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/vasanthkoniki24/BackendSetup.git
cd BackendSetup
```

---

### Step 2 — Create Virtual Environment

```bash
python -m venv venv
```

**Activate:**

Windows (PowerShell):
```powershell
venv\Scripts\activate
```

Mac / Linux:
```bash
source venv/bin/activate
```

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# App
APP_NAME=AI SaaS Backend
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=True

# Database
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/ai_saas_db
DATABASE_ECHO=False

# JWT
JWT_SECRET_KEY=your-super-secret-key-minimum-32-chars-change-in-production
JWT_ALGORITHM=HS256

# Token Expiry
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
OTP_TOKEN_EXPIRE_MINUTES=5

# OTP
OTP_LENGTH=6
OTP_MAX_RETRY=5
OTP_RESEND_COOLDOWN_SECONDS=60

# Cookie
COOKIE_SECURE=False
COOKIE_SAMESITE=lax
COOKIE_HTTPONLY=True
COOKIE_PATH=/

# Cookie Names
ACCESS_TOKEN_COOKIE=access_token
REFRESH_TOKEN_COOKIE=refresh_token
OTP_TOKEN_COOKIE=otp_token

# API
API_PREFIX=/api/v1

# Email (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-gmail-app-password
EMAIL_FROM=your@gmail.com
EMAIL_FROM_NAME=AI SaaS

# CORS
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8000","http://127.0.0.1:8000"]
```

> **Gmail App Password:** Google Account → Security → 2-Step Verification → App Passwords → generate one for "Mail".

---

### Step 5 — Create PostgreSQL Database

```bash
psql -U postgres -c "CREATE DATABASE ai_saas_db;"
```

---

### Step 6 — Run Migrations

```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

---

### Step 7 — Start the Server

```bash
uvicorn main:app --reload --port 8000
```

Server runs at: `http://localhost:8000`

---

## API Documentation

| Tool | URL |
|---|---|
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |

---

## API Endpoints

### System

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Health check |

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | No | Register Individual or Organization user |
| POST | `/api/v1/auth/verify-otp` | No | Verify email OTP — activates account |
| POST | `/api/v1/auth/resend-otp` | No | Resend OTP with cooldown |
| POST | `/api/v1/auth/login` | No | Login — issues access + refresh tokens |
| POST | `/api/v1/auth/forgot-password` | No | Initiate forgot password — sends OTP |
| POST | `/api/v1/auth/verify-forgot-otp` | No | Verify forgot password OTP |
| POST | `/api/v1/auth/reset-password` | No | Reset password after OTP verified |
| POST | `/api/v1/auth/logout` | Yes | Logout — revokes tokens + clears cookies |
| POST | `/api/v1/auth/refresh-token` | No | Rotate refresh token — issues new access token |

### Users

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me` | Yes | Get current authenticated user profile |

---

## Sample Requests

### Register — Individual User

```http
POST http://localhost:8000/api/v1/auth/register
Content-Type: application/json

{
    "full_name": "Vasanth Kumar",
    "email": "vasanth@example.com",
    "password": "SecurePass@123",
    "confirm_password": "SecurePass@123",
    "account_type": "individual"
}
```

**Response — 201:**

```json
{
    "message": "Registration successful. Please check your email for the 6-digit OTP.",
    "email_hint": "v*****@example.com"
}
```

---

### Register — Organization User

```http
POST http://localhost:8000/api/v1/auth/register
Content-Type: application/json

{
    "full_name": "Vasanth Kumar",
    "email": "vasanth@techcorp.com",
    "password": "SecurePass@123",
    "confirm_password": "SecurePass@123",
    "account_type": "organization",
    "organization_name": "TechCorp Solutions"
}
```

**Response — 201:**

```json
{
    "message": "Registration successful. Please check your email for the 6-digit OTP.",
    "email_hint": "v*****@techcorp.com"
}
```

---

### Verify OTP

```http
POST http://localhost:8000/api/v1/auth/verify-otp
Content-Type: application/json

{
    "otp": "847291"
}
```

> Email is NOT sent in the request body — it is extracted automatically from the `otp_token` HTTP-only cookie set during registration.

**Response — 200:**

```json
{
    "message": "Account verified and activated successfully.",
    "user": {
        "id": "9eeeeeee-4a62-46f8-bc12-032ecdcce464",
        "full_name": "Vasanth Kumar",
        "email": "vasanth@techcorp.com",
        "account_type": "organization",
        "is_active": true,
        "created_at": "2026-06-26T13:22:14Z"
    },
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "token_type": "bearer"
}
```

---

### Login

```http
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
    "email": "vasanth@techcorp.com",
    "password": "SecurePass@123"
}
```

**Response — 200:**

```json
{
    "message": "Login successful.",
    "user": {
        "id": "9eeeeeee-4a62-46f8-bc12-032ecdcce464",
        "full_name": "Vasanth Kumar",
        "email": "vasanth@techcorp.com",
        "account_type": "organization",
        "is_active": true
    },
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "token_type": "bearer"
}
```

---

### Get Current User (Protected)

```http
GET http://localhost:8000/api/v1/users/me
Authorization: Bearer your_access_token_here
```

**Response — 200:**

```json
{
    "id": "9eeeeeee-4a62-46f8-bc12-032ecdcce464",
    "full_name": "Vasanth Kumar",
    "email": "vasanth@techcorp.com",
    "account_type": "organization",
    "is_active": true,
    "created_at": "2026-06-26T13:22:14Z"
}
```

---

### Forgot Password

```http
POST http://localhost:8000/api/v1/auth/forgot-password
Content-Type: application/json

{
    "email": "vasanth@techcorp.com"
}
```

**Response — 200:**

```json
{
    "message": "If an account with this email exists, you will receive a password reset OTP shortly."
}
```

---

### Reset Password

```http
POST http://localhost:8000/api/v1/auth/reset-password
Content-Type: application/json

{
    "new_password": "NewSecurePass@456",
    "confirm_password": "NewSecurePass@456"
}
```

> Email extracted from `otp_token` cookie — not from request body.

---

### Logout

```http
POST http://localhost:8000/api/v1/auth/logout
Authorization: Bearer your_access_token_here
```

**Response — 200:**

```json
{
    "message": "Logged out successfully."
}
```

---

### Refresh Token

```http
POST http://localhost:8000/api/v1/auth/refresh-token
```

> `refresh_token` cookie sent automatically by browser. No request body needed.

**Response — 200:**

```json
{
    "message": "Token refreshed successfully.",
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "token_type": "bearer"
}
```

---

## Testing with API Dog (Recommended)

API Dog supports HTTP-only cookies — the closest experience to a real browser.

```
1. Go to https://apidog.com → create free account
2. New Project → Import Data → OpenAPI URL:
   http://localhost:8000/openapi.json
3. Environment → New → base_url = http://localhost:8000
4. Settings → Automatic Cookie Management → ON
5. Test the full flow:
   POST /register → check email → POST /verify-otp
   → POST /login → GET /users/me → POST /refresh-token
   → POST /logout
```

---

## Testing with Swagger UI

Swagger cannot send HTTP-only cookies. Use the Bearer token flow instead.

```
1. Open http://localhost:8000/docs
2. POST /api/v1/auth/login → copy access_token from response body
3. Click Authorize (top right 🔒)
4. Paste access_token → Authorize
5. All protected routes now work via Bearer header
```

---

## Validation Rules

| Field | Rule |
|---|---|
| Email | Valid format, unique per account |
| Password | Minimum 8 characters, must match confirm_password |
| Organization Email | Must be a business domain (no gmail/yahoo/hotmail) |
| Organization Name | Required for account_type = organization |
| Account Type | Required — must be `individual` or `organization` |
| OTP | 6-digit numeric, valid for 5 minutes, max 5 retries |

---

## Error Response Format

All errors follow a consistent envelope:

```json
{
    "success": false,
    "message": "Descriptive error message here"
}
```

| Status | Meaning |
|---|---|
| 400 | Bad request — invalid OTP, expired OTP, password mismatch |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — account not verified |
| 404 | Not found — user does not exist |
| 409 | Conflict — email already registered |
| 422 | Validation error — missing or invalid fields |
| 429 | Too many requests — OTP retry or resend limit exceeded |
| 500 | Internal server error |

---

## Git Workflow

**Create feature branch:**

```bash
git checkout -b feature/your-feature-name
```

**Stage and commit:**

```bash
git add .
git commit -m "feat: your feature description"
```

**Push:**

```bash
git push origin feature/your-feature-name
```

### Commit Convention

| Prefix | Usage |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `chore` | Config, dependencies |
| `refactor` | Code restructure |
| `docs` | Documentation only |
| `test` | Tests added or updated |

---

## Stop and Restart Server

**Stop:**

```
Ctrl + C
```

**Restart:**

```bash
uvicorn main:app --reload --port 8000
```

---

## Completed Deliverables

| Feature | Status |
|---|---|
| Individual User Registration | ✓ Done |
| Organization User Registration | ✓ Done |
| Email OTP Verification | ✓ Done |
| Account Activation | ✓ Done |
| Tenant Auto-Creation (Org) | ✓ Done |
| Tenant Admin Assignment | ✓ Done |
| Login API | ✓ Done |
| HTTP-Only Cookie Auth | ✓ Done |
| Access Token (JWT) | ✓ Done |
| Refresh Token + Rotation | ✓ Done |
| Forgot Password Flow | ✓ Done |
| Reset Password Flow | ✓ Done |
| Logout + Cookie Clearing | ✓ Done |
| Resend OTP with Cooldown | ✓ Done |
| OTP Max Retry Validation | ✓ Done |
| Swagger Bearer Auth Support | ✓ Done |
| Get Current User API | ✓ Done |
| Alembic Migrations | ✓ Done |
| Structured Logging | ✓ Done |
| Global Exception Handling | ✓ Done |