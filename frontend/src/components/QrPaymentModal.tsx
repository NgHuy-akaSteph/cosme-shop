import { Modal, Image, Typography, Space, Button, Alert, Spin } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import api from '../api/axios';

const { Text } = Typography;

export interface PaymentStatus {
  order_code: string;
  payment_status: string;
  paid_at: string | null;
}

interface QrPaymentModalProps {
  visible: boolean;
  qrUrl: string | null;
  orderId?: number;
  onClose: () => void;
  onContinue: () => void;
  onPaid?: () => void;
}

/**
 * Modal QR thanh toan SePay.
 * Tu poll trang thai don hang moi 4s, dung lai khi da thanh toan.
 */
export default function QrPaymentModal({
  visible,
  qrUrl,
  orderId,
  onClose,
  onContinue,
  onPaid,
}: QrPaymentModalProps) {
  const paidNotified = useRef(false);

  const { data: paymentStatus } = useQuery({
    queryKey: ['payment-status', orderId],
    queryFn: async () => {
      const res = await api.get(`/api/payment/status/${orderId}`);
      return res.data.data as PaymentStatus;
    },
    enabled: visible && Boolean(orderId),
    refetchInterval: (query) => {
      const status = query.state.data?.payment_status;
      return status === 'paid' ? false : 4000;
    },
  });

  useEffect(() => {
    if (paymentStatus?.payment_status === 'paid' && !paidNotified.current) {
      paidNotified.current = true;
      onPaid?.();
    }
  }, [paymentStatus, onPaid]);

  const isPaid = paymentStatus?.payment_status === 'paid';

  return (
    <Modal
      title="Thanh toán bằng QR Code"
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="continue" type="primary" onClick={onContinue}>
          {isPaid ? 'Xem đơn hàng' : 'Tôi đã thanh toán'}
        </Button>,
      ]}
      centered
      destroyOnHidden
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {isPaid ? (
          <Alert
            type="success"
            showIcon
            message="Thanh toán thành công!"
            description="Đơn hàng của bạn đã được ghi nhận thanh toán."
          />
        ) : (
          <>
            <Text>Vui lòng quét mã QR bên dưới để thanh toán qua SePay:</Text>
            {qrUrl ? (
              <div style={{ textAlign: 'center' }}>
                <Image src={qrUrl} alt="QR Code" width={250} />
              </div>
            ) : (
              <Alert
                type="warning"
                showIcon
                message="Chưa cấu hình thông tin tài khoản nhận tiền"
                description="Vui lòng liên hệ admin để được hỗ trợ thanh toán."
              />
            )}
            <Text type="secondary" style={{ fontSize: 12 }}>
              Trang này tự động cập nhật, bạn không cần tải lại trang.
            </Text>
            <div style={{ textAlign: 'center' }}>
              <Spin size="small" /> <Text type="secondary">Đang chờ thanh toán...</Text>
            </div>
          </>
        )}
      </Space>
    </Modal>
  );
}
