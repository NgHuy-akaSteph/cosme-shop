# Phase 03 — Frontend bugfix (lỗi hiển thị, type, phân trang, thanh toán)

Context links: `frontend/src/types/api.ts`, `frontend/src/pages/user/CheckoutPage.tsx`,
`frontend/src/pages/user/ProfilePage.tsx`, `frontend/src/pages/ProductDetailPage.tsx`,
`frontend/src/pages/admin/Products.tsx`, `frontend/src/pages/user/OrdersPage.tsx`,
`frontend/src/pages/user/OrderDetailPage.tsx`, `frontend/src/pages/admin/Users.tsx`,
`frontend/src/pages/user/CartPage.tsx`, `frontend/src/components/QrPaymentModal.tsx`.

Priority: P0 · Status: ✅ Hoàn thành (2026-10-31)

## Yêu cầu

R1. Mọi thông báo lỗi API đọc đúng `message`/`detail`.
R2. Sửa type sai của `ProductDetailPage.images`.
R3. `OrdersPage` phân trang server-side.
R4. `UsersPage` phân trang server-side.
R5. Polling trạng thái thanh toán SePay + không mất QR khi user tắt modal.
R6. Giỏ hàng: sau khi đặt hàng SePay, không clear cart trước khi xác nhận thanh toán.
R7. Bỏ `any` ở các file chính.

## R1 — Đọc đúng message lỗi

Helper đã có sẵn trong `frontend/src/types/api.ts`:

```typescript
export function getErrorMessage(error: ApiError, fallback = 'Đã xảy ra lỗi'): string {
  return error.response?.data?.detail || error.response?.data?.message || fallback;
}
```

Nhưng 6 chỗ bypass helper, đọc trực tiếp `error.response?.data?.detail` — trong khi backend trả `{message, code}` cho `HTTPException` nên `detail` là `undefined`:

| File | Dòng |
|---|---|
| `frontend/src/pages/user/CheckoutPage.tsx` | 56 |
| `frontend/src/pages/user/ProfilePage.tsx` | 24, 37 |
| `frontend/src/pages/ProductDetailPage.tsx` | 79 |
| `frontend/src/pages/admin/Products.tsx` | 49, 64 |

Sửa mỗi chỗ theo mẫu ( ví dụ CheckoutPage):

```typescript
import type { ApiError } from '../../types/api';
import { getErrorMessage } from '../../types/api';
...
onError: (error: ApiError) => {
  message.error(getErrorMessage(error, 'Đặt hàng thất bại'));
},
```

Lưu ý `ApiErrorResponse` đã khai báo `detail?: string; message?: string;` → type-safe.

## R2 — Type `images` sai

`frontend/src/pages/ProductDetailPage.tsx` khai báo:

```typescript
images: string[] | null;
```

Nhưng backend `_product_to_dict` trả `images` là list object (`id`, `url`, `secure_url`, `is_main`, `position`...). Sửa thành:

```typescript
interface ProductImage {
  id: number;
  url: string;
  secure_url: string | null;
  alt_text: string | null;
  position: number;
  is_main: boolean;
}

interface Product {
  ...
  images: ProductImage[] | null;
}
```

Trong Phase 04 sẽ dùng `images` này để làm gallery.

## R3 — OrdersPage phân trang server-side

`frontend/src/pages/user/OrdersPage.tsx` hiện gọi `/api/orders` không có `page`/`size` → lấy mặc định 20, nhưng bảng dùng `pagination={{ pageSize: 10 }}` của antd (client-side) → chỉ hiện 10 dòng và không tải trang 2.

Sửa thành query có `page`, `size`, `total`:

```typescript
const [page, setPage] = useState(1);
const pageSize = 10;

const { data: ordersData, isLoading } = useQuery({
  queryKey: ['orders', page],
  queryFn: async () => {
    const res = await api.get(`/api/orders?page=${page}&size=${pageSize}`);
    return res.data as { data: Order[]; total: number };
  },
});

const orders = ordersData?.data ?? [];
```

Và bảng:

```typescript
<Table
  dataSource={orders}
  columns={columns}
  rowKey="id"
  loading={isLoading}
  pagination={{
    current: page,
    pageSize,
    total: ordersData?.total ?? 0,
    showSizeChanger: false,
    onChange: setPage,
  }}
/>
```

## R4 — UsersPage phân trang server-side

`frontend/src/pages/admin/Users.tsx` gọi `/api/admin/users` không param → lấy 20 user, phân trang client-side. Sửa giống R3 với `page`/`size` và `total` từ response (sau Phase 01 R1, `total` đã đúng).

## R5 + R6 — Luồng thanh toán SePay

Vấn đề hiện tại:
- `CheckoutPage` gọi `clearCart()` ngay khi tạo đơn thành công, rồi mở `QrPaymentModal`.
- Nếu user đóng modal (nút X), họ ở lại `/checkout` với giỏ trống và không có đường quay lại QR.
- Không có polling → user không biết khi nào đơn được đánh dấu paid.

Cách sửa đề xuất (giữ phạm vi nhỏ, không thêm trang mới):

**a) `QrPaymentModal` thêm polling và nút "Đã tôi thanh toán xong".**

Sửa `frontend/src/components/QrPaymentModal.tsx`:

```typescript
import { Modal, Image, Typography, Space, Button, Alert, Spin } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import api from '../api/axios';

interface QrPaymentModalProps {
  visible: boolean;
  qrUrl: string | null;
  orderId?: number;
  onClose: () => void;
  onContinue: () => void;
  onPaid?: () => void;
}

export default function QrPaymentModal({ visible, qrUrl, orderId, onClose, onContinue, onPaid }: QrPaymentModalProps) {
  const paidNotified = useRef(false);

  const { data: paymentStatus } = useQuery({
    queryKey: ['payment-status', orderId],
    queryFn: async () => {
      const res = await api.get(`/api/payment/status/${orderId}`);
      return res.data.data as { order_code: string; payment_status: string; paid_at: string | null };
    },
    enabled: visible && Boolean(orderId),
    refetchInterval: (query) => {
      const status = query.state.data?.payment_status;
      return status === 'paid' ? false : 4000;
    },
  });

  useEffect(() => {
    if (paymentStatus?.payment_status === 'paid' && !paidNotified.current) {
      paidNotified.current = true;
      onPaid?.();
    }
  }, [paymentStatus, onPaid]);

  const isPaid = paymentStatus?.payment_status === 'paid';

  return (
    <Modal
      title="Thanh toán bằng QR Code"
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="continue" type="primary" onClick={onContinue}>
          {isPaid ? 'Xem đơn hàng' : 'Tôi đã thanh toán'}
        </Button>,
      ]}
      centered
      destroyOnHidden
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {isPaid ? (
          <Alert type="success" showIcon message="Thanh toán thành công!" description="Đơn hàng của bạn đã được ghi nhận thanh toán." />
        ) : (
          <>
            <Text>Vui lòng quét mã QR bên dưới để thanh toán qua SePay:</Text>
            {qrUrl && (
              <div style={{ textAlign: 'center' }}>
                <Image src={qrUrl} alt="QR Code" width={250} />
              </div>
            )}
            <Text type="secondary" style={{ fontSize: 12 }}>
              Trang này tự động cập nhật, bạn không cần tải lại trang.
            </Text>
            <div style={{ textAlign: 'center' }}>
              <Spin size="small" /> <Text type="secondary">Đang chờ thanh toán...</Text>
            </div>
          </>
        )}
      </Space>
    </Modal>
  );
}
```

Lưu ý kỹ thuật:
- `refetchInterval` trả `false` để dừng poll khi đã paid.
- Dùng `useRef` để chỉ gọi `onPaid` một lần.
- `destroyOnHidden` (antd 5.25+) để reset state khi đóng/mở lại. Nếu antd báo cảnh báo prop này chưa có, dùng `destroyOnClose`.
- Backend `GET /api/payment/status/{id}` sau Phase 01 R2 đã yêu cầu token → user đang đăng nhập nên OK.

**b) `CheckoutPage` không clear cart trước khi biết kết quả.**

Hiện tại:

```typescript
onSuccess: (data) => {
  clearCart();
  message.success('Đặt hàng thành công!');
  if (paymentMethod === 'sepay' && data.data?.qr_url) {
    setQrUrl(data.data.qr_url);
    setShowQrModal(true);
  } else {
    navigate('/orders');
  }
},
```

Sửa thành:

```typescript
onSuccess: (data) => {
  const orderId = data.data?.order?.id;
  const qrUrl = data.data?.qr_url ?? null;

  // COD: thanh toan khi nhan hang -> xoa gio ngay
  if (paymentMethod === 'cod') {
    clearCart();
    message.success('Đặt hàng thành công!');
    navigate(`/orders/${orderId}`);
    return;
  }

  // SePay: giu gio cho den khi xac nhanh thanh toan
  setQrUrl(qrUrl);
  setOrderId(orderId);
  setShowQrModal(true);
},
```

Và phần hiển thị modal:

```typescript
<QrPaymentModal
  visible={showQrModal}
  qrUrl={qrUrl}
  orderId={orderId}
  onClose={() => setShowQrModal(false)}
  onPaid={() => {
    clearCart();
    message.success('Thanh toán thành công!');
  }}
  onContinue={() => {
    setShowQrModal(false);
    navigate(`/orders/${orderId}`);
  }}
/>
```

Thêm state `const [orderId, setOrderId] = useState<number | undefined>(undefined);`.

Lưu ý: nếu user đóng modal bằng X thì giỏ vẫn còn. Cần một lối thoát rõ ràng: thêm link "Xem đơn hàng" trong modal, và ở `CheckoutPage` hiển thị alert nhắc nhở nếu đã tạo đơn SePay nhưng chưa thanh toán. Cách đơn giản nhất: khi đóng modal, chuyển hướng tới `/orders/{orderId}` — vì ở trang đó có thông tin đơn và nút quay lại QR sau (Phase 05).

**c) `OrderDetailPage` hiện lại QR cho đơn SePay chưa thanh toán.**

Thêm vào `frontend/src/pages/user/OrderDetailPage.tsx`, trong `Col xs={24} lg={16}`, trên `<Card title="Sản phẩm">`:

```typescript
{order.payment_method === 'sepay' && order.payment_status !== 'paid' && order.status !== 'cancelled' && (
  <QrPaymentModal
    visible={showQr}
    qrUrl={buildQrUrl(order)}
    orderId={order.id}
    onClose={() => setShowQr(false)}
    onPaid={() => message.success('Thanh toán thành công!')}
    onContinue={() => setShowQr(false)}
  />
)}
```

Và một nút "Quét mã QR để thanh toán" trong phần trạng thái thanh toán.

Về `buildQrUrl`: backend không trả `qr_url` cho đơn đã tạo (chỉ trả lúc tạo). Có 2 lựa chọn:
- **Lựa chọn A (khuyến nghị):** thêm `qr_url` vào response của `GET /api/orders/{id}` khi đơn là sepay và chưa paid. Backend tạo lại URL từ `settings.SEPAY_BANK_ACCOUNT` + `order.order_code` + `order.total`. Nhỏ gọn, giữ logic ở server.
- **Lựa chọn B:** dựng URL ở FE từ env `VITE_SEPAY_BANK_ACCOUNT`. Không khuyến nghị vì lộ config ra FE và lệch với server.

Triển khai Lựa chọn A — trong `backend/app/api/orders.py`, thêm helper:

```python
def _build_sepay_qr_url(order) -> str | None:
    """Dung QR URL SePay cho don sepay chua thanh toan."""
    if order.payment_method != "sepay" or order.payment_status == "paid":
        return None
    if not settings.SEPAY_BANK_ACCOUNT:
        return None
    return (
        f"https://qr.sepay.vn/img?"
        f"acc={settings.SEPAY_BANK_ACCOUNT}"
        f"&bank={settings.SEPAY_BANK_NAME or ''}"
        f"&amount={order.total}"
        f"&des={order.order_code}"
    )
```

Thêm `"qr_url": _build_sepay_qr_url(order)` vào dict trả về của `GET /api/orders/{id}`.

Cần `from app.core.config import settings` trong `orders.py`.

## R7 — Bỏ `any`

File còn `any`:
- `frontend/src/pages/admin/Products.tsx` (6)
- `frontend/src/pages/user/ProfilePage.tsx` (6)
- `frontend/src/pages/user/CartPage.tsx` (4)
- `frontend/src/pages/ProductDetailPage.tsx` (2)
- `frontend/src/pages/user/WishlistPage.tsx` (3)
- `frontend/src/pages/admin/Categories.tsx` (4)
- `frontend/src/pages/admin/Brands.tsx` (4)
- `frontend/src/pages/user/CheckoutPage.tsx` (3)
- `frontend/src/pages/user/OrdersPage.tsx` (1)
- `frontend/src/pages/user/RegisterPage.tsx` (1)

Cách làm: thay `any` bằng type cụ thể đã có sẵn hoặc khai báo mới. Ví dụ trong `CartPage.tsx`:

```typescript
import type { CartItem } from '../../store/cartStore';

const columns = [
  {
    title: 'Sản phẩm',
    dataIndex: 'name',
    render: (_: unknown, record: CartItem) => ( ... ),
  },
];
```

Với `mutationFn: async (values: any)` → định nghĩa interface form, ví dụ:

```typescript
interface ProductFormValues {
  name: string;
  price: number;
  sale_price?: number | null;
  stock: number;
  category_id: number;
  brand_id: number;
  description?: string;
}
```

Không bắt buộc làm hết trong phase này; làm cho các file sẽ sửa ở Phase 04-05 (`Products.tsx`, `CheckoutPage.tsx`, `ProductDetailPage.tsx`, `OrdersPage.tsx`). Các file còn lại để sau.

## Files cần sửa

- Sửa: `frontend/src/types/api.ts` (giữ nguyên, chỉ dùng)
- Sửa: `frontend/src/components/QrPaymentModal.tsx`
- Sửa: `frontend/src/pages/user/CheckoutPage.tsx`
- Sửa: `frontend/src/pages/user/OrderDetailPage.tsx`
- Sửa: `frontend/src/pages/user/OrdersPage.tsx`
- Sửa: `frontend/src/pages/user/ProfilePage.tsx`
- Sửa: `frontend/src/pages/ProductDetailPage.tsx`
- Sửa: `frontend/src/pages/admin/Products.tsx`
- Sửa: `frontend/src/pages/admin/Users.tsx`
- Sửa: `backend/app/api/orders.py` (thêm `qr_url` — cần cho R5c)
- Không tạo file mới.

## Todo

- [x] R1 error message ở 6 file
- [x] R2 type `images`
- [x] R3 OrdersPage server pagination
- [x] R4 UsersPage server pagination
- [x] R5 BE `qr_url` trong GET order + FE polling modal
- [x] R6 CheckoutPage không clear cart sớm
- [x] R7 bỏ `any` ở 4 file ưu tiên
- [x] `cd frontend && npx tsc -p tsconfig.app.json --noEmit` (compile check)
- [x] `cd frontend && npm run build`

## Success criteria

- Đặt hàng vượt stock → toast hiện đúng message từ backend (vd: "Sản phẩm X không đủ stock"), không phải "Đặt hàng thất bại".
- Checkout SePay → modal hiện QR, poll mỗi 4s, tự chuyển sang báo "Thanh toán thành công" khi webhook bắn; giỏ vẫn còn cho tới lúc đó.
- `/orders` hiện đủ số đơn, bấm trang 2 gọi API với `page=2`.
- `/admin/users` hiện tổng user đúng, bấm trang 2 gọi API với `page=2`.
- `npm run build` exit 0.

## Risk

- Polling 4s × nhiều tab có thể tăng tải nhẹ. Chấp nhận được ở quy mô đồ án.
- `refetchInterval` với function cần react-query v5 API — package đang ở `^5.80.2` nên OK.
- Nếu `SEPAY_BANK_ACCOUNT` rỗng thì `qr_url` null → FE phải fallback sang thông báo "chưa cấu hình thanh toán", không phải modal trống.
