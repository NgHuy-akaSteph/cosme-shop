# Cosme Shop

E-commerce mỹ phẩm: **FastAPI + PostgreSQL (Neon)** ở backend, **React 18 + TypeScript + Vite** ở frontend.

```
cosme-shop/
├── backend/          # FastAPI + SQLAlchemy async + Alembic
├── frontend/         # React + Vite + antd + TanStack Query + Zustand
├── docs/             # Tài liệu thiết kế (system design, DB, tech stack)
├── run-all.bat       # Chạy cả BE + FE trên Windows
└── run-all.sh        # Chạy cả BE + FE trên Linux/macOS
```

---

## 1. Yêu cầu trước khi bắt đầu (Windows)

| Công cụ | Phiên chuẩn | Cách cài |
|---|---|---|
| Python | 3.13 (đã pin trong `.python-version`) | https://www.python.org/downloads/windows/ — **nhớ tick "Add python.exe to PATH"** |
| Node.js | 20.19+ hoặc 22.12+ (LTS) | https://nodejs.org/ — bản `.msi` mặc định đã cài kèm `npm` |
| Git | mới nhất | https://git-scm.com/download/win |
| PostgreSQL | Neon cloud (khuyến nghị) hoặc local | https://neon.tech/ |

Kiểm tra môi trường mở **PowerShell**:

```powershell
python --version
node --version
npm --version
git --version
```

> Lưu ý PowerShell mặc định chặn script: nếu `python` báo *"not recognized"*, chạy lại terminal mới hoặc thêm Python vào `PATH`.

---

## 2. Clone dự án

```powershell
cd $HOME\Workspace\School
git clone <repo-url> cosme-shop
cd cosme-shop
```

---

## 3. Cấu hình biến môi trường

### 3.1 Backend — `backend\.env`

```powershell
copy backend\.env.example backend\.env
```

Mở `backend\.env` bằng VS Code và điền:

| Biến | Bắt buộc | Mô tả |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://<user>:<password>@<host>/<db>` — lấy từ Neon Dashboard → Connection Details → **Pooled connection**. Không thêm `?sslmode=require` (asyncpg sẽ lỗi) |
| `JWT_SECRET_KEY` | ✅ | Chuỗi ngẫu nhiên dài, dùng để ký JWT |
| `AUTO_MIGRATE` | ⬜ | `true` = tự chạy `alembic upgrade head` mỗi lần start app (mặc định `false`) |
| `CORS_ORIGINS` | ⬜ | JSON array, mặc định `["http://localhost:5173"]` |
| `SEPAY_API_KEY` / `SEPAY_WEBHOOK_SECRET` / `SEPAY_API_TOKEN` / `SEPAY_BANK_ACCOUNT` / `SEPAY_BANK_NAME` | ⬜ | Cấu hình thanh toán SePay (VietQR) |
| `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | ⬜ | Upload ảnh sản phẩm. `CLOUDINARY_UPLOAD_PRESET` mặc định `cosme_shop_unsigned` |

Sinh `JWT_SECRET_KEY` an toàn:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 3.2 Frontend — `frontend\.env`

```powershell
copy frontend\.env.example frontend\.env
```

```env
VITE_API_URL=http://localhost:8000
```

> `.env` đã nằm trong `.gitignore` — không commit lên git. Mỗi máy mới phải copy từ `.env.example`.

---

## 4. Cài đặt & chạy Backend (Windows)

Mở PowerShell tại thư mục gốc dự án:

```powershell
cd backend

# 1) Tạo virtualenv
python -m venv .venv

# 2) Kích hoạt virtualenv
.\.venv\Scripts\Activate.ps1
```

> Nếu PowerShell báo *"running scripts is disabled"*:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
> Hoặc dùng CMD thay thì: `.venv\Scripts\activate.bat`

```powershell
# 3) Cài dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt     # pytest, httpx (chỉ khi chạy test)

# 4) Tạo bảng trong database
alembic upgrade head

# 5) (Tùy chọn) Nạp dữ liệu mẫu
python -m app.scripts.seed
```

Tài khoản mẫu sau khi seed:

| Email | Mật khẩu | Vai trò |
|---|---|---|
| `admin@cosme-shop.com` | `admin123` | admin |
| `user@cosme-shop.com` | `user123` | user |

Chạy dev server:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Kiểm tra: <http://localhost:8000/health> → `{"status":"ok"}` · Swagger UI: <http://localhost:8000/docs>

> Có thể bỏ qua bước 4 và đặt `AUTO_MIGRATE=true` trong `.env` để app tự migrate khi khởi động.

---

## 5. Cài đặt & chạy Frontend (Windows)

Mở **cửa sổ PowerShell thứ hai** tại thư mục gốc dự án:

```powershell
cd frontend

npm install
npm run dev
```

Frontend: <http://localhost:5173> · tự proxy/gọi API qua `VITE_API_URL` (mặc định `http://localhost:8000`)

### Scripts frontend

| Lệnh | Mô tả |
|---|---|
| `npm run dev` | Dev server (HMR) |
| `npm run build` | Typecheck (`tsc -b`) + build production → `frontend\dist\` |
| `npm run preview` | Preview bản build (`http://localhost:4173`) |
| `npm run lint` | ESLint |

### Build production (frontend)

```powershell
cd frontend
npm run build          # -> frontend\dist\
npm run preview
```

Bản build là file tĩnh — có thể deploy lên Nginx, Netlify, Vercel hoặc serve bằng `npx serve dist`.

---

## 6. Chạy cả Backend + Frontend cùng lúc (Windows)

Có sẵn script `run-all.bat` ở thư mục gốc. Script tự:

1. Kiểm tra `python` / `npm` đã cài.
2. Tạo `.venv` + cài `requirements-dev.txt` nếu chưa có.
3. Copy `.env.example` → `.env` cho backend & frontend nếu chưa có.
4. `npm install` frontend nếu chưa có `node_modules`.
5. Mở 2 cửa sổ cmd: backend (port 8000) và frontend (port 5173).

```powershell
run-all.bat
```

Đổi port (mặc định `BACKEND_PORT=8000`, `FRONTEND_PORT=5173`):

```powershell
$env:BACKEND_PORT = "8080"
$env:FRONTEND_PORT = "3000"
run-all.bat
```

> Nhớ sửa `VITE_API_URL` trong `frontend\.env` và `CORS_ORIGINS` trong `backend\.env` nếu đổi port.

Đóng cửa sổ cmd của từng tiến trình để dừng.

---

## 7. Chạy test

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
```

Test suite **tự skip** nếu chưa set `TEST_DATABASE_URL` (để không xóa nhầm dữ liệu dev). Nếu muốn chạy thật:

```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://<user>:<password>@<host>/<db>"
$env:TEST_DATABASE_SCHEMA = "test_schema"
pytest
```

> `TEST_DATABASE_SCHEMA` nên trỏ tới schema riêng. Fixture có kiểm tra `current_schema()` và **abort** nếu trỏ nhầm schema `public` (bảo vệ dữ liệu dev).

---

## 8. Lệnh thường dùng (PowerShell)

```powershell
# Backend
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000   # chạy server
alembic upgrade head                                  # áp dụng migration
alembic revision --autogenerate -m "add x field"     # tạo migration mới
pytest                                                # chạy test

# Frontend
cd frontend
npm run dev
npm run build
npm run lint
```

---

## 9. Xử lý sự cố trên Windows

| Triệu chứng | Cách xử lý |
|---|---|
| `python` không được nhận | Cài lại Python và tick **Add python.exe to PATH**, mở terminal mới |
| `.\.venv\Scripts\Activate.ps1` bị chặn | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: No module named 'app'` | Phải chạy lệnh từ thư mục `backend\` (dùng `python -m ...` từ `backend`) |
| `alembic` không phải lệnh | `.\.venv\Scripts\alembic.exe upgrade head` hoặc activate venv trước |
| Lỗi kết nối DB / `SSL connection has been closed` | Kiểm tra `DATABASE_URL` dùng **Pooled connection** của Neon; không thêm `?sslmode=require` |
| `alembic` báo lỗi `Can't locate revision` | DB chưa có bảng `alembic_version` → xoá bảng trong Neon Console rồi `alembic upgrade head` |
| CORS error ở console trình duyệt | Thêm đúng origin vào `CORS_ORIGINS` (JSON array), ví dụ `["http://localhost:5173"]` |
| Frontend không gọi được API | Kiểm tra `frontend\.env` có `VITE_API_URL=http://localhost:8000` và **restart** `npm run dev` |
| Port 8000/5173 đã bị chiếm | `netstat -ano | findstr :8000` rồi `taskkill /PID <pid> /F`, hoặc đổi `BACKEND_PORT`/`FRONTEND_PORT` |
| `uvloop` lỗi khi cài trên Windows | `uvloop` chỉ hỗ trợ Linux/macOS — bỏ qua, Windows dùng `asyncio` mặc định |

### Lỗi build khi deploy (Koyeb)

| Triệu chứng | Cách xử lý |
|---|---|
| Build fail với `Failed to build 'uvloop==…'` / `Building uvloop==…` | Image build dùng Python quá mới (vd 3.15) không có sẵn wheel `cp3xx` → `uv` phải compile từ source rồi fail vì thiếu tool build (`/usr/bin/file`) |
| `Using CPython 3.15.0` trong build log | Sửa file `.python-version` ở thư mục gốc service (repo root hoặc `backend/`) về `3.13.0` — Koyeb yêu cầu đủ 3 thành phần `major.minor.patch` và chỉ hỗ trợ `3.9`–`3.13` |
| Build vẫn dùng Python cũ sau khi sửa | Xoá build cache / clone service mới, hoặc deploy lại từ commit mới có file `.python-version` |

### Lỗi runtime khi deploy (Koyeb) — build OK nhưng container crash

| Triệu chứng | Cách xử lý |
|---|---|
| `RuntimeError: To use the fastapi command, please install "fastapi[standard]"` trong log runtime (app restart liên tục) | Koyeb tự chạy lệnh start bằng FastAPI CLI (`/app/.venv/bin/fastapi`) nhưng `fastapi-cli` chưa được cài. Đã fix: thêm `fastapi-cli==0.0.32` vào `backend/requirements.txt` **và** file `backend/Procfile` (lệnh start tường minh bằng `uvicorn`) |
| Muốn ép lệnh start riêng | Service Settings → Builder → **Run command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --forwarded-allow-ips=*` (ghi đè `Procfile`) |
| App start nhưng không nhận traffic | Kiểm tra Exposed port đang là `8000:http` và route `/:8000`; Koyeb tự set `PORT` = port thấp nhất được expose |

---

## 10. Linux/macOS (tham khảo)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python -m uvicorn app.main:app --reload

# terminal khác
cd frontend && npm install && npm run dev
```

Hoặc chạy cả hai: `./run-all.sh`

---

## 11. Cấu trúc & tài liệu

```
backend/app/
├── api/          # Router FastAPI (auth, products, orders, admin, payment, upload...)
├── core/         # config, security (hash/JWT), cloudinary
├── db/           # session, base
├── model/        # SQLAlchemy models
├── schemas/      # Pydantic schemas
├── service/      # Business logic
├── payment/      # SePay (VietQR) provider + registry
└── scripts/      # seed.py, migrate seed images lên Cloudinary

frontend/src/
├── api/          # axios client + interceptors
├── components/   # Layout, ProductCard, QrPaymentModal...
├── hooks/        # useProducts
├── pages/        # public + user/* + admin/*
├── store/        # Zustand: authStore, cartStore
├── theme/        # Design tokens cho antd
├── types/        # Type dùng chung
└── utils/        # constants.ts
```

Tài liệu chi tiết: [`docs/`](./docs) — system design, business requirement, tech stack, database schema.
