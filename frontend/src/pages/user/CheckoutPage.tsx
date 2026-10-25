import { useMutation } from '@tanstack/react-query';
import { Form, Input, Button, Card, Typography, Radio, message, Row, Col } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useCartStore } from '../../store/cartStore';
import api from '../../api/axios';
import { useState } from 'react';
import { formatPrice, SHIPPING_FEE, SHIPPING_FREE_THRESHOLD } from '../../utils/constants';
import QrPaymentModal from '../../components/QrPaymentModal';

const { Title, Text } = Typography;

export default function CheckoutPage() {
  const navigate = useNavigate();
  const { items, getTotal, clearCart } = useCartStore();
  const [form] = Form.useForm();
  const [paymentMethod, setPaymentMethod] = useState('cod');
  const [showQrModal, setShowQrModal] = useState(false);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  
  const subtotal = getTotal();
  const shippingFee = subtotal >= SHIPPING_FREE_THRESHOLD ? 0 : SHIPPING_FEE;
  const total = subtotal + shippingFee;
  
  const checkoutMutation = useMutation({
    mutationFn: async (values: any) => {
      const orderItems = items.map((item) => ({
        product_id: item.product_id,
        variant_id: item.variant_id,
        qty: item.qty,
      }));
      
      const res = await api.post('/api/orders', {
        items: orderItems,
        shipping_name: values.shipping_name,
        shipping_phone: values.shipping_phone,
        shipping_address: values.shipping_address,
        payment_method: paymentMethod,
        note: values.note,
      });
      
      return res.data;
    },
    onSuccess: (data) => {
      clearCart();
      message.success('Đặt hàng thành công!');

      // Show QR modal for SePay
      if (paymentMethod === 'sepay' && data.data?.qr_url) {
        setQrUrl(data.data.qr_url);
        setShowQrModal(true);
      } else {
        navigate('/orders');
      }
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Đặt hàng thất bại');
    },
  });
  
  const onFinish = (values: any) => {
    checkoutMutation.mutate(values);
  };
  
  if (items.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <Text>Giỏ hàng trống</Text>
      </div>
    );
  }
  
  return (
    <div>
      <Title level={2}>Thanh toán</Title>
      
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card title="Thông tin giao hàng">
            <Form form={form} layout="vertical" onFinish={onFinish}>
              <Form.Item
                name="shipping_name"
                label="Họ và tên"
                rules={[{ required: true, message: 'Vui lòng nhập họ tên!' }]}
              >
                <Input placeholder="Nguyễn Văn A" />
              </Form.Item>
              
              <Form.Item
                name="shipping_phone"
                label="Số điện thoại"
                rules={[
                  { required: true, message: 'Vui lòng nhập số điện thoại!' },
                  { pattern: /^[0-9]{10,11}$/, message: 'Số điện thoại không hợp lệ!' },
                ]}
              >
                <Input placeholder="0901234567" />
              </Form.Item>
              
              <Form.Item
                name="shipping_address"
                label="Địa chỉ"
                rules={[{ required: true, message: 'Vui lòng nhập địa chỉ!' }]}
              >
                <Input.TextArea rows={3} placeholder="123 Đường ABC, Quận 1, TP. Hồ Chí Minh" />
              </Form.Item>
              
              <Form.Item name="note" label="Ghi chú (tùy chọn)">
                <Input.TextArea rows={2} placeholder="Giao giờ hành chính" />
              </Form.Item>
              
              <Title level={5}>Phương thức thanh toán</Title>
              
              <Radio.Group
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                style={{ marginBottom: 24 }}
              >
                <Radio value="cod">
                  <Text>Thanh toán khi nhận hàng (COD)</Text>
                </Radio>
                <br />
                <Radio value="sepay">
                  <Text>Thanh toán qua SePay (Chuyển khoản ngân hàng)</Text>
                </Radio>
              </Radio.Group>
              
              <Button
                type="primary"
                size="large"
                htmlType="submit"
                block
                loading={checkoutMutation.isPending}
              >
                Đặt hàng
              </Button>
            </Form>
          </Card>
        </Col>
        
        <Col xs={24} lg={8}>
          <Card>
          <Title level={4}>Đơn hàng của bạn</Title>
          
          <div style={{ marginBottom: 16 }}>
            {items.map((item) => (
              <div
                key={`${item.product_id}-${item.variant_id}`}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: 8,
                }}
              >
                <Text>
                  {item.name}
                  {item.variant_name && ` (${item.variant_name})`}
                  <Text type="secondary"> x{item.qty}</Text>
                </Text>
                <Text>{formatPrice(item.price * item.qty)}</Text>
              </div>
            ))}
          </div>
          
          <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <Text>Tạm tính:</Text>
              <Text>{formatPrice(subtotal)}</Text>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <Text>Phí vận chuyển:</Text>
              <Text>{shippingFee === 0 ? 'Miễn phí' : formatPrice(shippingFee)}</Text>
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              paddingTop: 8,
              borderTop: '1px solid #f0f0f0',
            }}>
              <Text strong>Tổng:</Text>
              <Text strong style={{ fontSize: 18, color: '#fa8c16' }}>
                {formatPrice(total)}
              </Text>
            </div>
            </div>
          </Card>
        </Col>
      </Row>
      
      <QrPaymentModal
        visible={showQrModal}
        qrUrl={qrUrl}
        onClose={() => setShowQrModal(false)}
        onContinue={() => {
          setShowQrModal(false);
          navigate('/orders');
        }}
      />
    </div>
  );
}
