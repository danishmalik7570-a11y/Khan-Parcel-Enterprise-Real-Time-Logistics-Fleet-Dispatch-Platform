# Khan Parcel — Security Architecture & Runbook

## 1. Security Architecture (`SECURITY.md`)

### Authentication & Authorization
- **JWT (JSON Web Tokens)**: Cryptographically signed via HMAC-SHA256. Access tokens expire in 15 minutes (`SIMPLE_JWT.ACCESS_TOKEN_LIFETIME`); Refresh tokens in 7 days.
- **Two-Factor Authentication (2FA)**: Staff accounts (Admin, Dispatcher, Support) require TOTP verification (Google Authenticator / Authy) using RFC 6238 time-synchronized secrets.
- **Brute-Force Attack Mitigation**: Handled by `django-axes` with 5 failed login limit, 15-minute cool-off lockout, and IP/user tracking in Redis.
- **OTP Protection**: Phone OTP codes are stored as salted SHA-256 digests. Rate limited to 3 requests per 10 minutes per phone number with mandatory 30-second cooldown between resends.
- **KYC Document Privacy**: Driver documents are stored privately in MinIO/S3 and served exclusively through short-lived 15-minute presigned authorization URLs.

---

## 2. Operations Runbook (`RUNBOOK.md`)

### Single Command Boot
To build and start the entire stack (PostgreSQL + PostGIS, Redis, MinIO, MailHog, Django Web, Daphne ASGI, Celery Worker, Celery Beat, Nginx):

```bash
# 1. Initialize environment configuration
cp .env.example .env

# 2. Build and launch Docker Compose services
docker compose up -d --build

# 3. Apply database migrations
docker compose exec web python manage.py migrate

# 4. Seed initial Islamabad / Rawalpindi test data
docker compose exec web python manage.py seed_khanparcel
```

### Accessing Platform Components
- **Web Portal / Control Room**: [http://localhost:5173](http://localhost:5173) (Vite dev) or [http://localhost](http://localhost) (Nginx reverse proxy)
- **Django Admin**: [http://localhost/admin/](http://localhost/admin/) (User: `+923000000001`, Pass: `Admin@123456`)
- **OpenAPI Swagger UI**: [http://localhost/api/docs/](http://localhost/api/docs/)
- **MinIO S3 Console**: [http://localhost:9001](http://localhost:9001) (User: `minioadmin`, Pass: `minioadmin`)
- **MailHog Email Sandbox**: [http://localhost:8025](http://localhost:8025)

### Running Operational Diagnostics
```bash
# Liveness probe
curl http://localhost/healthz/

# Readiness check (DB + Redis + Celery ping)
curl http://localhost/readyz/

# Run day operation simulator
docker compose exec web python scripts/simulate_day.py 5
```
