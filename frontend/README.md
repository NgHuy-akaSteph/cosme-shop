# Cosme Shop - Frontend

React 19 + TypeScript + Vite 8 + antd 5 + TanStack Query + Zustand.

## Setup

```bash
cp .env.example .env
npm install
npm run dev
```

Vite dev server chạy ở `http://localhost:5173`. Backend API mặc định ở `http://localhost:8000`
(khai báo trong `.env` qua `VITE_API_URL`).

> `.env` không được commit vào git. Mỗi máy mới cần copy từ `.env.example`.

## Scripts

| Lệnh | Mô tả |
|---|---|
| `npm run dev` | Chạy dev server |
| `npm run build` | Typecheck (`tsc -b`) + build production vào `dist/` |
| `npm run lint` | Chạy ESLint |
| `npm run preview` | Preview bản build |

## Cấu trúc

```
src/
├── api/          # axios client + interceptors
├── components/   # Layout, ProductCard, QrPaymentModal, home/*
├── hooks/        # useProducts
├── pages/        # Trang public + user/* + admin/*
├── store/        # Zustand: authStore, cartStore
├── theme/        # Design tokens (màu, radius, font) cho antd
├── types/        # Type dùng chung: api.ts, product.ts
└── utils/        # constants.ts (formatPrice, bộ lọc da/vấn đề da)
```

## Theme

Màu chủ đạo và design token nằm tại `src/theme/theme.ts` + `src/theme/colors.ts`.
Không hard-code hex rải rác trong component — dùng `colors.primary` từ `src/theme`.
