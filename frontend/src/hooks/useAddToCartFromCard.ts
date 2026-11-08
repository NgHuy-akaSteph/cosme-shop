import { useNavigate } from 'react-router-dom';
import { App } from 'antd';
import { useCartStore } from '../store/cartStore';
import type { Product } from '../types/product';

/**
 * Thêm sản phẩm vào giỏ hàng từ card (trang danh sách / trang chủ / sản phẩm tương tự).
 *
 * - Sản phẩm có phân loại: phải chọn variant ở trang chi tiết (backend cũng chặn
 *   khi tạo đơn mà thiếu `variant_id` — xem `order_service.create_order`).
 * - Giá lấy theo cùng logic với trang chi tiết và server.
 */
export function useAddToCartFromCard() {
  const { addItem } = useCartStore();
  const { message } = App.useApp();
  const navigate = useNavigate();

  return (product: Product) => {
    if (product.variants && product.variants.length > 0) {
      message.info('Vui lòng chọn phân loại ở trang chi tiết sản phẩm');
      navigate(`/products/${product.id}`);
      return;
    }

    const price = Number(product.sale_price ?? product.price);
    addItem(
      {
        product_id: product.id,
        variant_id: undefined,
        name: product.name,
        price,
        image_url: product.image_urls?.thumb ?? product.image_url ?? undefined,
      },
      1,
    );
    message.success('Đã thêm vào giỏ hàng');
  };
}
