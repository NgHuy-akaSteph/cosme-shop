import { Radio, Typography } from 'antd';
import CouponInput from '../CouponInput';

const { Title, Text } = Typography;

interface PaymentSectionProps {
  /** Phương thức thanh toán hiện tại. */
  paymentMethod: string;
  onPaymentMethodChange: (method: string) => void;
  /** Tổng tiền hàng (chưa giảm) - server tính lại khi đặt hàng. */
  subtotal: number;
  /** Mã giảm giá đã áp dụng (null = chưa áp dụng). */
  appliedCoupon: string | null;
  /** Số tiền giảm server đã xác nhận. */
  discountAmount: number;
  onCouponChange: (code: string | null, discountAmount: number) => void;
}

/** Khu vực mã giảm giá + phương thức thanh toán. */
export default function PaymentSection({
  paymentMethod,
  onPaymentMethodChange,
  subtotal,
  appliedCoupon,
  discountAmount,
  onCouponChange,
}: PaymentSectionProps) {
  return (
    <>
      <Title level={5}>Mã giảm giá</Title>
      <div style={{ marginBottom: 24 }}>
        <CouponInput
          subtotal={subtotal}
          appliedCode={appliedCoupon}
          discountAmount={discountAmount}
          onChange={onCouponChange}
        />
      </div>

      <Title level={5}>Phương thức thanh toán</Title>

      <Radio.Group
        value={paymentMethod}
        onChange={(e) => onPaymentMethodChange(e.target.value)}
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
    </>
  );
}
