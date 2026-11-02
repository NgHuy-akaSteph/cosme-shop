import { Card, Row, Col, Statistic, Typography, Table, Tag, List } from 'antd';
import {
  ShoppingCartOutlined,
  UserOutlined,
  ShoppingOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/axios';
import { formatPrice } from '../../utils/constants';
import { colors } from '../../theme';

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
    {
      title: 'Doanh thu đã thu',
      value: formatPrice(data?.total_revenue ?? 0),
      icon: <DollarOutlined />,
      color: colors.success,
    },
    {
      title: 'Chờ thu (COD chưa giao)',
      value: formatPrice(data?.pending_revenue ?? 0),
      icon: <ShoppingCartOutlined />,
      color: colors.warning,
    },
    {
      title: 'Tổng đơn hàng',
      value: data?.total_orders ?? 0,
      icon: <ShoppingOutlined />,
      color: colors.primary,
    },
    {
      title: 'Người dùng',
      value: data?.total_users ?? 0,
      icon: <UserOutlined />,
      color: colors.info,
    },
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
                {
                  title: 'Doanh thu',
                  dataIndex: 'revenue',
                  width: 140,
                  render: (v: string) => formatPrice(v),
                },
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
