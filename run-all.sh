#!/usr/bin/env bash
#
# Chạy đồng thời Backend (FastAPI) + Frontend (Vite) trên Linux/macOS.
# Dùng: ./run-all.sh
# Nhấn Ctrl+C để dừng cả hai tiến trình.

set -uo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

log() { printf '\033[36m[dev]\033[0m %s\n' "$*"; }
err() { printf '\033[31m[dev][error]\033[0m %s\n' "$*" >&2; }

PIDS=()

cleanup() {
    log "Đang dừng các tiến trình..."
    for pid in "${PIDS[@]:-}"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
    log "Đã dừng."
    exit 0
}
trap cleanup INT TERM EXIT

# ---------------------------------------------------------------- Backend
if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    log "Tạo virtualenv cho backend..."
    python3 -m venv "$BACKEND_DIR/.venv" || { err "Không tạo được venv"; exit 1; }
    "$BACKEND_DIR/.venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt" \
        || { err "Cài dependencies thất bại"; exit 1; }
    "$BACKEND_DIR/.venv/bin/pip" install -r "$BACKEND_DIR/requirements-dev.txt" \
        || { err "Cài dev dependencies thất bại"; exit 1; }
fi

if [[ ! -f "$BACKEND_DIR/.env" ]]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    log "Đã tạo backend/.env từ .env.example (NHỚ điền DATABASE_URL, JWT_SECRET_KEY...)"
fi

log "Khởi động backend tại http://localhost:$BACKEND_PORT"
(
    cd "$BACKEND_DIR"
    exec ./.venv/bin/python -m uvicorn app.main:app \
        --host "${HOST:-0.0.0.0}" \
        --port "$BACKEND_PORT" \
        --reload
) &
PIDS+=($!)

# ---------------------------------------------------------------- Frontend
if ! command -v npm >/dev/null 2>&1; then
    err "Không tìm thấy npm. Cài Node.js 20+ trước khi chạy frontend."
    exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    log "Cài dependencies cho frontend..."
    (cd "$FRONTEND_DIR" && npm install) || { err "npm install thất bại"; exit 1; }
fi

if [[ ! -f "$FRONTEND_DIR/.env" ]]; then
    printf 'VITE_API_URL=http://localhost:%s\n' "$BACKEND_PORT" > "$FRONTEND_DIR/.env"
    log "Đã tạo frontend/.env (VITE_API_URL=http://localhost:$BACKEND_PORT)"
fi

log "Khởi động frontend tại http://localhost:$FRONTEND_PORT"
(
    cd "$FRONTEND_DIR"
    exec npm run dev -- --port "$FRONTEND_PORT"
) &
PIDS+=($!)

log "FE: http://localhost:$FRONTEND_PORT  |  BE: http://localhost:$BACKEND_PORT"
wait
