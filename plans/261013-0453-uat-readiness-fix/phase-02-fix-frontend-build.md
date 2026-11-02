# Phase 02: Fix Frontend Build (24 TypeScript Errors)

## Context Links

- [plan.md](plan.md) — Overview
- [phase-01-fix-backend-blockers.md](phase-01-fix-backend-blockers.md) — Prerequisite
- [frontend/tsconfig.app.json](../../frontend/tsconfig.app.json) — Compiler config
- [frontend/package.json](../../frontend/package.json) — Dependencies

## Overview

- **Priority**: P1 (blocker for production build, dev server vẫn chạy được)
- **Status**: Pending
- **Brief**: Fix 24 TypeScript errors để `npm run build` pass. Tập trung vào 5 lỗi runtime trước, sau đó dọn unused locals.

## Key Insights

### Tại sao Vite dev OK nhưng build fail?

- Vite dev dùng esbuild → skip strict TypeScript check
- `npm run build` chạy `tsc -b && vite build` → tsc check full
- `tsconfig.app.json` có `noUnusedLocals: true`, `noUnusedParameters: true`, `verbatimModuleSyntax: true`

### 3 categories lỗi

1. **Runtime blockers** (5 lỗi) — sửa ngay:
   - `Text cannot be used as JSX component` (admin/Orders.tsx)
   - `ReactNode` phải dùng `import type`
   - `Menu items` với `type:'divider'` không match types
   - `<Input.TextArea prefix={...}>` invalid

2. **Unused locals** (~15 lỗi) — xoá import/decl unused

3. **Type narrowing** (~4 lỗi) — sửa khai báo kiểu

## Requirements

### Functional
- `npm run build` exit code 0
- Tất cả 28 page + 4 component render bình thường
- Vite dev server không có error trong console

### Non-Functional
- Không thay đổi logic UI
- Không xoá type safety hiện có

## Related Code Files

### Modify (priority order)

**Tier 1 — Runtime blockers:**

- [frontend/src/pages/admin/Orders.tsx](../../frontend/src/pages/admin/Orders.tsx) — Dòng 98: `const { Title } = Typography` → `Typography.Text` không destructure được
- [frontend/src/components/ProtectedRoute.tsx](../../frontend/src/components/ProtectedRoute.tsx) — `ReactNode` type import
- [frontend/src/components/AdminRoute.tsx](../../frontend/src/components/AdminRoute.tsx) — `ReactNode` type import
- [frontend/src/components/MainLayout.tsx](../../frontend/src/components/MainLayout.tsx) — `Menu items` type với divider
- [frontend/src/components/AdminLayout.tsx](../../frontend/src/components/AdminLayout.tsx) — `Menu items` type với divider
- [frontend/src/pages/user/ProfilePage.tsx](../../frontend/src/pages/user/ProfilePage.tsx) — `Input.TextArea` không có `prefix`

**Tier 2 — Unused locals:**

- [frontend/src/pages/ProductDetailPage.tsx](../../frontend/src/pages/ProductDetailPage.tsx) — `Card`, `queryClient`, `effectivePrice` unused
- [frontend/src/pages/ProductsPage.tsx](../../frontend/src/pages/ProductsPage.tsx) — `Button` unused
- [frontend/src/pages/RoutineQuizPage.tsx](../../frontend/src/pages/RoutineQuizPage.tsx) — `Result` unused
- [frontend/src/pages/admin/Products.tsx](../../frontend/src/pages/admin/Products.tsx) — `Select` unused
- [frontend/src/pages/user/CheckoutPage.tsx](../../frontend/src/pages/user/CheckoutPage.tsx) — `Spin`, `data` unused
- [frontend/src/pages/user/WishlistPage.tsx](../../frontend/src/pages/user/WishlistPage.tsx) — `isLoading` unused
- [frontend/src/components/MainLayout.tsx](../../frontend/src/components/MainLayout.tsx) — `HeartOutlined`, `Avatar` unused
- [frontend/src/components/AdminLayout.tsx](../../frontend/src/components/AdminLayout.tsx) — `Avatar`, `user` unused

## Implementation Steps

### Step 2.1: Fix `Orders.tsx` Text JSX

Lỗi `Text cannot be used as JSX component` xảy ra vì destructure nhầm:

```typescript
// Hiện tại (lỗi):
const { Title } = Typography;
// → Text dùng trực tiếp <Text> không work
```

Fix:
```typescript
const { Title, Text } = Typography;
```

### Step 2.2: Fix `ReactNode` type-only imports

Trong `ProtectedRoute.tsx` và `AdminRoute.tsx`:

```typescript
// Trước:
import { ReactNode } from 'react';

// Sau:
import type { ReactNode } from 'react';
```

### Step 2.3: Fix Antd `Menu items` type với `type:'divider'`

Trong `MainLayout.tsx` (line ~25) và `AdminLayout.tsx` (line ~60):

```typescript
// Pattern hiện tại (lỗi):
const userMenuItems = [
  { key: 'profile', label: <Link>...</Link> },
  { type: 'divider' },  // ← không match ItemType
  { key: 'logout', ... },
];
```

Fix option A — cast as `ItemType[]`:
```typescript
import type { MenuProps } from 'antd';
const userMenuItems: MenuProps['items'] = [...];
```

Fix option B — dùng `as const` + `satisfies MenuProps['items']`.

Recommend Option A cho đơn giản.

### Step 2.4: Fix `ProfilePage.tsx` Input.TextArea prefix

```typescript
// Trước (lỗi):
<Input.TextArea prefix={<HomeOutlined />} rows={3} />

// Sau: bỏ prefix (TextArea không có):
<Input.TextArea rows={3} />
```

Hoặc dùng Input thường có prefix ở trên, TextArea ở dưới.

### Step 2.5: Dọn unused locals

Với mỗi file, đơn giản xoá tên không dùng khỏi import/destructure.

Chi tiết theo file:

**`ProductDetailPage.tsx`:**
- Import `Card` không dùng → bỏ
- `queryClient` không dùng → bỏ khai báo
- `effectivePrice` ở line 86 không dùng (chỉ line 58 mới dùng) → bỏ hoặc `_effectivePrice`

**`ProductsPage.tsx`:**
- Import `Button` không dùng → bỏ

**`RoutineQuizPage.tsx`:**
- Import `Result` không dùng → bỏ

**`admin/Products.tsx`:**
- Import `Select` không dùng → bỏ

**`user/CheckoutPage.tsx`:**
- Import `Spin` không dùng → bỏ
- Destructure `data` không dùng trong `onSuccess` → đổi thành `_data` hoặc bỏ destructure

**`user/WishlistPage.tsx`:**
- Destructure `isLoading` không dùng → bỏ khỏi query result

**`components/MainLayout.tsx`:**
- Import `HeartOutlined`, `Avatar` không dùng → bỏ
- (Note: `Avatar` được dùng ở `<Avatar icon={<UserOutlined />}>` → KHÔNG bỏ nếu vẫn dùng; kiểm tra lại)

**`components/AdminLayout.tsx`:**
- Import `Avatar` không dùng → bỏ
- Destructure `user` không dùng → bỏ khỏi `useAuthStore()`

### Step 2.6: Verify build pass

```bash
cd /home/huyquang/Workspace/School/cosme-shop/frontend
npm run build 2>&1 | tail -10
```

Expected:
```
✓ built in Xs
```

exit code 0.

### Step 2.7: Verify dev server

```bash
npm run dev -- --port 5173  # background
sleep 3
curl -s http://localhost:5173/ | head -5
```

Hoặc đơn giản start và check console không có error.

## Todo List

- [ ] Step 2.1: Fix `Orders.tsx` Text destructure
- [ ] Step 2.2: Fix ReactNode type-only imports (2 files)
- [ ] Step 2.3: Fix Menu items type (2 files)
- [ ] Step 2.4: Fix Input.TextArea prefix
- [ ] Step 2.5: Cleanup unused locals (~8 files)
- [ ] Step 2.6: Verify `npm run build` exit 0
- [ ] Step 2.7: Verify dev server start không error

## Success Criteria

- `npm run build` exit code 0
- Không có warning TS errors
- Tất cả page render OK khi navigate

## Risk Assessment

### Risk 1: Fix Menu items type ảnh hưởng rendering

- Mitigation: Type chỉ là type annotation — không ảnh hưởng runtime behavior. Sau fix, navigate qua các menu để verify vẫn hoạt động.

### Risk 2: Bỏ `HeartOutlined`/`Avatar` import gây regression

- Mitigation: grep trước khi bỏ:
  ```bash
  grep -r "HeartOutlined\|Avatar" src/components/MainLayout.tsx
  ```

### Risk 3: Build cần install thêm deps

- Mitigation: Sau `npm install` ở phase setup, đã có đủ deps. Nếu thiếu → check `package.json`.

## Security Considerations

- Không thay đổi auth flow, chỉ type fix
- Không touch token handling

## Next Steps

Sau khi Phase 02 xong → [Phase 03: Seed & Smoke Test](phase-03-seed-and-smoke-test.md)