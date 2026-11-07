import { Card, Table, Button, Empty, Typography, InputNumber, Popconfirm, Row, Col } from 'antd';
import { DeleteOutlined, ShoppingOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useCartStore, type CartItem } from '../../store/cartStore';
import { formatPrice } from '../../utils/constants';
import { colors } from '../../theme';

const { Title, Text } = Typography;

export default function CartPage() {
  const navigate = useNavigate();
  const { items, updateQty, removeItem, getTotal } = useCartStore();

  const columns = [
    {
      title: 'Sản phẩm',
      dataIndex: 'name',
      render: (_: unknown, record: CartItem) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {record.image_url && (
            <img
              src={record.image_url}
              alt={record.name}
              style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 4 }}
            />
          )}
          <div>
            <Text strong>{record.name}</Text>
            {record.variant_name && (
              <Text type="secondary" style={{ display: 'block' }}>
                {record.variant_name}
              </Text>
            )}
          </div>
        </div>
      ),
    },
    {
      title: 'Giá',
      dataIndex: 'price',
      render: (price: number) => formatPrice(price),
    },
    {
      title: 'Số lượng',
      dataIndex: 'qty',
      render: (_: unknown, record: CartItem) => (
        <InputNumber
          min={1}
          value={record.qty}
          onChange={(value) => updateQty(record.product_id, record.variant_id, value || 1)}
        />
      ),
    },
    {
      title: 'Thành tiền',
      render: (_: unknown, record: CartItem) => formatPrice(record.price * record.qty),
    },
    {
      title: '',
      render: (_: unknown, record: CartItem) => (
        <Popconfirm
          title="Xóa sản phẩm?"
          onConfirm={() => removeItem(record.product_id, record.variant_id)}
          okText="Xóa"
          cancelText="Hủy"
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];
  
  if (items.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Giỏ hàng trống"
        >
          <Link to="/products">
            <Button type="primary" icon={<ShoppingOutlined />}>
              Tiếp tục mua sắm
            </Button>
          </Link>
        </Empty>
      </div>
    );
  }
  
  const total = getTotal();
  
  return (
    <div>
      <Title level={2}>Giỏ hàng</Title>
      
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card>
            <Table
              dataSource={items}
              columns={columns}
              rowKey={(record) => `${record.product_id}-${record.variant_id}`}
              pagination={false}
              scroll={{ x: 600 }}
            />
          </Card>
        </Col>
        
        <Col xs={24} lg={8}>
          <Card>
            <Title level={4}>Tổng cộng</Title>
            
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '16px 0',
              borderTop: `1px solid ${colors.dividerDefault}`,
              marginBottom: 16,
            }}>
              <Text strong>Tổng:</Text>
              <Text strong style={{ fontSize: 18, color: colors.primary }}>
                {formatPrice(total)}
              </Text>
            </div>
            
            <Button
              type="primary"
              size="large"
              block
              onClick={() => navigate('/checkout')}
            >
              Tiến hành đặt hàng
            </Button>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
