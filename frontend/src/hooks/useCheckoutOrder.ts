import { useMutation } from '@tanstack/react-query';
import { App } from 'antd';
import api from '../api/axios';
import type { ApiError } from '../types/api';
import { getErrorMessage } from '../types/api';
import type { CartItem } from '../store/cartStore';
import type { CheckoutFormValues } from '../types/checkout';

/** Response cua `POST /api/orders`. */
export interface CheckoutResponse {
  data?: {
    order?: { id: number };
    qr_url?: string | null;
  };
}

interface UseCheckoutOrderParams {
  items: CartItem[];
  paymentMethod: string;
  /** Ma giam gia da ap dung (null = chua ap dung). */
  couponCode: string | null;
  /** Callback chay sau khi don tao thanh cong (dung de luu ho so). */
  onSuccess?: (values: CheckoutFormValues) => void;
}

/**
 * Tao don hang (mutation `POST /api/orders`).
 *
 * Server la noi duy nhat tinh tien giam - client chi gui `coupon_code`.
 */
export function useCheckoutOrder({
  items,
  paymentMethod,
  couponCode,
  onSuccess,
}: UseCheckoutOrderParams) {
  const { message } = App.useApp();

  return useMutation({
    mutationFn: async (values: CheckoutFormValues) => {
      const orderItems = items.map((item) => ({
        product_id: item.product_id,
        variant_id: item.variant_id,
        qty: item.qty,
      }));

      const res = await api.post<CheckoutResponse>('/api/orders', {
        items: orderItems,
        shipping_name: values.shipping_name,
        shipping_phone: values.shipping_phone,
        shipping_address: values.shipping_address,
        payment_method: paymentMethod,
        note: values.note,
        coupon_code: couponCode,
      });

      return res.data;
    },
    onSuccess: (data, values) => {
      onSuccess?.(values);
      return data;
    },
    onError: (error: ApiError) => {
      message.error(getErrorMessage(error, 'Đặt hàng thất bại'));
    },
  });
}
