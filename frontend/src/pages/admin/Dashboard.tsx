import { Card, Row, Col, Statistic, Typography } from 'antd';
import { ShoppingOutlined, ShoppingCartOutlined, UserOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/axios';

const { Title } = Typography;

export default function AdminDashboard() {
  const { data: pendingOrdersData } = useQuery({
    queryKey: ['admin', 'orders', 'pending'],
    queryFn: async () => {
      const res = await api.get('/api/admin/orders?status=pending&size=1');
      return res.data;
    },
  });
  
  const { data: allOrdersData } = useQuery({
    queryKey: ['admin', 'orders', 'all'],
    queryFn: async () => {
      const res = await api.get('/api/admin/orders?size=1');
      return res.data;
    },
  });
  
  const { data: usersData } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: async () => {
      const res = await api.get('/api/admin/users?size=1');
      return res.data;
    },
  });
  
  return (
    <div>
      <Title level={2}>Dashboard</Title>
      
      <Row gutter={16}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Tổng đơn hàng"
              value={allOrdersData?.total || 0}
              prefix={<ShoppingCartOutlined />}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Người dùng"
              value={usersData?.total || 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Đơn chờ xử lý"
              value={pendingOrdersData?.total || 0}
              prefix={<ShoppingOutlined />}
            />
          </Card>
        </Col>
      </Row>
      
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card title="Chào mừng đến trang quản trị">
            <p>Sử dụng menu bên trái để quản lý:</p>
            <ul>
              <li>Sản phẩm - Thêm, sửa, xóa sản phẩm</li>
              <li>Đơn hàng - Xem và cập nhật trạng thái đơn hàng</li>
              <li>Danh mục - Quản lý danh mục sản phẩm</li>
              <li>Thương hiệu - Quản lý thương hiệu</li>
              <li>Người dùng - Quản lý tài khoản người dùng</li>
            </ul>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
