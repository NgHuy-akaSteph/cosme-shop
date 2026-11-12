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
import { colors } from '../theme';

const { Header } = Layout;

const NAV_ITEMS = [
  { key: '/', label: 'Trang chủ', to: '/' },
  { key: '/products', label: 'Sản phẩm', to: '/products' },
  { key: '/products?sort=best_seller', label: 'Bán chạy', to: '/products?sort=best_seller' },
  { key: '/faq', label: 'Hỏi đáp', to: '/faq' },
];

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
    logout({ clearCart: true });
    navigate('/');
  };

  const userMenuItems: MenuProps['items'] = isAuthenticated
    ? [
        { key: 'profile', label: <Link to="/profile">Tài khoản</Link> },
        { key: 'orders', label: <Link to="/orders">Đơn hàng</Link> },
        { key: 'wishlist', label: <Link to="/wishlist">Yêu thích</Link> },
        ...(user?.role === 'admin'
          ? [{ key: 'admin', icon: <ShopOutlined />, label: <Link to="/admin">Quản trị</Link> }]
          : []),
        { type: 'divider' },
        {
          key: 'logout',
          icon: <LogoutOutlined />,
          label: 'Đăng xuất',
          onClick: handleLogout,
        },
      ]
    : [];

  return (
    <Header
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 24,
        position: 'sticky',
        top: 0,
        zIndex: 100,
        borderBottom: `1px solid ${colors.border}`,
      }}
    >
      <Link
        to="/"
        style={{ fontSize: 22, fontWeight: 700, color: colors.textBase, whiteSpace: 'nowrap' }}
      >
        Cosme<span style={{ color: colors.primary }}>Shop</span>
      </Link>

      {screens.md ? (
        <nav style={{ display: 'flex', gap: 24 }}>
          {NAV_ITEMS.map((item) => (
            <Link key={item.key} to={item.to} style={{ fontWeight: 500, color: colors.textBase }}>
              {item.label}
            </Link>
          ))}
        </nav>
      ) : (
        <Button
          type="text"
          icon={<MenuOutlined />}
          onClick={() => setDrawerOpen(true)}
          aria-label="Menu"
        />
      )}

      <div style={{ flex: 1, maxWidth: 460, marginLeft: screens.md ? 0 : 'auto' }}>
        <Input
          placeholder="Tìm serum, kem chống nắng..."
          prefix={<SearchOutlined style={{ color: colors.placeholderIcon }} />}
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
            <Avatar
              icon={<UserOutlined />}
              style={{ cursor: 'pointer', background: colors.primarySoft, color: colors.primary }}
            />
          </Dropdown>
        ) : (
          <Link to="/login">
            <Button type="primary">Đăng nhập</Button>
          </Link>
        )}
      </div>

      <Drawer title="Menu" open={drawerOpen} onClose={() => setDrawerOpen(false)}>
        {NAV_ITEMS.map((item) => (
          <div
            key={item.key}
            style={{ padding: '10px 0' }}
            onClick={() => setDrawerOpen(false)}
          >
            <Link to={item.to}>{item.label}</Link>
          </div>
        ))}
      </Drawer>
    </Header>
  );
}
