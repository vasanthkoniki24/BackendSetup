# FastAPI Backend — AI Resume Screening & Interview Assistant

A production-grade FastAPI backend with PostgreSQL, SQLAlchemy (async), Alembic migrations, and JWT authentication.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy (Async) |
| Migrations | Alembic |
| Authentication | JWT (python-jose) |
| Password Hashing | bcrypt |
| Validation | Pydantic v2 |
| Server | Uvicorn |

---

## Project Structure

```text
fastapi_app/
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── exceptions.py
│   ├── logging_config.py
│   └── security.py
├── models/
│   ├── __init__.py
│   └── user.py
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── users.py
│   ├── tenants.py
│   ├── marketplace.py
│   ├── subscriptions.py
│   ├── notifications.py
│   ├── admin.py
│   ├── ai_chatbot.py
│   ├── ai_resume.py
│   └── ai_document.py
├── schemas/
│   ├── __init__.py
│   ├── auth.py
│   └── user.py
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── main.py
└── requirements.txt
```

---

## Local Setup

### Prerequisites

* Python 3.11+
* PostgreSQL installed and running
* Git

### Step 1 — Clone the Repository

```bash
git clone [https://github.com/vasanthkoniki24/BackendSetup.git](https://github.com/vasanthkoniki24/BackendSetup.git)
cd BackendSetup
```

### Step 2 — Create Virtual Environment

```bash
python -m venv venv
```

**Activate it:**

*Windows:*
```cmd
venv\Scripts\activate
```

*Mac/Linux:*
```bash
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
APP_NAME=FastAPI App
APP_VERSION=1.0.0
APP_ENV=development
DEBUG=True
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/fastapi_db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Step 5 — Create PostgreSQL Database

```bash
psql -U postgres -c "CREATE DATABASE fastapi_db;"
```

### Step 6 — Run Migrations

```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

### Step 7 — Start the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
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
| GET | `/version` | No | App version |

### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | No | Register new user |
| POST | `/api/v1/auth/login` | No | Login and get tokens |
| POST | `/api/v1/auth/refresh` | No | Refresh access token |
| GET | `/api/v1/auth/me` | Yes | Get current user |
| POST | `/api/v1/auth/logout` | Yes | Logout |

### Users
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users` | Admin | List all users |
| GET | `/api/v1/users/{id}` | Yes | Get user by ID |
| PATCH | `/api/v1/users/{id}` | Yes | Update user |
| DELETE | `/api/v1/users/{id}` | Admin | Delete user |
| POST | `/api/v1/users/me/change-password` | Yes | Change password |

### Tenants
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/tenants` | Yes | List tenants |
| POST | `/api/v1/tenants` | Yes | Create tenant |
| GET | `/api/v1/tenants/{id}` | Yes | Get tenant |
| PATCH | `/api/v1/tenants/{id}` | Yes | Update tenant |
| DELETE | `/api/v1/tenants/{id}` | Yes | Delete tenant |

### Marketplace
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/marketplace` | Yes | List listings |
| POST | `/api/v1/marketplace` | Yes | Create listing |
| GET | `/api/v1/marketplace/{id}` | Yes | Get listing |
| PATCH | `/api/v1/marketplace/{id}` | Yes | Update listing |
| DELETE | `/api/v1/marketplace/{id}` | Yes | Delete listing |

### Subscriptions
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/subscriptions` | Yes | List subscriptions |
| POST | `/api/v1/subscriptions` | Yes | Create subscription |
| GET | `/api/v1/subscriptions/{id}` | Yes | Get subscription |
| PATCH | `/api/v1/subscriptions/{id}` | Yes | Update subscription |
| DELETE | `/api/v1/subscriptions/{id}` | Yes | Cancel subscription |

### Notifications
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/notifications` | Yes | List notifications |
| POST | `/api/v1/notifications/{id}/read` | Yes | Mark as read |
| POST | `/api/v1/notifications/read-all` | Yes | Mark all as read |
| DELETE | `/api/v1/notifications/{id}` | Yes | Delete notification |

### Admin
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/admin/dashboard` | Admin | Admin dashboard |
| GET | `/api/v1/admin/stats` | Admin | App statistics |
| GET | `/api/v1/admin/logs` | Admin | System logs |

### AI Chatbot
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/ai/chatbot/chat` | Yes | Send message |
| GET | `/api/v1/ai/chatbot/history` | Yes | Chat history |
| DELETE | `/api/v1/ai/chatbot/history` | Yes | Clear history |

### AI Resume
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/ai/resume/analyze` | Yes | Analyze resume |
| POST | `/api/v1/ai/resume/score` | Yes | Score resume |
| POST | `/api/v1/ai/resume/interview-questions`| Yes | Generate interview questions |
| GET | `/api/v1/ai/resume/history` | Yes | Resume history |

### AI Document
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/ai/document/analyze` | Yes | Analyze document |
| POST | `/api/v1/ai/document/summarize` | Yes | Summarize document |
| POST | `/api/v1/ai/document/extract` | Yes | Extract data |
| GET | `/api/v1/ai/document/history` | Yes | Document history |

---

## Sample Requests

### Register

```http
POST http://localhost:8000/api/v1/auth/register
Content-Type: application/json

{
    "email": "vasanth@example.com",
    "full_name": "Vasanth Reddy",
    "password": "strongpassword123",
    "role": "user"
}
```

**Response:**

```json
{
    "success": true,
    "message": "Registration successful",
    "id": 1,
    "email": "vasanth@example.com",
    "full_name": "Vasanth Reddy",
    "role": "user",
    "is_active": true,
    "created_at": "2026-06-23T08:47:50.123456Z"
}
```

### Login

```http
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
    "email": "vasanth@example.com",
    "password": "strongpassword123"
}
```

**Response:**

```json
{
    "success": true,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### Authenticated Request

```http
GET http://localhost:8000/api/v1/auth/me
Authorization: Bearer your_access_token_here
```

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
| `refactor`| Code restructure |
| `docs` | Documentation |

---

## Stop and Restart Server

**Stop:**
```text
Ctrl + C
```

**Restart:**
```bash
uvicorn main:app --reload --port 8000
```