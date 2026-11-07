import { Outlet, Link, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  ShoppingOutlined,
  ShoppingCartOutlined,
  FolderOutlined,
  TeamOutlined,
  LogoutOutlined,
  ShopOutlined,
  TagOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { colors } from '../theme';

const { Sider, Content } = Layout;

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const menuItems: MenuProps['items'] = [
    {
      key: '/admin/dashboard',
      icon: <DashboardOutlined />,
      label: <Link to="/admin/dashboard">Dashboard</Link>,
    },
    {
      key: '/admin/products',
      icon: <ShoppingOutlined />,
      label: <Link to="/admin/products">Sản phẩm</Link>,
    },
    {
      key: '/admin/orders',
      icon: <ShoppingCartOutlined />,
      label: <Link to="/admin/orders">Đơn hàng</Link>,
    },
    {
      key: '/admin/categories',
      icon: <FolderOutlined />,
      label: <Link to="/admin/categories">Danh mục</Link>,
    },
    {
      key: '/admin/brands',
      icon: <ShopOutlined />,
      label: <Link to="/admin/brands">Thương hiệu</Link>,
    },
    {
      key: '/admin/coupons',
      icon: <TagOutlined />,
      label: <Link to="/admin/coupons">Mã giảm giá</Link>,
    },
    {
      key: '/admin/users',
      icon: <TeamOutlined />,
      label: <Link to="/admin/users">Người dùng</Link>,
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Đăng xuất',
      onClick: handleLogout,
    },
  ];
  
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={250} theme="dark" style={{ position: 'fixed', left: 0, top: 0, bottom: 0 }}>
        <div style={{ padding: '16px', color: 'white', textAlign: 'center' }}>
          <h2>Cosme Admin</h2>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
        />
      </Sider>
      
      <Layout style={{ marginLeft: 250 }}>
        <Content
          style={{
            padding: '24px',
            minHeight: '100vh',
            background: colors.surfaceMuted,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
