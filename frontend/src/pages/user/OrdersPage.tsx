import { Card, Table, Typography, Tag, Empty, Button } from 'antd';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ShoppingOutlined, EyeOutlined } from '@ant-design/icons';
import api from '../../api/axios';
import { formatPrice, formatDate, statusColors, statusText } from '../../utils/constants';

const { Title, Text } = Typography;

interface Order {
  id: number;
  order_code: string;
  status: string;
  total: string;
  payment_method: string;
  payment_status: string;
  created_at: string;
}

interface OrderListResponse {
  data: Order[];
  total: number;
  page: number;
  size: number;
}

const PAGE_SIZE = 10;

export default function OrdersPage() {
  const [page, setPage] = useState(1);

  const { data: ordersData, isLoading } = useQuery({
    queryKey: ['orders', page],
    queryFn: async () => {
      const res = await api.get(`/api/orders?page=${page}&size=${PAGE_SIZE}`);
      return res.data as OrderListResponse;
    },
  });

  const orders = ordersData?.data ?? [];

  const columns = [
    {
      title: 'Mã đơn',
      dataIndex: 'order_code',
      render: (code: string) => <Text strong>{code}</Text>,
    },
    {
      title: 'Ngày đặt',
      dataIndex: 'created_at',
      render: (date: string) => formatDate(date),
    },
    {
      title: 'Tổng tiền',
      dataIndex: 'total',
      render: (total: string) => <Text strong>{formatPrice(total)}</Text>,
    },
    {
      title: 'Thanh toán',
      dataIndex: 'payment_method',
      render: (method: string) => method.toUpperCase(),
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      render: (status: string) => (
        <Tag color={statusColors[status] || 'default'}>
          {statusText[status] || status}
        </Tag>
      ),
    },
    {
      title: '',
      render: (_: unknown, record: Order) => (
        <Link to={`/orders/${record.id}`}>
          <Button type="link" icon={<EyeOutlined />}>
            Chi tiết
          </Button>
        </Link>
      ),
    },
  ];

  if (isLoading) {
    return <div>Đang tải...</div>;
  }

  if (orders.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Chưa có đơn hàng nào"
        >
          <Link to="/products">
            <Button type="primary" icon={<ShoppingOutlined />}>
              Mua sắm ngay
            </Button>
          </Link>
        </Empty>
      </div>
    );
  }

  return (
    <div>
      <Title level={2}>Đơn hàng của tôi</Title>

      <Card>
        <Table
          dataSource={orders}
          columns={columns}
          rowKey="id"
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total: ordersData?.total ?? 0,
            showSizeChanger: false,
            onChange: setPage,
          }}
        />
      </Card>
    </div>
  );
}
