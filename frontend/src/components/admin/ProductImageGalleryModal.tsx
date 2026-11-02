import { Modal, Typography } from 'antd';
import ProductImageManager from './ProductImageManager';

const { Text } = Typography;

export interface ProductImageGalleryModalProps {
  open: boolean;
  productId: number | null;
  productName?: string;
  onClose: () => void;
}

/**
 * Modal "Quan ly anh" - mo tu nut tren bang san pham.
 * Dung chung component ProductImageManager voi form Them/Sua san pham.
 */
export default function ProductImageGalleryModal({
  open,
  productId,
  productName,
  onClose,
}: ProductImageGalleryModalProps) {
  return (
    <Modal
      title="Quản lý ảnh sản phẩm"
      open={open}
      onCancel={onClose}
      footer={null}
      width={820}
      destroyOnClose
    >
      {productName && (
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          {productName}
        </Text>
      )}
      {productId && <ProductImageManager productId={productId} />}
    </Modal>
  );
}
