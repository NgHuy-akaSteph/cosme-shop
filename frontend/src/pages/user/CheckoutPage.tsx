import { Form, Button, Card, Typography, App, Row, Col, Checkbox } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useCartStore } from '../../store/cartStore';
import QrPaymentModal from '../../components/QrPaymentModal';
import RecipientSelector from '../../components/checkout/RecipientSelector';
import ShippingAddressFields from '../../components/checkout/ShippingAddressFields';
import OrderSummary from '../../components/checkout/OrderSummary';
import PaymentSection from '../../components/checkout/PaymentSection';
import { useCurrentUser } from '../../hooks/useCurrentUser';
import { useShippingAddressPrefill } from '../../hooks/useShippingAddressPrefill';
import { useCheckoutOrder } from '../../hooks/useCheckoutOrder';
import {
  useSaveShippingToProfile,
  toProfilePayload,
} from '../../hooks/useSaveShippingToProfile';
import type { CheckoutFormValues, RecipientMode } from '../../types/checkout';

const { Title, Text } = Typography;

export default function CheckoutPage() {
  const navigate = useNavigate();
  const { items, getTotal, clearCart } = useCartStore();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [paymentMethod, setPaymentMethod] = useState('cod');
  const [recipientMode, setRecipientMode] = useState<RecipientMode>('self');
  const [saveToProfile, setSaveToProfile] = useState(true);
  const [showQrModal, setShowQrModal] = useState(false);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [orderId, setOrderId] = useState<number | undefined>(undefined);

  // Ma giam gia: server la noi duy nhat tinh tien giam, FE chi hien thi preview.
  const [couponCode, setCouponCode] = useState<string | null>(null);
  const [discountAmount, setDiscountAmount] = useState(0);

  // Ho so nguoi dung - nguon du lieu prefill thong tin giao hang.
  const { data: profile } = useCurrentUser();
  const { markDirty } = useShippingAddressPrefill({
    form,
    profile,
    mode: recipientMode,
  });
  const saveProfileMutation = useSaveShippingToProfile();

  const subtotal = getTotal();
  const total = subtotal - discountAmount;

  /** Luu thong tin giao hang vao ho so (chi khi giao cho chinh minh). */
  const persistShippingToProfile = (values: CheckoutFormValues) => {
    if (recipientMode !== 'self' || !saveToProfile) return;
    const payload = toProfilePayload(values);
    if (payload) {
      saveProfileMutation.mutate(payload);
    }
  };

  const checkoutMutation = useCheckoutOrder({
    items,
    paymentMethod,
    couponCode,
    onSuccess: (values) => {
      // Luu thong tin giao hang da sua vao ho so (best-effort, khong block don).
      persistShippingToProfile(values);
    },
  });

  const handleCheckoutSuccess = (data: { data?: { order?: { id: number }; qr_url?: string | null } }) => {
    const createdOrderId = data.data?.order?.id;
    const createdQrUrl = data.data?.qr_url ?? null;

    // COD: thanh toan khi nhan hang -> xoa gio ngay
    if (paymentMethod === 'cod') {
      clearCart();
      message.success('Đặt hàng thành công!');
      navigate(createdOrderId ? `/orders/${createdOrderId}` : '/orders');
      return;
    }

    // SePay: giu gio cho den khi xac nhanh thanh toan
    setQrUrl(createdQrUrl);
    setOrderId(createdOrderId);
    setShowQrModal(true);
  };

  const onFinish = (values: CheckoutFormValues) => {
    checkoutMutation.mutate(values, {
      onSuccess: handleCheckoutSuccess,
    });
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
            <Form
              form={form}
              layout="vertical"
              onFinish={onFinish}
              onValuesChange={markDirty}
            >
              <RecipientSelector value={recipientMode} onChange={setRecipientMode} />

              <ShippingAddressFields isOtherRecipient={recipientMode === 'other'} />

              {recipientMode === 'self' && (
                <Form.Item style={{ marginBottom: 16 }}>
                  <Checkbox
                    checked={saveToProfile}
                    onChange={(e) => setSaveToProfile(e.target.checked)}
                  >
                    Lưu thông tin này vào hồ sơ để lần sau điền nhanh hơn
                  </Checkbox>
                </Form.Item>
              )}

              <PaymentSection
                paymentMethod={paymentMethod}
                onPaymentMethodChange={setPaymentMethod}
                subtotal={subtotal}
                appliedCoupon={couponCode}
                discountAmount={discountAmount}
                onCouponChange={(code, amount) => {
                  setCouponCode(code);
                  setDiscountAmount(amount);
                }}
              />

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
          <OrderSummary
            items={items}
            subtotal={subtotal}
            appliedCoupon={couponCode}
            discountAmount={discountAmount}
            total={total}
          />
        </Col>
      </Row>

      <QrPaymentModal
        visible={showQrModal}
        qrUrl={qrUrl}
        orderId={orderId}
        onClose={() => {
          setShowQrModal(false);
          if (orderId) navigate(`/orders/${orderId}`);
        }}
        onPaid={() => {
          clearCart();
          message.success('Thanh toán thành công!');
        }}
        onContinue={() => {
          setShowQrModal(false);
          if (orderId) navigate(`/orders/${orderId}`);
          else navigate('/orders');
        }}
      />
    </div>
  );
}
