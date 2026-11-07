import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Tag, Timeline, Table, Spin, Button, Descriptions, App, Popconfirm, Row, Col } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeftOutlined, QrcodeOutlined } from '@ant-design/icons';
import { useState } from 'react';
import api from '../../api/axios';
import { formatPrice, formatDate, statusColors, statusText } from '../../utils/constants';
import type { ApiError } from '../../types/api';
import { getErrorMessage } from '../../types/api';
import QrPaymentModal from '../../components/QrPaymentModal';

const { Title, Text } = Typography;

interface OrderItem {
  id: number;
  product_name: string;
  product_price: string;
  qty: number;
  subtotal: string;
  variant_info: {
    id?: string;
    name?: string;
  } | null;
}

interface StatusHistory {
  status: string;
  note: string | null;
  created_at: string;
}

interface Order {
  id: number;
  order_code: string;
  status: string;
  total: string;
  subtotal: string;
  shipping_fee: string;
  payment_method: string;
  payment_status: string;
  paid_at: string | null;
  shipping_name: string;
  shipping_phone: string;
  shipping_address: string;
  tracking_code: string | null;
  created_at: string;
  qr_url?: string | null;
  items: OrderItem[];
  status_history: StatusHistory[];
}

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [showQr, setShowQr] = useState(false);
  
  const { data: order, isLoading } = useQuery({
    queryKey: ['order', id],
    queryFn: async () => {
      const res = await api.get(`/api/orders/${id}`);
      return res.data.data as Order;
    },
  });
  
  const cancelMutation = useMutation({
    mutationFn: async () => {
      if (!id) return;
      await api.post(`/api/orders/${id}/cancel`);
    },
    onSuccess: () => {
      message.success('Đơn hàng đã được hủy');
      queryClient.invalidateQueries({ queryKey: ['order', id] });
    },
    onError: (error: ApiError) => {
      message.error(getErrorMessage(error, 'Không thể hủy đơn hàng'));
    },
  });
  
  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>;
  }
  
  if (!order) {
    return <Text>Không tìm thấy đơn hàng</Text>;
  }
  
  const itemColumns = [
    { title: 'Sản phẩm', dataIndex: 'product_name' },
    {
      title: 'Phân loại',
      dataIndex: 'variant_info',
      render: (v: OrderItem['variant_info']) => v?.name ?? '-',
    },
    { title: 'Giá', dataIndex: 'product_price', render: (p: string) => formatPrice(p) },
    { title: 'SL', dataIndex: 'qty', width: 60 },
    { title: 'Tổng', dataIndex: 'subtotal', render: (s: string) => formatPrice(s) },
  ];
  
  return (
    <div>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/orders')}
        style={{ marginBottom: 16, padding: 0 }}
      >
        Quay lại danh sách đơn hàng
      </Button>
      
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card
            title={`Đơn hàng ${order.order_code}`}
            extra={
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Tag color={statusColors[order.status]}>{statusText[order.status]}</Tag>
                {(order.status === 'pending' || order.status === 'confirmed') && (
                  <Popconfirm
                    title="Bạn có chắc muốn hủy đơn hàng này?"
                    onConfirm={() => cancelMutation.mutate()}
                    okText="Hủy đơn"
                    cancelText="Không"
                  >
                    <Button size="small" danger loading={cancelMutation.isPending}>
                      Hủy đơn
                    </Button>
                  </Popconfirm>
                )}
              </div>
            }
          >
            <Descriptions column={2}>
              <Descriptions.Item label="Ngày đặt">{formatDate(order.created_at)}</Descriptions.Item>
              <Descriptions.Item label="Phương thức">{order.payment_method.toUpperCase()}</Descriptions.Item>
              <Descriptions.Item label="Thanh toán">
                <Tag color={order.payment_status === 'paid' ? 'green' : 'orange'}>
                  {order.payment_status === 'paid' ? 'Đã thanh toán' : 'Chưa thanh toán'}
                </Tag>
              </Descriptions.Item>
              {order.tracking_code && (
                <Descriptions.Item label="Mã vận đơn">{order.tracking_code}</Descriptions.Item>
              )}
            </Descriptions>

            {order.payment_method === 'sepay' &&
              order.payment_status !== 'paid' &&
              order.status !== 'cancelled' && (
                <Button
                  type="primary"
                  icon={<QrcodeOutlined />}
                  style={{ marginTop: 16 }}
                  onClick={() => setShowQr(true)}
                >
                  Quét mã QR để thanh toán
                </Button>
              )}
            
            <Title level={5} style={{ marginTop: 24 }}>Sản phẩm</Title>
            <Table
              dataSource={order.items}
              columns={itemColumns}
              rowKey="id"
              pagination={false}
              size="small"
            />
            
            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <div><Text>Tạm tính: {formatPrice(order.subtotal)}</Text></div>
              <div><Text>Phí vận chuyển: {formatPrice(order.shipping_fee)}</Text></div>
              <div style={{ marginTop: 8 }}>
                <Text strong style={{ fontSize: 16 }}>Tổng cộng: {formatPrice(order.total)}</Text>
              </div>
            </div>
          </Card>
          
          <Card title="Địa chỉ giao hàng" style={{ marginTop: 16 }}>
            <Descriptions column={1}>
              <Descriptions.Item label="Người nhận">{order.shipping_name}</Descriptions.Item>
              <Descriptions.Item label="SĐT">{order.shipping_phone}</Descriptions.Item>
              <Descriptions.Item label="Địa chỉ">{order.shipping_address}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        
        <Col xs={24} lg={8}>
          <Card title="Timeline">
          <Timeline
            items={order.status_history
              .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
              .map((h) => ({
                color: statusColors[h.status] || 'blue',
                children: (
                  <div>
                    <Text strong>{statusText[h.status]}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {formatDate(h.created_at)}
                    </Text>
                    {h.note && <div><Text>{h.note}</Text></div>}
                  </div>
                ),
              }))}
          />
        </Card>
        </Col>
      </Row>

      <QrPaymentModal
        visible={showQr}
        qrUrl={order.qr_url ?? null}
        orderId={order.id}
        onClose={() => setShowQr(false)}
        onPaid={() => {
          message.success('Thanh toán thành công!');
          queryClient.invalidateQueries({ queryKey: ['order', id] });
        }}
        onContinue={() => setShowQr(false)}
      />
    </div>
  );
}
