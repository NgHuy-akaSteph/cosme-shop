import { Form, Input } from 'antd';
import { PHONE_PATTERN } from '../../types/checkout';

interface ShippingAddressFieldsProps {
  /** True khi giao cho người khác -> hiện gợi ý nhập tay. */
  isOtherRecipient?: boolean;
}

/**
 * Cac truong thong tin giao hang cua trang thanh toan.
 *
 * Tach rieng de dung chung `form` instance cua trang cha (CheckoutPage).
 * Gia tri co san duoc prefill tu ho so (xem `useShippingAddressPrefill`),
 * nhung nguoi dung van luon co the sua.
 */
export default function ShippingAddressFields({ isOtherRecipient }: ShippingAddressFieldsProps) {
  return (
    <>
      <Form.Item
        name="shipping_name"
        label="Họ và tên"
        rules={[{ required: true, message: 'Vui lòng nhập họ tên!' }]}
        extra={isOtherRecipient ? 'Nhập tên người nhận hàng' : undefined}
      >
        <Input placeholder="Nguyễn Văn A" />
      </Form.Item>

      <Form.Item
        name="shipping_phone"
        label="Số điện thoại"
        rules={[
          { required: true, message: 'Vui lòng nhập số điện thoại!' },
          { pattern: PHONE_PATTERN, message: 'Số điện thoại không hợp lệ!' },
        ]}
        extra={isOtherRecipient ? 'Nhập số điện thoại người nhận' : undefined}
      >
        <Input placeholder="0901234567" />
      </Form.Item>

      <Form.Item
        name="shipping_address"
        label="Địa chỉ"
        rules={[{ required: true, message: 'Vui lòng nhập địa chỉ!' }]}
        extra={isOtherRecipient ? 'Nhập địa chỉ giao hàng của người nhận' : undefined}
      >
        <Input.TextArea
          rows={3}
          placeholder="123 Đường ABC, Quận 1, TP. Hồ Chí Minh"
        />
      </Form.Item>

      <Form.Item name="note" label="Ghi chú (tùy chọn)">
        <Input.TextArea rows={2} placeholder="Giao giờ hành chính" />
      </Form.Item>
    </>
  );
}
