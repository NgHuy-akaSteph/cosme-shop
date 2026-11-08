# Phase 01 — FE: xoá giỏ khi đăng xuất

**Trạng thái:** ✅ Đã làm
**Ưu tiên:** P0

## Context Links

- Store auth: `frontend/src/store/authStore.ts` (`logout()` tại dòng 38-42).
- Store cart: `frontend/src/store/cartStore.ts` (`clearCart()` tại dòng 77-79).
- Call site chủ động: `frontend/src/components/SiteHeader.tsx:43` và `frontend/src/components/AdminLayout.tsx:25`.
- **Không sửa**: `frontend/src/api/axios.ts:44` (401 interceptor gọi `logout()` — phải giữ giỏ).
- Pattern store có action tuỳ biến: không có trong repo → đây là pattern mới, giữ tối giản.

## Overview

**Priority:** P0.

**Current status:** Chưa làm.

**Description:** Thêm tuỳ chọn `clearCart` cho `authStore.logout()`. Khi user **chủ động** đăng xuất
(SiteHeader, AdminLayout) → xoá giỏ hàng. Khi token hết hạn (401 interceptor) → **giữ nguyên** giỏ.

## Key Insights

- `logout()` có **3 call site**: `SiteHeader.tsx:43`, `AdminLayout.tsx:25`, `api/axios.ts:44`.
  Chỉ 2 call site đầu là chủ động.
- **Không** đặt `clearCart()` trực tiếp trong `logout()` — JWT TTL 1 ngày
  (`docs/02-business-requirement.md:398`) nên token hết hạn là chuyện thường xuyên;
  xoá giỏ ở đó là mất dữ liệu oan.
- `authStore` import `cartStore` là **an toàn**: `cartStore.ts` không import `authStore.ts`
  → không có circular import. Đã verify bằng grep.
- `useCartStore.getState()` gọi từ module khác là pattern chuẩn của Zustand (store là singleton,
  không phụ thuộc thứ tự import module).
- `cartStore` dùng `persist` middleware với key `cart-storage` → `clearCart()` sẽ xoá cả
  trong RAM lẫn `localStorage` (persist tự ghi lại state). Đúng ý muốn.

## Requirements

**Functional**
- F1. `logout(options?: { clearCart?: boolean })` — tuỳ chọn, mặc định **không** xoá giỏ.
- F2. Khi `options.clearCart === true` → gọi `useCartStore.getState().clearCart()`.
- F3. `SiteHeader.tsx` → `logout({ clearCart: true })`.
- F4. `AdminLayout.tsx` → `logout({ clearCart: true })`.
- F5. `api/axios.ts` → **không đổi** (mặc định giữ giỏ).

**Non-functional**
- N1. Backward compatible: call site cũ gọi `logout()` không vỡ.
- N2. Không thêm dependency mới.
- N3. Comment giải thích **tại sao** 401 không xoá giỏ (để không ai "tối ưu" nhầm về sau).

## Architecture

```mermaid
flowchart TD
    Header[SiteHeader / AdminLayout<br/>chủ động] -->|logout clearCart: true| Logout["authStore.logout(opts)"]
    Axios[axios interceptor<br/>401 token hết hạn] -->|logout()| Logout
    Logout --> ClearCart["useCartStore.getState().clearCart()"]
    Logout --> ClearToken[xoá auth_token / auth_user]
```

## Related Code Files

**Sửa:**
- `frontend/src/store/authStore.ts`
- `frontend/src/components/SiteHeader.tsx`
- `frontend/src/components/AdminLayout.tsx`

**Tạo:** không.

**Xoá:** không.

## Implementation Steps

1. **Sửa `frontend/src/store/authStore.ts`** — thêm import và đổi signature `logout`:
   ```typescript
   import { create } from 'zustand';
   import { persist } from 'zustand/middleware';
   import { useCartStore } from './cartStore';
   ```
   ```typescript
   interface AuthState {
     user: User | null;
     token: string | null;
     isAuthenticated: boolean;

     // Actions
     login: (user: User, token: string) => void;
     /**
      * Đăng xuất.
      * `clearCart: true` chỉ dùng cho **đăng xuất chủ động** (người dùng bấm nút).
      * Khi token hết hạn (401) gọi `logout()` không tham số -> GIỮ giỏ hàng,
      * tránh mất giỏ chỉ vì hết phiên đăng nhập.
      */
     logout: (options?: { clearCart?: boolean }) => void;
     updateUser: (user: Partial<User>) => void;
   }
   ```
   ```typescript
       logout: (options) => {
         localStorage.removeItem('auth_token');
         localStorage.removeItem('auth_user');
         set({ user: null, token: null, isAuthenticated: false });
         // Chi xoa gio khi user chu dong dang xuat.
         if (options?.clearCart) {
           useCartStore.getState().clearCart();
         }
       },
   ```

2. **Sửa `frontend/src/components/SiteHeader.tsx`** (dòng 43-46):
   ```typescript
     const handleLogout = () => {
       logout({ clearCart: true });
       navigate('/');
     };
   ```

3. **Sửa `frontend/src/components/AdminLayout.tsx`** (dòng 25-28):
   ```typescript
     const handleLogout = () => {
       logout({ clearCart: true });
       navigate('/');
     };
   ```

4. **KHÔNG sửa `frontend/src/api/axios.ts`** — dòng 44 `useAuthStore.getState().logout();` giữ nguyên
   (không truyền `clearCart`) → token hết hạn vẫn giữ giỏ.

5. **Compile check:**
   ```bash
   cd frontend && npx tsc -b
   ```

## Todo

- [ ] T1. Thêm `import { useCartStore } from './cartStore'` vào `authStore.ts`
- [ ] T2. Đổi signature `logout` trong `interface AuthState` + JSDoc giải thích
- [ ] T3. Implement `clearCart` có điều kiện trong `logout`
- [ ] T4. `SiteHeader.tsx` → `logout({ clearCart: true })`
- [ ] T5. `AdminLayout.tsx` → `logout({ clearCart: true })`
- [ ] T6. Verify `api/axios.ts` **không** bị đổi
- [ ] T7. `npx tsc -b` exit 0

## Success Criteria

- [ ] Đăng nhập → thêm vào giỏ → bấm "Đăng xuất" → badge giỏ = 0, `localStorage['cart-storage'].items = []`
- [ ] Admin logout → giỏ cũng trống
- [ ] Token hết hạn → request trả 401 → `api/axios.ts` gọi `logout()` → **giỏ còn nguyên**
- [ ] `npx tsc -b` không lỗi type

## Risk Assessment

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Circular import `authStore` ↔ `cartStore` | Thấp | `cartStore.ts` không import `authStore.ts` → đã verify. Nếu sau này `cartStore` cần biết user → tách sang file `cart-user.ts` riêng. |
| Ai đó gọi `logout()` mà quên `clearCart` | Trung bình | Đặt JSDoc ngay trên interface + comment trong implement. Call site chủ động chỉ có 2, đều đã rõ. |
| `clearCart()` xoá `localStorage` nhưng store trong RAM còn items | Thấp | Zustand `persist` tự serialize lại state sau mỗi `set` → RAM và `localStorage` đồng bộ. Verify tay. |

## Security Considerations

- Không thay đổi cơ chế auth token (`auth_token` / `auth_user` vẫn bị xoá như cũ).
- `clearCart` chỉ xoá dữ liệu client (`localStorage`), không ảnh hưởng server.
- Giỏ không chứa dữ liệu nhạy cảm (tên/giá/ảnh sản phẩm) → không rò rỉ gì khi xoá.

## Next Steps

- P2: clamp `qty` trong `cartStore` (cùng file, làm chung lượt sửa cho đỡ đụng file).
