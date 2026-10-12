import { Outlet, Link, useNavigate } from 'react-router-dom';
import { Layout, Menu, Badge, Button, Dropdown, Avatar } from 'antd';
import type { MenuProps } from 'antd';
import {
  ShoppingCartOutlined,
  UserOutlined,
  LogoutOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../store/authStore';
import { useCartStore } from '../store/cartStore';

const { Header, Content, Footer } = Layout;

type MenuItem = NonNullable<MenuProps['items']>[number];

export default function MainLayout() {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuthStore();
  const cartCount = useCartStore((state) => state.getItemCount());

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const adminMenuItem: MenuItem = {
    key: 'admin',
    icon: <ShopOutlined />,
    label: <Link to="/admin">Quản trị</Link>,
  };

  const userMenuItems: MenuProps['items'] = isAuthenticated
    ? [
        {
          key: 'profile',
          label: <Link to="/profile">Tài khoản</Link>,
        },
        {
          key: 'orders',
          label: <Link to="/orders">Đơn hàng</Link>,
        },
        {
          key: 'wishlist',
          label: <Link to="/wishlist">Yêu thích</Link>,
        },
        ...(user?.role === 'admin' ? [adminMenuItem] : []),
        {
          type: 'divider',
        },
        {
          key: 'logout',
          label: 'Đăng xuất',
          icon: <LogoutOutlined />,
          onClick: handleLogout,
        },
      ]
    : [];

  return (
    <Layout className="layout" style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <div className="logo" style={{ color: 'white', fontSize: 20, fontWeight: 'bold' }}>
          <Link to="/" style={{ color: 'white' }}>Cosme Shop</Link>
        </div>

        <Menu
          theme="dark"
          mode="horizontal"
          defaultSelectedKeys={['home']}
          items={[
            { key: 'home', label: <Link to="/">Trang chủ</Link> },
            { key: 'products', label: <Link to="/products">Sản phẩm</Link> },
          ]}
          style={{ flex: 1 }}
        />

        <Link to="/cart">
          <Badge count={cartCount} size="small">
            <Button type="text" icon={<ShoppingCartOutlined />} size="large" style={{ color: 'white' }} />
          </Badge>
        </Link>

        {isAuthenticated ? (
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Avatar icon={<UserOutlined />} style={{ cursor: 'pointer' }} />
          </Dropdown>
        ) : (
          <Link to="/login">
            <Button type="primary">Đăng nhập</Button>
          </Link>
        )}
      </Header>
      
      <Content style={{ padding: '0 50px', minHeight: 'calc(100vh - 134px)' }}>
        <div style={{ padding: '24px 0', minHeight: '100%' }}>
          <Outlet />
        </div>
      </Content>
      
      <Footer style={{ textAlign: 'center' }}>
        Cosme Shop ©{new Date().getFullYear()} - Mỹ phẩm chính hãng
      </Footer>
    </Layout>
  );
}
