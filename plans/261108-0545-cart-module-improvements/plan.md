# Plan: Cải thiện module Giỏ hàng (Cart Improvements)

Ngày: 2026-11-08 · Work context: `/home/huyquang/Workspace/School/cosme-shop`
Phạm vi: **FE only** (cart là client-side 100%, không có endpoint BE cho cart — `docs/rules.md` §9.3).
Nội dung: xoá giỏ khi đăng xuất · chặn qty vượt giới hạn · clear giỏ khi tạo đơn · nút xoá tất cả ·
revalidate giá & tồn kho của giỏ · bật nút "Thêm vào giỏ" trên ProductCard.

## Bối cảnh

Giỏ hàng hiện là Zustand store persist vào `localStorage` (`frontend/src/store/cartStore.ts`,
key `cart-storage`). Backend **không** có endpoint cart — chỉ nhận `product_id/variant_id/qty`
lúc checkout và tự tính tiền + trừ kho (`backend/app/service/order_service.py` → `create_order`).

Đã xác minh 5 vấn đề thật:

| # | Vấn đề | Bằng chứng |
|---|---|---|
| 1 | Giỏ **không** được xoá khi logout → user B thấy giỏ của user A (key persist hằng số) | `store/authStore.ts:38-42` không gọi `clearCart` |
| 2 | Token hết hạn (401) cũng gọi `logout()` → nếu nhét `clearCart` vào trong sẽ **mất giỏ oan** | `api/axios.ts:44` gọi `useAuthStore.getState().logout()` |
| 3 | `qty` vượt 99 → BE trả **422** (Pydantic) không có message tiếng Việt, khác hẳn 400 của service | `backend/app/schemas/order.py:14` `qty: int = Field(..., gt=0, le=99)` |
| 4 | SePay: đóng modal chưa thanh toán → **đơn đã tạo + kho đã trừ** nhưng giỏ còn → checkout lại tạo đơn thứ 2 | `pages/user/CheckoutPage.tsx:74-82` chỉ `clearCart()` ở nhánh COD |
| 5 | Giá trong giỏ là **snapshot** lúc thêm; server tính lại từ DB → tổng hiển thị ≠ tổng thực trả nếu admin đổi giá | `order_service.py:246-254` tính lại `item_price` |

Ngoài ra: `ProductCard` đã có prop `onAddToCart` nhưng **không nơi nào truyền vào** → nút
"Thêm vào giỏ" không bao giờ hiển thị (`components/ProductCard.tsx:12`).

## Quyết định thiết kế (đã chốt với user)

- **Xoá giỏ khi logout** dùng tham số tuỳ chọn `logout({ clearCart: true })` — chỉ 2 call site
  **chủ động** (SiteHeader, AdminLayout) mới truyền `clearCart`. 401 interceptor giữ nguyên giỏ.
- **Không làm merge giỏ guest** khi login — giỏ đã tự tồn tại qua localStorage nên hành vi
  "mua trước, đăng nhập sau" **đã hoạt động sẵn**. `docs/02-business-requirement.md:399` ghi
  "tùy chọn" → YAGNI, bỏ qua.
- **Clear giỏ ngay khi đơn được tạo** (cả COD lẫn SePay) — đơn đã lưu đủ snapshot `order_items`,
  giữ giỏ không mang lại giá trị gì, chỉ gây rủi ro tạo đơn trùng.
- **Revalidate giá/tồn kho** bằng `useQueries` gọi `GET /api/products/{id}` cho từng item giỏ
  (endpoint public, không cần auth). Không tạo endpoint bulk mới (YAGNI).
- **Không đụng backend** — mọi thay đổi đều là hardening phía FE, không nới lỏng validation nào.

## Phase

| Phase | Nội dung | Trạng thái |
|---|---|---|
| [P1](phase-01-clear-cart-on-logout.md) | FE: `logout({ clearCart })` + 2 call site chủ động | ✅ Đã làm |
| [P2](phase-02-clamp-item-quantity.md) | FE: clamp `qty` về [1, 99] ở store + `InputNumber` | ✅ Đã làm |
| [P3](phase-03-clear-cart-on-order-created.md) | FE: clear giỏ ngay khi đơn SePay/COD tạo thành công | ✅ Đã làm |
| [P4](phase-04-cart-page-ux-actions.md) | FE: nút "Xoá tất cả" + link "Tiếp tục mua sắm" ở `CartPage` | ✅ Đã làm |
| [P5](phase-05-revalidate-cart-price-and-stock.md) | FE: đồng bộ giá/tồn kho giỏ từ API + cảnh báo | ✅ Đã làm |
| [P6](phase-06-enable-add-to-cart-on-product-card.md) | FE: bật nút "Thêm vào giỏ" trên ProductCard (3 nơi dùng) | ✅ Đã làm |
| [P7](phase-07-docs-and-verify.md) | Docs + lint + tsc build verify | ✅ Đã làm |

## Dependency

```
P1 (logout clearCart)      ── độc lập ──┐
P2 (clamp qty)             ── độc lập ──┤
P3 (clear cart on order)   ── độc lập ──┤
P4 (cart page UX)          ── độc lập ──┼──> P7 (docs + verify)
P5 (revalidate giá)        ── cần P2 ───┤
P6 (ProductCard add-to-cart) ── độc lập ┘
```

P1–P4, P6 độc lập nhau (có thể làm song song). P5 cần P2 vì cùng đụng `cartStore.ts` và
cùng bộ field của `CartItem`. P7 chạy sau cùng.

## Success Criteria (tổng)

- [ ] `cd frontend && npm run lint` → exit 0
- [ ] `cd frontend && npx tsc -b` → exit 0
- [ ] `cd frontend && npm run build` → exit 0
- [ ] Đăng nhập → thêm giỏ → **đăng xuất** → badge giỏ = 0, `localStorage['cart-storage'].items = []`
- [ ] Token hết hạn (401) → giỏ **còn nguyên** (không bị xoá)
- [ ] `addItem` với `qty = 150` → giỏ lưu `qty = 99`
- [ ] Checkout SePay → đóng modal chưa thanh toán → giỏ **đã trống** (không tạo đơn trùng khi bấm lại)
- [ ] Admin đổi giá sản phẩm → mở lại `/cart` → giá hiển thị **khớp** giá server
- [ ] Trang `/products` → bấm "Thêm vào giỏ" trên card → badge header tăng đúng

## Rủi ro chung

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| `authStore` import `cartStore` tạo circular import | Thấp | `cartStore` không import `authStore` → không có vòng. Đã kiểm tra. |
| `syncItems` ghi đè `qty` user vừa sửa | Trung bình | `syncItems` chỉ merge metadata (`price`/`name`/`image_url`/`stock`), **không** đụng `qty` |
| Revalidate ghi đè lúc user đang sửa số lượng | Trung bình | Tách bước: `syncItems` merge theo key `product_id+variant_id`, `qty` giữ nguyên của store |
| `useQueries` gọi N request khi giỏ lớn | Thấp | Chấp nhận (giỏ thường < 20 item). Endpoint bulk = follow-up nếu cần |
| `logout()` gọi từ interceptor 401 xoá oan giỏ | Cao | Dùng tham số tuỳ chọn, **không** sửa `api/axios.ts` |
| Sửa `ProductCard` wrapper `<Link>` → ảnh hưởng layout | Thấp | Giữ nguyên `<Link>`, chỉ thêm prop; refactor HTML chỉ khi cần |

## Câu hỏi còn mở

- Có nên thêm `vitest` + test cho `cartStore`? `docs/rules.md:704-709` yêu cầu test cho store Zustand
  nhưng FE hiện **chưa có** vitest lẫn test file nào. → **Để phase sau** (ngoài phạm vi đã chốt).
- Có nên namespace key persist theo `userId` thay vì xoá giỏ khi logout? → **Đã chốt: không**,
  xoá giỏ khi logout đơn giản hơn và đáp ứng đúng nhu cầu.
- Có nên hiển thị cảnh báo "đơn chưa thanh toán" khi user quay lại giỏ sau khi đóng modal SePay?
  → **Không** trong scope này (đơn đã có trong `/orders`).

## Ghi chú

- `docs/02-business-requirement.md:399` ghi "Giỏ hàng guest | Lưu `localStorage`, merge khi login (tùy chọn)"
  → sau P1 sẽ ghi rõ hành vi thực tế (xoá khi chủ động đăng xuất, giữ khi token hết hạn).
- `docs/rules.md` §9.3 sẽ bổ sung dòng về hành vi logout.
