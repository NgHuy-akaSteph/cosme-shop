# Phase 04 — Frontend UI refactor (theme, ProductCard, trang chủ, danh sách, chi tiết)

Context links: `frontend/src/App.tsx`, `frontend/src/components/MainLayout.tsx`,
`frontend/src/pages/HomePage.tsx`, `frontend/src/pages/ProductsPage.tsx`,
`frontend/src/pages/ProductDetailPage.tsx`, `frontend/src/utils/constants.ts`,
`frontend/src/store/cartStore.ts`.

Priority: P1 · Status: ✅ Hoàn thành (2026-10-31)

## Nguyên tắc

- Giữ antd 5 + React 19. Không đổi framework, không thêm template ngoài.
- Tách component trước khi làm đẹp, tránh copy-paste.
- Theme tập trung ở `ConfigProvider` + 1 file token, không rải màu hex rải rác.
- Mỗi file giữ dưới 200 dòng.

## Yêu cầu

R1. Theme design token tập trung (màu, font, bo góc, shadow).
R2. Tạo `ProductCard` dùng chung + hook `useProducts`.
R3. Làm lại `MainLayout`: header trắng, logo, ô tìm kiếm, menu responsive, footer nhiều cột.
R4. Làm lại `HomePage`: hero có ảnh, lưới danh mục, dải thương hiệu, hàng mới về, điểm tin cậy.
R5. `ProductsPage`: thanh lọc bên cạnh với loại da / vấn đề da / khoảng giá.
R6. `ProductDetailPage`: gallery nhiều ảnh, tab thông tin, khối sản phẩm tương tự.
R7. Bỏ inline style rải rác, chuyển sang token + class CSS.

## R1 — Theme token

Tạo `frontend/src/theme/theme.ts`:

```typescript
import type { ThemeConfig } from 'antd';

/** Design tokens cua Cosme Shop - mau nude/hong cam cho nganh my pham. */
export const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: '#d9736a',
    colorInfo: '#d9736a',
    colorSuccess: '#5a9e6f',
    colorWarning: '#e0a458',
    colorError: '#c85a5a',
    colorTextBase: '#2c2622',
    colorBgLayout: '#faf7f5',
    borderRadius: 10,
    fontFamily:
      "'Be Vietnam Pro', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 14,
    controlHeight: 38,
    boxShadowSecondary: '0 4px 20px rgba(44, 38, 34, 0.08)',
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      headerHeight: 68,
      headerPadding: '0 32px',
      bodyBg: '#faf7f5',
      footerBg: '#ffffff',
    },
    Card: {
      borderRadiusLG: 16,
      paddingLG: 20,
    },
    Menu: {
      horizontalItemSelectedColor: '#d9736a',
      horizontalItemHoverColor: '#d9736a',
    },
    Table: {
      headerBg: '#f5efec',
      headerColor: '#5a514c',
    },
  },
};
```

Tạo `frontend/src/theme/index.ts` re-export để import gọn.

Trong `frontend/src/App.tsx`, thay khối `theme={{ token: { colorPrimary: '#fa8c16' } }}`:

```tsx
import { themeConfig } from './theme';
...
<ConfigProvider locale={viVN} theme={themeConfig}>
```

Thêm Google Font vào `frontend/index.html` (trong `<head>`):

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap"
  rel="stylesheet"
/>
```

Lưu ý: sau khi đổi màu primary, các chỗ hard-code `color: '#fa8c16'` trong FE phải đổi theo. Phase này sẽ xử lý ở R3-R6. Grep tìm `'#fa8c16'` để không sót.

## R2 — ProductCard + hook dùng chung

Tạo `frontend/src/types/product.ts`:

```typescript
export interface ProductImage {
  id: number;
  url: string;
  secure_url: string | null;
  alt_text: string | null;
  position: number;
  is_main: boolean;
}

export interface ProductVariant {
  id: string;
  name: string;
  price?: number | null;
  stock?: number | null;
  image_url?: string | null;
}

export interface Product {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  price: number | string;
  sale_price: number | string | null;
  stock: number;
  image_url: string | null;
  category_id: number;
  brand_id: number;
  skin_types: string[] | null;
  concerns: string[] | null;
  key_ingredients: string[] | null;
  free_from: string[] | null;
  variants: ProductVariant[] | null;
  sold_count: number;
  rating_avg: number;
  rating_count: number;
  is_active: boolean;
  category: { id: number; name: string; slug: string } | null;
  brand: { id: number; name: string; slug: string } | null;
  images: ProductImage[] | null;
}
```

Tạo `frontend/src/components/ProductCard.tsx`:

```tsx
import { Link } from 'react-router-dom';
import { Card, Tag, Typography, Button, Skeleton } from 'antd';
import { ShoppingCartOutlined, ShoppingOutlined } from '@ant-design/icons';
import { formatPrice } from '../utils/constants';
import type { Product } from '../types/product';

const { Text } = Typography;

interface ProductCardProps {
  product: Product;
  onAddToCart?: (product: Product) => void;
}

export default function ProductCard({ product, onAddToCart }: ProductCardProps) {
  const hasDiscount = Boolean(product.sale_price);
  const discountPercent =
    hasDiscount && Number(product.price) > 0
      ? Math.round((1 - Number(product.sale_price) / Number(product.price)) * 100)
      : 0;

  return (
    <Link to={`/products/${product.id}`} style={{ display: 'block', height: '100%' }}>
      <Card
        hoverable
        variant="borderless"
        styles={{ body: { padding: 16 } }}
        style={{ height: '100%', borderRadius: 16, overflow: 'hidden' }}
        cover={
          <div
            style={{
              height: 220,
              background: 'linear-gradient(160deg, #fdf6f2 0%, #f3e8e2 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
            }}
          >
            {product.image_url ? (
              <img
                src={product.image_url}
                alt={product.name}
                loading="lazy"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <ShoppingOutlined style={{ fontSize: 48, color: '#d9c8c0' }} />
            )}

            {hasDiscount && (
              <Tag
                color="#d9736a"
                style={{ position: 'absolute', top: 12, left: 12, margin: 0, borderRadius: 8 }}
              >
                -{discountPercent}%
              </Tag>
            )}

            {product.stock === 0 && (
              <Tag
                color="default"
                style={{ position: 'absolute', top: 12, right: 12, margin: 0, borderRadius: 8 }}
              >
                Hết hàng
              </Tag>
            )}
          </div>
        }
      >
        <Text type="secondary" style={{ fontSize: 12 }}>
          {product.brand?.name}
        </Text>

        <div
          style={{
            fontWeight: 600,
            margin: '4px 0 8px',
            minHeight: 44,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {product.name}
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          {hasDiscount ? (
            <>
              <Text delete type="secondary" style={{ fontSize: 13 }}>
                {formatPrice(product.price)}
              </Text>
              <Text strong style={{ color: '#d9736a', fontSize: 16 }}>
                {formatPrice(product.sale_price!)}
              </Text>
            </>
          ) : (
            <Text strong style={{ color: '#d9736a', fontSize: 16 }}>
              {formatPrice(product.price)}
            </Text>
          )}
        </div>

        {onAddToCart && (
          <Button
            type="primary"
            block
            icon={<ShoppingCartOutlined />}
            style={{ marginTop: 12 }}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onAddToCart(product);
            }}
            disabled={product.stock === 0}
          >
            Thêm vào giỏ
          </Button>
        )}
      </Card>
    </Link>
  );
}

export function ProductCardSkeleton() {
  return (
    <Card variant="borderless" style={{ borderRadius: 16 }}>
      <Skeleton.Image style={{ width: '100%', height: 220, marginBottom: 16 }} active />
      <Skeleton active paragraph={{ rows: 2 }} />
    </Card>
  );
}
```

Lưu ý kỹ thuật:
- `Card` trong antd 5.25 hỗ trợ `variant="borderless"` thay cho `bordered={false}`. Nếu bản antd trong project không có, dùng `bordered={false}`.
- `Card.Meta` không dùng vì layout cần tùy biến.
- Nút bấm trong `<Link>` cần `e.preventDefault()` để không điều hướng.

Tạo `frontend/src/hooks/useProducts.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import api from '../api/axios';
import type { Product } from '../types/product';

export interface ProductListResponse {
  data: Product[];
  total: number;
  page: number;
  size: number;
}

export function useProducts(params: {
  page?: number;
  size?: number;
  category_id?: number | null;
  brand_id?: number | null;
  search?: string;
  sort?: string;
  skin_types?: string[];
  concerns?: string[];
  min_price?: number | null;
  max_price?: number | null;
}) {
  return useQuery({
    queryKey: ['products', params],
    queryFn: async () => {
      const query = new URLSearchParams();
      query.append('page', String(params.page ?? 1));
      query.append('size', String(params.size ?? 20));
      if (params.category_id) query.append('category_id', String(params.category_id));
      if (params.brand_id) query.append('brand_id', String(params.brand_id));
      if (params.search) query.append('search', params.search);
      if (params.sort) query.append('sort', params.sort);
      if (params.skin_types?.length) query.append('skin_types', params.skin_types.join(','));
      if (params.concerns?.length) query.append('concerns', params.concerns.join(','));
      if (params.min_price != null) query.append('min_price', String(params.min_price));
      if (params.max_price != null) query.append('max_price', String(params.max_price));

      const res = await api.get(`/api/products?${query.toString()}`);
      return res.data as ProductListResponse;
    },
  });
}
```

## R3 — MainLayout mới

Tạo `frontend/src/components/SiteHeader.tsx` ( tách header khỏi layout cho file không quá dài):

```tsx
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Layout, Input, Button, Badge, Dropdown, Avatar, Drawer, Grid } from 'antd';
import type { MenuProps } from 'antd';
import {
  SearchOutlined,
  ShoppingCartOutlined,
  UserOutlined,
  LogoutOutlined,
  ShopOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { useCartStore } from '../store/cartStore';

const { Header } = Layout;

export default function SiteHeader() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [keyword, setKeyword] = useState(searchParams.get('search') ?? '');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuthStore();
  const cartCount = useCartStore((state) => state.getItemCount());
  const screens = Grid.useBreakpoint();

  const handleSearch = () => {
    const params = new URLSearchParams(searchParams);
    if (keyword.trim()) params.set('search', keyword.trim());
    else params.delete('search');
    params.set('page', '1');
    navigate(`/products?${params.toString()}`);
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const userMenuItems: MenuProps['items'] = isAuthenticated
    ? [
        { key: 'profile', label: <Link to="/profile">Tài khoản</Link> },
        { key: 'orders', label: <Link to="/orders">Đơn hàng</Link> },
        { key: 'wishlist', label: <Link to="/wishlist">Yêu thích</Link> },
        ...(user?.role === 'admin' ? [{ key: 'admin', icon: <ShopOutlined />, label: <Link to="/admin">Quản trị</Link> }] : []),
        { type: 'divider' },
        { key: 'logout', icon: <LogoutOutlined />, label: 'Đăng xuất', onClick: handleLogout },
      ]
    : [];

  const navItems = [
    { key: '/', label: <Link to="/">Trang chủ</Link> },
    { key: '/products', label: <Link to="/products">Sản phẩm</Link> },
    { key: '/products?category_id=1', label: <Link to="/products?category_id=1">Skincare</Link> },
  ];

  return (
    <Header
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 24,
        position: 'sticky',
        top: 0,
        zIndex: 100,
        borderBottom: '1px solid #f0e6e1',
      }}
    >
      <Link to="/" style={{ fontSize: 22, fontWeight: 700, color: '#2c2622', whiteSpace: 'nowrap' }}>
        Cosme<span style={{ color: '#d9736a' }}>Shop</span>
      </Link>

      {screens.md ? (
        <nav style={{ display: 'flex', gap: 24 }}>
          {navItems.map((item) => (
            <span key={item.key} style={{ fontWeight: 500 }}>{item.label}</span>
          ))}
        </nav>
      ) : (
        <Button type="text" icon={<MenuOutlined />} onClick={() => setDrawerOpen(true)} />
      )}

      <div style={{ flex: 1, maxWidth: 460, marginLeft: screens.md ? 0 : 'auto' }}>
        <Input
          placeholder="Tìm serum, kem chống nắng..."
          prefix={<SearchOutlined style={{ color: '#c9b8b0' }} />}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={handleSearch}
          allowClear
          style={{ borderRadius: 999 }}
        />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginLeft: 'auto' }}>
        <Link to="/cart">
          <Badge count={cartCount} size="small">
            <Button type="text" shape="circle" icon={<ShoppingCartOutlined />} />
          </Badge>
        </Link>

        {isAuthenticated ? (
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Avatar icon={<UserOutlined />} style={{ cursor: 'pointer', background: '#f3e8e2', color: '#d9736a' }} />
          </Dropdown>
        ) : (
          <Link to="/login">
            <Button type="primary">Đăng nhập</Button>
          </Link>
        )}
      </div>

      <Drawer title="Menu" open={drawerOpen} onClose={() => setDrawerOpen(false)}>
        {navItems.map((item) => (
          <div key={item.key} style={{ padding: '10px 0' }} onClick={() => setDrawerOpen(false)}>
            {item.label}
          </div>
        ))}
      </Drawer>
    </Header>
  );
}
```

Tạo `frontend/src/components/SiteFooter.tsx`:

```tsx
import { Link } from 'react-router-dom';
import { Layout, Typography, Space, Divider } from 'antd';
import { FacebookOutlined, InstagramOutlined, TikTokOutlined } from '@ant-design/icons';

const { Footer } = Layout;
const { Text, Title } = Typography;

export default function SiteFooter() {
  return (
    <Footer style={{ padding: '48px 32px 24px' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 40, justifyContent: 'space-between' }}>
        <div style={{ maxWidth: 280 }}>
          <Title level={4} style={{ marginTop: 0 }}>
            Cosme<span style={{ color: '#d9736a' }}>Shop</span>
          </Title>
          <Text type="secondary">
            Mỹ phẩm chính hãng từ các thương hiệu uy tín trong nước và quốc tế. Giao hàng toàn quốc, đổi trả trong 7 ngày.
          </Text>
        </div>

        <div>
          <Title level={5}>Mua sắm</Title>
          <Space direction="vertical" size={6}>
            <Link to="/products">Tất cả sản phẩm</Link>
            <Link to="/products?sort=best_seller">Bán chạy</Link>
            <Link to="/products?sort=newest">Mới về</Link>
            <Link to="/cart">Giỏ hàng</Link>
          </Space>
        </div>

        <div>
          <Title level={5}>Hỗ trợ</Title>
          <Space direction="vertical" size={6}>
            <Link to="/orders">Tra cứu đơn hàng</Link>
            <Link to="/profile">Tài khoản</Link>
            <span>Chính sách đổi trả</span>
            <span>Liên hệ: 1900 6868</span>
          </Space>
        </div>

        <div>
          <Title level={5}>Kết nối</Title>
          <Space size={16}>
            <FacebookOutlined style={{ fontSize: 20 }} />
            <InstagramOutlined style={{ fontSize: 20 }} />
            <TikTokOutlined style={{ fontSize: 20 }} />
          </Space>
        </div>
      </div>

      <Divider />
      <div style={{ textAlign: 'center' }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          © {new Date().getFullYear()} Cosme Shop. Giao hàng toàn quốc — Freeship từ 500.000đ.
        </Text>
      </div>
    </Footer>
  );
}
```

Rút gọn `frontend/src/components/MainLayout.tsx`:

```tsx
import { Outlet } from 'react-router-dom';
import { Layout } from 'antd';
import SiteHeader from './SiteHeader';
import SiteFooter from './SiteFooter';

const { Content } = Layout;

export default function MainLayout() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <SiteHeader />
      <Content style={{ padding: '0 32px' }}>
        <div style={{ padding: '24px 0', minHeight: 'calc(100vh - 300px)', maxWidth: 1280, margin: '0 auto' }}>
          <Outlet />
        </div>
      </Content>
      <SiteFooter />
    </Layout>
  );
}
```

## R4 — HomePage mới

Cấu trúc trang chủ (mỗi khối một component con để file không quá dài):

- `HeroSection` — ảnh nền Unsplash, tiêu đề, 2 nút CTA, 3 điểm tin cậy (Chính hãng 100% / Freeship từ 500k / Đổi trả 7 ngày).
- `CategoryStrip` — lưới 8 danh mục, mỗi ô có ảnh `image_url` từ API `/api/categories` (backend đã trả `image_url` có sẵn trong seed).
- `FeaturedTabs` — 3 tab: Bán chạy / Mới về / Giảm giá, dùng `useProducts` với `sort` tương ứng (`best_seller`, `newest`, và `min_price=0&max_price=...` cho giảm giá — hoặc đơn giản dùng `newest` cho tab 2 và lọc client-side cho tab giảm giá).
- `BrandStrip` — dải logo thương hiệu từ `/api/brands` (backend `Brand` có `logo_url`).
- `TrustBanner` — 4 icon + mô tả ngắn.

Ví dụ `frontend/src/components/home/FeaturedTabs.tsx`:

```tsx
import { Tabs } from 'antd';
import { Col, Row } from 'antd';
import ProductCard, { ProductCardSkeleton } from '../ProductCard';
import { useProducts } from '../../hooks/useProducts';

const TABS = [
  { key: 'best_seller', label: 'Bán chạy', sort: 'best_seller' },
  { key: 'newest', label: 'Mới về', sort: 'newest' },
  { key: 'discount', label: 'Đang giảm giá', sort: 'price_asc' },
];

export default function FeaturedTabs() {
  return (
    <Tabs
      defaultActiveKey="best_seller"
      items={TABS.map((tab) => ({
        key: tab.key,
        label: tab.label,
        children: <ProductGrid sort={tab.sort} />,
      }))}
    />
  );
}

function ProductGrid({ sort }: { sort: string }) {
  const { data, isLoading } = useProducts({ sort, size: 8 });

  if (isLoading) {
    return (
      <Row gutter={[16, 16]}>
        {Array.from({ length: 8 }).map((_, i) => (
          <Col key={i} xs={12} sm={8} md={6} lg={6}><ProductCardSkeleton /></Col>
        ))}
      </Row>
    );
  }

  return (
    <Row gutter={[16, 16]}>
      {data?.data.map((product) => (
        <Col key={product.id} xs={12} sm={8} md={6} lg={6}>
          <ProductCard product={product} />
        </Col>
      ))}
    </Row>
  );
}
```

Lưu ý: giữ mọi component trong `frontend/src/components/home/`.

## R5 — ProductsPage: filter theo loại da / vấn đề da

BE đã hỗ trợ `skin_types` và `concerns` (dạng CSV). Seed data dùng các giá trị:

- `skin_types`: `oily`, `dry`, `combination`, `normal`, `sensitive`
- `concerns`: `acne`, `dark_spots`, `aging`, `dehydration`, `dullness`, `pores`, `redness`

Thêm 2 hằng số ở `frontend/src/utils/constants.ts`:

```typescript
// Bo loc theo nganh my pham
export const SKIN_TYPES = [
  { value: 'oily', label: 'Da dầu' },
  { value: 'dry', label: 'Da khô' },
  { value: 'combination', label: 'Da hỗn hợp' },
  { value: 'normal', label: 'Da bình thường' },
  { value: 'sensitive', label: 'Da nhạy cảm' },
];

export const CONCERNS = [
  { value: 'acne', label: 'Mụn' },
  { value: 'dark_spots', label: 'Thâm nám' },
  { value: 'aging', label: 'Lão hoá' },
  { value: 'dehydration', label: 'Mất nước' },
  { value: 'dullness', label: 'Xỉn da' },
  { value: 'pores', label: 'Lỗ chân lông' },
  { value: 'redness', label: 'Đỏ da' },
];
```

Layout mới: `Row` với `Col xs={24} lg={18}` cho lưới sản phẩm và `Col xs={24} lg={6}` cho sidebar filter (sticky).

Sidebar filter gồm:
- Tìm kiếm
- Danh mục (Select)
- Thương hiệu (Select)
- Loại da (Checkbox group, multi)
- Vấn đề da (Checkbox group, multi)
- Khoảng giá (Select dạng preset: dưới 200k / 200k-500k / 500k-1tr / trên 1tr)
- Xoá tất cả filter

State đồng bộ với URL (dùng `useSearchParams`) để filter có thể chia sẻ link. `skin_types` và `concerns` lưu dạng CSV trong query string.

Ví dụ xử lý param:

```typescript
const skinTypes = searchParams.get('skin_types')?.split(',').filter(Boolean) ?? [];
const concerns = searchParams.get('concerns')?.split(',').filter(Boolean) ?? [];
```

Và khi đổi:

```typescript
const handleToggleFilter = (key: string, value: string, checked: boolean) => {
  const params = new URLSearchParams(searchParams);
  const current = params.get(key)?.split(',').filter(Boolean) ?? [];
  const next = checked ? [...current, value] : current.filter((v) => v !== value);
  if (next.length) params.set(key, next.join(','));
  else params.delete(key);
  params.set('page', '1');
  setSearchParams(params);
};
```

Lưu ý: Phase 01 R3 đã sửa filter sang OR nên chọn nhiều loại da sẽ trả đúng tập hợp hợp nhất.

## R6 — ProductDetailPage: gallery, tab, sản phẩm tương tự

BE đã có `GET /api/products/{id}/similar` (trả 8 sản phẩm cùng category, sort theo `sold_count`). Hiện FE chưa gọi.

**Gallery:** dùng `product.images` (đã sửa type ở Phase 03 R2). Nếu `images` rỗng thì fallback `image_url`.

```tsx
const galleryImages = product.images?.length
  ? product.images.map((img) => img.secure_url || img.url)
  : product.image_url
    ? [product.image_url]
    : [];
```

Render: ảnh chính lớn + hàng thumbnail bên dưới (hoặc ảnh nhỏ bên trái). Click thumbnail đổi ảnh chính. Dùng `useState` cho index ảnh hiện tại.

**Tabs:** dùng antd `Tabs` với 3 tab:
- "Mô tả": `product.description`
- "Thành phần chính": `key_ingredients` dạng tag
- "Thông tin": bảng `Descriptions` — brand, category, loại da phù hợp, vấn đề giải quyết, số lượng tồn, `sold_count`, `rating_avg`/`rating_count` (backend đã có nhưng FE chưa dùng).

**Sản phẩm tương tự:** thêm query:

```tsx
const { data: similarData } = useQuery({
  queryKey: ['product', id, 'similar'],
  queryFn: async () => {
    const res = await api.get(`/api/products/${id}/similar?limit=8`);
    return res.data.data as Product[];
  },
});
```

Render lưới 4 `ProductCard`.

**Thêm vào giỏ:** hiện `addToCartMutation` dùng `useMutation` không cần thiết vì không gọi API. Đơn giản hoá thành hàm thường + `message.success`. Đồng thời dùng `product.sale_price` khi không có variant (logic hiện tại đã đúng).

Lưu ý bug nhỏ hiện tại: nút "+" giới hạn theo `product.stock` nhưng nếu có variant thì stock của variant mới đúng. Sửa: tính `maxQty = selectedVariant ? (variant.stock ?? product.stock) : product.stock`.

## R7 — Dọn màu hard-code

Grep `'#fa8c16'` trong `frontend/src` và thay bằng `#d9736a` hoặc bỏ hẳn (dùng theme token / màu trong `theme.ts`). Các file dự kiến còn màu cũ: `CartPage.tsx`, `CheckoutPage.tsx`, `HomePage.tsx`, `ProductsPage.tsx`, `ProductDetailPage.tsx`, `admin/Products.tsx`.

Nên tạo `frontend/src/theme/colors.ts`:

```typescript
export const colors = {
  primary: '#d9736a',
  primarySoft: '#fdf1ee',
  textBase: '#2c2622',
  textSecondary: '#8a807a',
  surface: '#ffffff',
  bgLayout: '#faf7f5',
  border: '#f0e6e1',
};
```

Rồi dùng `colors.primary` thay cho hex rải rác.

## Files cần sửa / tạo

Tạo:
- `frontend/src/theme/theme.ts`
- `frontend/src/theme/index.ts`
- `frontend/src/theme/colors.ts`
- `frontend/src/types/product.ts`
- `frontend/src/hooks/useProducts.ts`
- `frontend/src/components/ProductCard.tsx`
- `frontend/src/components/SiteHeader.tsx`
- `frontend/src/components/SiteFooter.tsx`
- `frontend/src/components/home/HeroSection.tsx`
- `frontend/src/components/home/CategoryStrip.tsx`
- `frontend/src/components/home/FeaturedTabs.tsx`
- `frontend/src/components/home/BrandStrip.tsx`
- `frontend/src/components/home/TrustBanner.tsx`

Sửa:
- `frontend/src/App.tsx` (theme)
- `frontend/index.html` (font)
- `frontend/src/components/MainLayout.tsx`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/ProductsPage.tsx`
- `frontend/src/pages/ProductDetailPage.tsx`
- `frontend/src/utils/constants.ts`
- `frontend/src/pages/user/CartPage.tsx`, `CheckoutPage.tsx` (màu)

Không tạo file `.css` riêng nếu không cần — antd token + CSS variables trong `index.css` là đủ. Nếu tạo CSS thì dùng `frontend/src/index.css` (một file duy nhất).

## Todo

- [x] R1 theme.ts + colors.ts + App.tsx + font
- [x] R2 types/product.ts + hooks/useProducts.ts + components/ProductCard.tsx
- [x] R3 SiteHeader + SiteFooter + MainLayout
- [x] R4 HomePage + 5 component home/
- [x] R5 ProductsPage sidebar filter
- [x] R6 ProductDetailPage gallery + tabs + similar
- [x] R7 dọn `#fa8c16`
- [x] `cd frontend && npx tsc -p tsconfig.app.json --noEmit`
- [x] `cd frontend && npm run build`
- [x] Kiểm tra trực quan: chạy `npm run dev`, xem `/`, `/products`, `/products/1`, `/cart`

## Success criteria

- Trang chủ có hero có ảnh, lưới danh mục, 3 tab sản phẩm, dải thương hiệu, footer nhiều cột.
- `/products` lọc được theo nhiều loại da cùng lúc và kết quả là hợp (OR).
- Trang chi tiết có gallery nhiều ảnh, 3 tab, khối sản phẩm tương tự.
- Header có ô tìm kiếm hoạt động, dẫn tới `/products?search=...`.
- Không còn chuỗi `#fa8c16` trong `frontend/src`.
- Mọi file mới dưới 200 dòng. `npm run build` exit 0.

## Risk

- Đổi theme là thay đổi thị giác toàn trang → cần xem lại từng trang sau khi làm để không mất contrast (chữ trên nền `#d9736a`).
- Thêm `@ant-design/icons` `TikTokOutlined` — nếu version icons không có icon này thì bỏ và dùng icon khác.
