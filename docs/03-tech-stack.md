# Tech Stack — cosme-shop

Tài liệu này liệt kê chi tiết các dependencies, ports, biến môi trường, lệnh phát triển và yêu cầu hệ thống tối thiểu của dự án `cosme-shop`. Mục đích là để dev mới onboard nhanh và đảm bảo mọi môi trường (dev/staging) đồng nhất.

## 1. Kiến trúc 5 services

```mermaid
flowchart TB
    subgraph Host[Developer machine]
        DC[docker-compose.yml]
    end

    subgraph DockerNetwork[cosme_shop network]
        PG[(postgres:17-alpine<br/>port 5432)]
        AD[adminer:latest<br/>port 8080]
        BE[backend FastAPI<br/>port 8000]
        AI[ai FastAPI<br/>port 8001]
        FE[fe Vite dev<br/>port 3000]
    end

    DC --> PG
    DC --> AD
    DC --> BE
    DC --> AI
    DC --> FE

    FE -->|VITE_API_URL| BE
    BE -->|DATABASE_URL| PG
    BE -->|AI_SERVICE_URL| AI
    AD -->|browser DB GUI| PG
```

Service dependency:

- `fe` chỉ gọi `backend` (qua Axios).
- `backend` gọi `postgres` (DB) và `ai` (Routine Builder).
- `ai` không gọi DB nghiệp vụ, chỉ gọi Gemini API.
- `adminer` chỉ phục vụ debug DB.

## 2. Ports

| Service | Host port | Container port | Mô tả |
|---|---|---|---|
| postgres | 5432 | 5432 | PostgreSQL 17 |
| adminer | 8080 | 8080 | DB GUI (debug only) |
| backend | 8000 | 8000 | FastAPI chính |
| ai | 8001 | 8001 | AI Routine Builder |
| fe | 3000 | 3000 | Vite dev server |

## 3. Dependencies

### 3.1 Backend (`/backend` + `requirements.txt`)

| Package | Version chính | Mục đích |
|---|---|---|
| fastapi | 0.141.x | Web framework |
| uvicorn[standard] | 0.53.x | ASGI server |
| sqlalchemy | 2.0.x | ORM async |
| asyncpg | 0.31.x | PostgreSQL async driver |
| alembic | 1.20.x | DB migration |
| pydantic | 2.13.x | Validation |
| pydantic-settings | 2.15.x | Đọc `.env` |
| python-jose[cryptography] | 3.5.x | JWT |
| passlib[bcrypt] | 1.7.x | Password hashing |
| bcrypt | 5.0.x | Bcrypt backend |
| python-multipart | 0.0.x | Form data |
| httpx | 0.28.x | Gọi AI service |
| python-dotenv | 1.2.x | Load `.env` |

### 3.2 AI service (`/ai` + `requirements.txt`)

| Package | Version chính | Mục đích |
|---|---|---|
| fastapi | 0.141.x | Web framework |
| uvicorn[standard] | 0.53.x | ASGI server |
| google-genai | latest | Gemini SDK |
| pydantic | 2.13.x | Validation |
| pydantic-settings | 2.15.x | Đọc `.env` |
| httpx | 0.28.x | Internal HTTP (nếu cần) |

### 3.3 Frontend (`/fe` + `package.json`)

| Package | Version chính | Mục đích |
|---|---|---|
| react | 19.x | UI library |
| react-dom | 19.x | React DOM |
| react-router-dom | 6.x | Routing |
| @tanstack/react-query | 5.x | Server state |
| zustand | 4.x | Client state |
| axios | 1.x | HTTP client |
| antd | 5.x | UI components |
| vite | 5.x | Build tool / dev server |
| typescript | 5.x | Type system |
| @vitejs/plugin-react | latest | React plugin cho Vite |
| vitest | 2.x | Unit test (devDep) |
| @testing-library/react | latest | Component test (devDep) |
| eslint + typescript-eslint | latest | Lint (devDep) |

## 4. Biến môi trường

### 4.1 `backend/.env`

```dotenv
# Database
POSTGRES_DB=cosme_shop
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret
DATABASE_URL=postgresql+asyncpg://admin:secret@postgres:5432/cosme_shop

# Auth
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_SECONDS=86400

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# AI service
AI_SERVICE_URL=http://ai:8001

# SePay
SEPAY_API_KEY=
SEPAY_BANK_ACCOUNT=
SEPAY_BANK_NAME=
```

### 4.2 `ai/.env`

```dotenv
# LLM
LLM_PROVIDER=gemini
GEMINI_API_KEY=
OLLAMA_URL=http://localhost:11434
```

### 4.3 `fe/.env`

```dotenv
VITE_API_URL=http://localhost:8000
```

### 4.4 Bảng tổng hợp

| Key | Service | Required | Default | Mô tả |
|---|---|---|---|---|
| `POSTGRES_DB` | backend | Có | `cosme_shop` | Tên database |
| `POSTGRES_USER` | backend | Có | `admin` | User DB |
| `POSTGRES_PASSWORD` | backend | Có | `secret` | Password DB |
| `DATABASE_URL` | backend | Có | -- | Full connection string asyncpg |
| `JWT_SECRET_KEY` | backend | Có | `change-me` | Secret ký JWT |
| `JWT_ALGORITHM` | backend | Không | `HS256` | Thuật toán JWT |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | backend | Không | `86400` | 1 ngày |
| `CORS_ORIGINS` | backend | Không | `["http://localhost:3000"]` | Whitelist origin |
| `AI_SERVICE_URL` | backend | Có | `http://ai:8001` | URL AI service nội bộ |
| `SEPAY_API_KEY` | backend | Có (prod) | -- | API key webhook SePay |
| `SEPAY_BANK_ACCOUNT` | backend | Có | -- | STK nhận CK |
| `SEPAY_BANK_NAME` | backend | Có | -- | Tên ngân hàng |
| `LLM_PROVIDER` | ai | Không | `gemini` | `gemini` \| `ollama` |
| `GEMINI_API_KEY` | ai | Có (gemini) | -- | API key Gemini |
| `OLLAMA_URL` | ai | Có (ollama) | -- | URL Ollama local |
| `VITE_API_URL` | fe | Có | `http://localhost:8000` | Base URL backend |

## 5. Lệnh phát triển

### 5.1 Khởi động toàn bộ stack

```bash
# Từ thư mục root cosme-shop
cp backend/.env.example backend/.env
cp ai/.env.example ai/.env
cp fe/.env.example fe/.env

docker compose up -d
docker compose logs -f backend
```

### 5.2 Migration database

```bash
# Trong container backend
docker compose exec backend alembic revision --autogenerate -m "add wishlist"
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1
```

### 5.3 Seed data

```bash
docker compose exec backend python -m app.scripts.seed
```

### 5.4 Frontend dev (không qua Docker)

```bash
cd fe
npm install
npm run dev          # vite dev server
npm run build        # production build
npm run test         # vitest
npm run lint         # eslint
```

### 5.5 Backend dev (không qua Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5.6 AI service dev

```bash
cd ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## 6. Yêu cầu hệ thống tối thiểu

| Thành phần | Yêu cầu |
|---|---|
| Docker Engine | 24.x trở lên |
| Docker Compose | v2.x |
| RAM | 8 GB (4 service + DB) |
| Disk trống | 5 GB (image Docker + DB volume) |
| CPU | 4 cores (khuyến nghị) |
| OS | Linux / macOS / Windows + WSL2 |

## 7. Quyết định kỹ thuật chính

| Quyết định | Lý do |
|---|---|
| Async toàn bộ backend | Hiệu năng, đặc biệt khi gọi AI service |
| `pgvector` bị loại bỏ | AI dùng Gemini trực tiếp, không cần vector store |
| AI tách service riêng | Độc lập deploy, dễ thay đổi LLM provider |
| Giỏ hàng ở FE | Guest cũng có giỏ, giảm tải backend |
| PostgreSQL 17 | Phiên bản ổn định, asyncpg tương thích đầy đủ |
| TypeScript strict FE | Phát hiện bug sớm, code dễ maintain |
| Docker Compose | Đồng nhất môi trường dev, không cài runtime trực tiếp |
