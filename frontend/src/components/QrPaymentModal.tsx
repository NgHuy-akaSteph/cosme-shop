import { Modal, Image, Typography, Space, Button } from 'antd';

const { Text } = Typography;

interface QrPaymentModalProps {
  visible: boolean;
  qrUrl: string | null;
  onClose: () => void;
  onContinue: () => void;
}

export default function QrPaymentModal({ visible, qrUrl, onClose, onContinue }: QrPaymentModalProps) {
  return (
    <Modal
      title="Thanh toán bằng QR Code"
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="continue" type="primary" onClick={onContinue}>
          Tiếp tục
        </Button>,
      ]}
      centered
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Text>Vui lòng quét mã QR bên dưới để thanh toán qua SePay:</Text>
        {qrUrl && (
          <div style={{ textAlign: 'center' }}>
            <Image src={qrUrl} alt="QR Code" width={250} />
          </div>
        )}
        <Text type="secondary" style={{ fontSize: 12 }}>
          Sau khi thanh toán, bạn sẽ được chuyển đến danh sách đơn hàng.
        </Text>
      </Space>
    </Modal>
  );
}
