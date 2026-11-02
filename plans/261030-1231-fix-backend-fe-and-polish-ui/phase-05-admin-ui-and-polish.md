# Phase 05 — Admin UI, git hygiene, docs, tests

Context links: `frontend/src/pages/admin/Dashboard.tsx`, `frontend/src/pages/admin/Orders.tsx`,
`frontend/src/components/AdminLayout.tsx`, `backend/app/main.py`,
`plans/261013-0453-uat-readiness-fix/reports/uat-checklist.md`.

Priority: P1 · Status: ✅ Hoàn thành (2026-10-31)

## Yêu cầu

R1. Dashboard dùng `GET /api/admin/stats` (Phase 02) thay vì đếm thủ công.
R2. Admin Orders: phân trang server-side, hiện chi tiết đơn trong modal.
R3. Admin Products: form thêm/sửa đủ field (skin_types, concerns, key_ingredients, free_from, variants), upload ảnh.
R4. Dọn git: bỏ track `frontend/.env` và `__pycache__`.
R5. Cập nhật docs cho khớp code thực tế.
R6. Thêm test backend tối thiểu.

## R1 — Dashboard mới

Thay nội dung `frontend/src/pages/admin/Dashboard.tsx`:

```tsx
import { Card, Row, Col, Statistic, Typography, Table, Tag, List, Progress } from 'antd';
import {
  ShoppingCartOutlined,
  UserOutlined,
  ShoppingOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/axios';
import { formatPrice } from '../../utils/constants';

const { Title, Text } = Typography;

interface Stats {
  total_orders: number;
  total_revenue: string;
  pending_revenue: string;
  total_products: number;
  total_users: number;
  orders_by_status: Record<string, number>;
  revenue_by_day: { day: string; revenue: string; orders: number }[];
  top_products: { name: string; qty: number; revenue: string }[];
  low_stock: { id: number; name: string; stock: number; price: string }[];
}

export default function AdminDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: async () => {
      const res = await api.get('/api/admin/stats');
      return res.data.data as Stats;
    },
  });

  const statCards = [
    { title: 'Doanh thu đã thu', value: formatPrice(data?.total_revenue ?? 0), icon: <DollarOutlined />, color: '#5a9e6f' },
    { title: 'Chờ thu (COD chưa giao)', value: formatPrice(data?.pending_revenue ?? 0), icon: <ShoppingCartOutlined />, color: '#e0a458' },
    { title: 'Tổng đơn hàng', value: data?.total_orders ?? 0, icon: <ShoppingOutlined />, color: '#d9736a' },
    { title: 'Người dùng', value: data?.total_users ?? 0, icon: <UserOutlined />, color: '#7a9cc6' },
  ];

  return (
    <div>
      <Title level={2}>Dashboard</Title>

      <Row gutter={[16, 16]}>
        {statCards.map((card) => (
          <Col key={card.title} xs={24} sm={12} lg={6}>
            <Card loading={isLoading}>
              <Statistic
                title={card.title}
                value={card.value}
                prefix={<span style={{ color: card.color }}>{card.icon}</span>}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={14}>
          <Card title="Sản phẩm bán chạy" loading={isLoading}>
            <Table
              dataSource={data?.top_products ?? []}
              rowKey="name"
              pagination={false}
              size="small"
              columns={[
                { title: 'Sản phẩm', dataIndex: 'name' },
                { title: 'Số lượng', dataIndex: 'qty', width: 100 },
                { title: 'Doanh thu', dataIndex: 'revenue', width: 140, render: (v: string) => formatPrice(v) },
              ]}
            />
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card title="Sắp hết hàng" loading={isLoading}>
            <List
              dataSource={data?.low_stock ?? []}
              renderItem={(item) => (
                <List.Item>
                  <Text>{item.name}</Text>
                  <Tag color={item.stock === 0 ? 'red' : 'orange'}>
                    {item.stock === 0 ? 'Hết hàng' : `Còn ${item.stock}`}
                  </Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Đơn hàng theo trạng thái" style={{ marginTop: 16 }} loading={isLoading}>
        <Row gutter={16}>
          {Object.entries(data?.orders_by_status ?? {}).map(([status, count]) => (
            <Col key={status} xs={12} md={6}>
              <Text type="secondary">{status}</Text>
              <div style={{ fontSize: 22, fontWeight: 600 }}>{count}</div>
            </Col>
          ))}
        </Row>
      </Card>
    </div>
  );
}
```

Không cần thêm thư viện biểu đồ. Nếu muốn biểu đồ doanh thu 7 ngày thì cài `recharts` (khoảng 1 phút) và vẽ `revenue_by_day`. Đề xuất: làm sau, vì `revenue_by_day` thường rỗng khi dữ liệu mới.

## R2 — Admin Orders

- Query hiện tại dùng `size=50` cố định → chuyển sang phân trang server-side (`page`, `size`, `total` từ response).
- Modal cập nhật trạng thái: chỉ cho chọn trạng thái hợp lệ theo máy trạng thái. Backend trả 400 `INVALID_STATUS_TRANSITION` nếu sai, nhưng nên disable lựa chọn không hợp lệ:

```
pending  -> confirmed | cancelled
confirmed-> packing | cancelled
packing  -> shipping
shipping -> delivered
```

Thêm map:

```typescript
const NEXT_STATUS: Record<string, string[]> = {
  pending: ['confirmed', 'cancelled'],
  confirmed: ['packing', 'cancelled'],
  packing: ['shipping'],
  shipping: ['delivered'],
  delivered: [],
  cancelled: [],
};
```

Trong modal, `options={statusOptions.filter((o) => NEXT_STATUS[selectedOrder.status]?.includes(o.value))}`.

- Hiện thêm danh sách items của đơn trong modal (hiện chỉ có tên, SĐT, địa chỉ, tổng tiền).

## R3 — Admin Products form đầy đủ

Hiện form chỉ có: name, price, sale_price, stock, category_id, brand_id, description. Thiếu các field đặc thù mỹ phẩm và ảnh.

Thêm vào form:
- `skin_types`: `Select mode="multiple"` với options từ `SKIN_TYPES`.
- `concerns`: `Select mode="multiple"` với options từ `CONCERNS`.
- `key_ingredients`: `Select mode="tags"`.
- `free_from`: `Select mode="tags"`.
- `category_id` / `brand_id`: đổi từ `InputNumber` sang `Select` tải danh sách từ API (dùng `/api/categories`, `/api/brands`).
- Upload ảnh: dùng endpoint `POST /api/upload/product-image/{product_id}` (đã có sẵn, Admin only). Vì upload cần `product_id`, chỉ cho upload sau khi sản phẩm đã tạo → trong modal edit mới hiện phần upload ảnh.

Lưu ý: `Form.Item` với `Select mode="tags"` trả `string[]` → backend `ProductUpdate.skin_types: list[str] | None` khớp.

Sau khi upload ảnh xong, cần `queryClient.invalidateQueries({ queryKey: ['admin', 'products'] })` và refetch để thấy ảnh mới.

## R4 — Git hygiene

Hiện đang track: `frontend/.env` (chỉ chứa `VITE_API_URL`) và khoảng 74 file `__pycache__/*.pyc`.

Cập nhật `.gitignore` ở root:

```
# Python
__pycache__/
*.py[cod]
.venv/

# Env
.env
.env.local
.env.*.local
```

Gỡ khỏi git index (giữ file trên đĩa):

```bash
cd /home/huyquang/Workspace/School/cosme-shop
git rm -r --cached frontend/.env
git rm -r --cached $(git ls-files | grep '__pycache__') 2>/dev/null
git add .gitignore
```

Kiểm tra lại: `git ls-files | grep -E "__pycache__|\.env$"` → không còn output.

Lưu ý: `frontend/.env` đang được `import.meta.env.VITE_API_URL` sử dụng ở local. Vì `.env` không còn được track, mỗi máy phải copy từ `.env.example`. Nên tạo `frontend/.env.example`:

```
VITE_API_URL=http://localhost:8000
```

Và cập nhật `frontend/README.md` (file đã tồn tại) để nói rõ bước này.

## R5 — Cập nhật docs

`docs/03-tech-stack.md`:
- Xoá phần service `ai` (port 8001), `AI_SERVICE_URL`, `GEMINI_API_KEY`, `OLLAMA_URL` — code không còn dùng.
- Xoá phần `docker-compose` vì repo không có `docker-compose.yml`.
- Sửa ports: frontend Vite chạy port 5173 (mặc định của Vite 8), không phải 3000. Sửa cả `CORS_ORIGINS` trong `backend/.env.example` từ `["http://localhost:3000"]` sang `["http://localhost:5173"]` (khớp với `backend/app/core/config.py` default). Đây là bug thật: copy `.env.example` rồi chạy FE ở 5173 sẽ bị CORS chặn.
- Thêm endpoint `GET /api/admin/stats`.

`docs/02-business-requirement.md`:
- §3.2 ghi rõ filter `skin_types`/`concerns` là OR (đã sửa code theo spec này, giữ nguyên spec).
- §5 máy trạng thái: giữ nguyên.
- Ghi chú §3.7 AI Routine Builder đã bị gỡ ở commit `e8399bb` và hiện tạm không triển khai — sửa mục §9 "Ưu tiên triển khai" và §10 để không còn mâu thuẫn.

`plans/261013-0453-uat-readiness-fix/reports/uat-checklist.md`:
- Appendix A: thêm `GET /api/admin/stats`.
- Appendix B "Known Limitations": cập nhật danh sách (bỏ dòng AI đã gỡ, thêm "SePay polling mới thêm ở phase 03").

## R6 — Test backend tối thiểu

Hiện dự án không có test nào. Thêm pytest cho các luồng quan trọng nhất:

Tạo `backend/requirements-dev.txt`:
```
pytest
pytest-asyncio
httpx
```

Tạo `backend/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

Tạo `backend/tests/conftest.py`:
- Fixture `db_session`: tạo engine async trỏ tới DB test, tạo toàn bộ table, yield session, rollback/drop sau mỗi test.
- Fixture `client`: `httpx.AsyncClient` với `ASGITransport(app=app)`.

Tạo `backend/tests/test_orders.py` — các case:
1. Tạo order COD thành công → 201, `total = subtotal + shipping_fee`, stock bị trừ.
2. Tạo order vượt stock → 400 `VALIDATION_ERROR`.
3. Sản phẩm `is_active=False` → 400.
4. Huỷ đơn `pending` → stock được hoàn lại đúng số lượng ban đầu.
5. Huỷ đơn `shipping` → 400 `INVALID_STATUS_TRANSITION`.
6. Chuyển `pending → confirmed → packing → shipping → delivered` thành công, và `sold_count` tăng.

Tạo `backend/tests/test_payment.py`:
1. Webhook sai API key → 401.
2. Webhook `transfer_type != "in"` → 200 `{"success": true}`, không đổi trạng thái.
3. Webhook với amount thiếu → order vẫn `unpaid`.
4. Webhook hợp lệ → order `paid`, `paid_at` có giá trị.
5. Webhook lặp lại (idempotent) → vẫn `paid`, không lỗi.
6. Webhook cho đơn `cancelled` → không đánh dấu `paid`.

Tạo `backend/tests/test_auth.py`:
1. Đăng ký email trùng → 400 `EMAIL_EXISTS`.
2. Đăng ký password ngắn → 400.
3. Login sai → 401.
4. Login đúng → 200 + token.
5. `GET /api/auth/me` không token → 401.

Tạo `backend/tests/test_products.py`:
1. Filter `skin_types=oily,combination` trả sản phẩm có một trong hai (kiểm tra OR).
2. `PATCH` product với `sale_price: null` → `sale_price` null sau khi GET.
3. Public list không trả sản phẩm `is_active=False`.
4. Admin tạo product → 201; user thường tạo → 403.

Cách chạy:
```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Lưu ý: test cần DB riêng. Đặt `TEST_DATABASE_URL` trong env test, không dùng DB dev (test có ghi/xoá dữ liệu).

## Files cần sửa / tạo

Sửa:
- `frontend/src/pages/admin/Dashboard.tsx`
- `frontend/src/pages/admin/Orders.tsx`
- `frontend/src/pages/admin/Products.tsx`
- `frontend/src/components/AdminLayout.tsx` (header trắng cho khớp theme, bỏ `theme="dark"` nếu muốn đồng bộ)
- `.gitignore` (root)
- `backend/.env.example` (CORS port 5173)
- `docs/03-tech-stack.md`
- `docs/02-business-requirement.md`
- `plans/261013-0453-uat-readiness-fix/reports/uat-checklist.md`
- `frontend/README.md`

Tạo:
- `frontend/.env.example`
- `backend/requirements-dev.txt`
- `backend/pytest.ini`
- `backend/tests/conftest.py`
- `backend/tests/test_orders.py`
- `backend/tests/test_payment.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_products.py`

## Todo

- [x] R1 Dashboard dùng `/api/admin/stats`
- [x] R2 Admin Orders phân trang + filter trạng thái hợp lệ + items trong modal
- [x] R3 Admin Products form đầy đủ + upload ảnh
- [x] R4 git hygiene (`git rm --cached`)
- [x] R5 docs
- [x] R6 test backend (4 file test + conftest)
- [x] `cd frontend && npm run build`
- [x] `cd backend && .venv/bin/pytest`

## Success criteria

- Dashboard hiện doanh thu thật, tổng đơn, tổng user (không còn "1 người dùng"), top sản phẩm, sắp hết hàng.
- Admin bấm trang 2 trong danh sách đơn → gọi API `page=2`.
- Admin chọn trạng thái không hợp lệ không được (option bị ẩn).
- `git ls-files | grep -E "__pycache__|\.env$"` → rỗng.
- `pytest` chạy pass hết, không còn test fail.
- Docs không còn nhắc service AI / docker-compose / port 3000.

## Risk

- Test DB: nếu trỏ nhầm DB dev sẽ xoá dữ liệu thật. Bắt buộc dùng biến môi trường riêng và kiểm tra tên DB trước khi drop.
- Upload ảnh trong form admin cần Cloudinary credentials đã cấu hình; nếu chưa có thì ẩn phần upload, không làm hỏng luồng tạo sản phẩm.
