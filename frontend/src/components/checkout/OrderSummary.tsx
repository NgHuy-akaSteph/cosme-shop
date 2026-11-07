import { Card, Typography } from 'antd';
import { formatPrice } from '../../utils/constants';
import { colors } from '../../theme';
import type { CartItem } from '../../store/cartStore';

const { Title, Text } = Typography;

interface OrderSummaryProps {
  items: CartItem[];
  subtotal: number;
  /** Ma giam gia da ap dung (null = chua ap dung). */
  appliedCoupon: string | null;
  /** So tien giam server da xac nhan. */
  discountAmount: number;
  total: number;
}

/** Tom tat don hang + tien tong ben phai trang thanh toan. */
export default function OrderSummary({
  items,
  subtotal,
  appliedCoupon,
  discountAmount,
  total,
}: OrderSummaryProps) {
  return (
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

      <div style={{ borderTop: `1px solid ${colors.dividerDefault}`, paddingTop: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <Text>Tạm tính:</Text>
          <Text>{formatPrice(subtotal)}</Text>
        </div>
        {discountAmount > 0 && (
          <div
            style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}
          >
            <Text type="danger">
              Giảm giá{appliedCoupon ? ` (${appliedCoupon})` : ''}:
            </Text>
            <Text type="danger">-{formatPrice(discountAmount)}</Text>
          </div>
        )}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            paddingTop: 8,
            borderTop: `1px solid ${colors.dividerDefault}`,
          }}
        >
          <Text strong>Tổng:</Text>
          <Text strong style={{ fontSize: 18, color: colors.primary }}>
            {formatPrice(total)}
          </Text>
        </div>
      </div>
    </Card>
  );
}
