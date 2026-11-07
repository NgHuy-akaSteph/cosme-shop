import { useMutation, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';
import api from '../api/axios';
import { currentUserKey } from './useCurrentUser';
import type { CheckoutFormValues } from '../types/checkout';

/**
 * Payload luu thong tin giao hang vao ho so nguoi dung.
 *
 * Chi gui truong co gia tri - backend dung `exclude_unset=True` nen truong
 * khong gui se khong bi ghi de (tranh xoa nham thong tin da co).
 */
export interface ProfileShippingPayload {
  full_name?: string;
  phone?: string;
  address?: string;
}

/**
 * Luu thong tin giao hang da sua vao ho so nguoi dung.
 *
 * Chi dung khi giao cho chinh minh ("Giao cho tôi") - don "giao cho nguoi khac"
 * thi khong duoc ghi de thong tin ho so.
 */
export function useSaveShippingToProfile() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (values: ProfileShippingPayload) => {
      const res = await api.patch('/api/auth/me', values);
      return res.data;
    },
    onSuccess: () => {
      // Lam moi du lieu nguoi dung de trang Tai khoan va trang Thanh toan
      // khong hien thi thong tin cu.
      queryClient.invalidateQueries({ queryKey: currentUserKey });
    },
    onError: () => {
      // Don hang da tao thanh cong => khong block nguoi dung bang loi luu ho so.
      message.warning(
        'Không lưu được thông tin vào hồ sơ. Bạn vẫn có thể sửa ở trang Tài khoản.',
      );
    },
  });
}

/**
 * Gom gia tri form thanh toan thanh payload luu ho so.
 *
 * Truong rong bi bo qua (khong ghi de gia tri cu cua ho so).
 * Tra `null` khi khong co gi tri nao de luu.
 */
export function toProfilePayload(
  values: CheckoutFormValues,
): ProfileShippingPayload | null {
  const fullName = values.shipping_name?.trim();
  const phone = values.shipping_phone?.trim();
  const address = values.shipping_address?.trim();

  const payload: ProfileShippingPayload = {};
  if (fullName) payload.full_name = fullName;
  if (phone) payload.phone = phone;
  if (address) payload.address = address;

  return Object.keys(payload).length > 0 ? payload : null;
}
