# Build AI Template API

Build AI Template API is the core component of Build AI Template, responsible for handling all the API requests and responses.

## Project Structure

```bash
/
├── app/
│   ├── main.py               # FastAPI instance creation and route registration entry point
│   ├── routers/              # Route related code
│   │   ├── v1/               # API versioning
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   ├── core/                 # Core configuration, startup settings, etc.
│   │   ├── config.py         # Environment variables and configuration file loading
│   │   ├── security.py       # Security related logic, e.g., password encryption, JWT
│   ├── models/               # Data models, typically SQLAlchemy models
│   │   ├── user.py
│   ├── schemas/              # Pydantic models (request and response validation)
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── message.py
│   ├── crud/                 # Database operations encapsulation (Create, Read, Update, Delete)
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── message.py
│   ├── services/             # Business logic modules
│   │   ├── user_service.py
│   │   ├── email_service.py
│   ├── db/                   # Database initialization and session management
│   │   ├── base.py           # Base class definition
│   ├── dependencies/         # FastAPI Depends related logic
│   │   ├── db.py
│   ├── util/                # Utility functions
│   │   ├── db.py
│   ├── templates/           # Email templates
├── alembic/                  # Database migration directory (if using Alembic)
├── scripts/                  # Scripts directory
├── .env.example            # Environment variables file
├── pyproject.toml           # Project configuration file
├── uv.lock                  # Dependency lock file
├── README.md
```

## Get Started

> ⚠️ Requirements:
>
> - Python: >= 3.10 (3.12.10 recommended)
> - uv: >= 0.6 (0.6.16 recommended)

### Install database with Docker

```bash
cd ./api

bash scripts/run_postgres.sh
bash scripts/run_redis.sh
```

### Configuration

```bash
cp .env.example .env
# Edit .env file
```

### Email Service Configuration

The system supports two email sending methods: `SMTP` and `Resend`. You can configure this via the `MAIL_SEND_METHOD` environment variable.

- **`MAIL_SEND_METHOD=SMTP`**: Uses traditional SMTP servers for sending emails. You need to configure the following variables:
  - `MAIL_USERNAME`: SMTP username
  - `MAIL_PASSWORD`: SMTP password
  - `MAIL_FROM`: Sender's email address
  - `MAIL_PORT`: SMTP server port
  - `MAIL_SERVER`: SMTP server address

- **`MAIL_SEND_METHOD=RESEND`**: Uses the Resend service for sending emails. This is useful when the cloud provider disables SMTP. You need to configure the following variables:
  - `RESEND_API_KEY`: Your Resend API Key
  - `RESEND_MAIL_FROM`: The sender's email address registered with Resend

### Local Development

use [uv](https://docs.astral.sh/uv/getting-started/installation/) to install the dependencies.

```bash
uv sync

# activate virtual environment
source .venv/bin/activate

# run in dev mode in port 8000
python -m app.main
```

### Run with Docker

```bash
docker build -t build-ai-template-api:0.1.0 .

cp .env.example .env
# Edit .env file

docker run -d --name build-ai-template-api \
    -p 8000:8000 \
    -v $(pwd)/.env:/app/.env \
    build-ai-template-api:0.1.0
```

## Stripe Test

### Most commonly used test card numbers

• `4242 4242 4242 4242` → Any future expiry date + any CVC + any billing address (always succeeds)

### Different scenario testing card numbers

• `4000 0000 0000 0002` → 一般拒绝
• `4242 4242 4242 4241` → 错误卡号拒付
• `4000 0000 0000 4954` → 最高风险

[more card numbers](https://docs.stripe.com/testing#use-test-cards)

### Test Webhook

```bash
stripe login

stripe listen --forward-to localhost:8000/api/v1/orders/stripe/webhook
```
