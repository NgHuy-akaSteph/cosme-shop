import { useEffect, useRef } from 'react';
import { useQueries } from '@tanstack/react-query';
import api from '../api/axios';
import { useCartStore, type CartItem } from '../store/cartStore';
import type { Product } from '../types/product';

/** Lấy chi tiết sản phẩm (public endpoint, không cần auth). */
function fetchProduct(productId: number) {
  return api
    .get(`/api/products/${productId}`)
    .then((res) => res.data.data as Product);
}

/**
 * Đồng bộ giá & tồn kho của các dòng giỏ từ server.
 *
 * - Giá: variant price → product price/sale_price (mirror logic server
 *   `order_service.create_order`).
 * - Tồn kho: variant stock → product stock (tổng stock các variant).
 * - KHÔNG thay đổi `qty` (người dùng tự chỉnh).
 * - Sản phẩm không còn tồn tại (404) → giữ nguyên dòng cũ, không chặn các dòng khác.
 */
export function useCartItemsSync(items: CartItem[]) {
  const syncItems = useCartStore((state) => state.syncItems);

  // Snapshot giá trị đã đồng bộ lần trước -> tránh gọi `syncItems` lặp lại
  // (mỗi lần `syncItems` tạo array mới -> `items` đổi tham chiếu -> vòng lặp).
  const syncedRef = useRef<string>('');

  const results = useQueries({
    queries: items.map((item) => ({
      queryKey: ['product', item.product_id],
      queryFn: () => fetchProduct(item.product_id),
      enabled: item.product_id > 0,
    })),
  });

  useEffect(() => {
    if (items.length === 0) {
      syncedRef.current = '';
      return;
    }

    const merged = items.map((item, index) => {
      const product = results[index]?.data;
      // Chưa tải xong hoặc sản phẩm đã bị xoá -> giữ nguyên dữ liệu cũ của dòng này.
      if (!product) return item;

      const variant = item.variant_id
        ? product.variants?.find((v) => v.id === item.variant_id)
        : undefined;

      // Server: có variant -> variant.price ?? product.price (KHÔNG dùng sale_price).
      // Không variant -> sale_price ?? price.
      const price = variant
        ? Number(variant.price ?? product.price)
        : Number(product.sale_price ?? product.price);

      const stock = variant
        ? Number(variant.stock ?? 0)
        : Number(product.stock ?? 0);

      return {
        ...item,
        name: product.name,
        price,
        image_url: product.image_urls?.thumb ?? product.image_url ?? item.image_url,
        stock,
        is_active: product.is_active,
        variant_name: variant?.name ?? item.variant_name,
      };
    });

    // Chỉ ghi khi giá trị thực sự khác lần đồng bộ trước.
    const signature = merged
      .map(
        (m) =>
          `${m.product_id}-${m.variant_id ?? ''}:${m.name}:${m.price}:${m.stock}:${m.is_active}:${m.image_url ?? ''}`,
      )
      .join('|');
    if (signature === syncedRef.current) return;

    syncedRef.current = signature;
    syncItems(merged);
  }, [results, items, syncItems]);
}
