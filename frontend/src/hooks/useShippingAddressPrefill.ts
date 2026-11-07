import { useCallback, useEffect, useRef } from 'react';
import type { FormInstance } from 'antd';
import type { RecipientMode } from '../types/checkout';
import { isValidPhone } from '../types/checkout';
import type { User } from '../store/authStore';

interface UseShippingAddressPrefillParams {
  /** Form instance cua trang thanh toan. */
  form: FormInstance;
  /** Ho so nguoi dung (nguon du lieu prefill). */
  profile: User | undefined;
  /** Che do nhan hang hien tai. */
  mode: RecipientMode;
}

/**
 * Tu dong dien thong tin giao hang tu ho so nguoi dung.
 *
 * - `mode = 'self'`  -> dien `full_name` / `phone` / `address` tu ho so.
 * - `mode = 'other'` -> xoa sach 3 truong, nguoi dung phai nhap tay.
 *
 * Luon co the sua: prefill chi gan gia tri, khong khoa form.
 *
 * `dirtyRef` danh dau nguoi dung da go tay. No chan ghi de trong 2 truong hop:
 * 1. Ho so ve muon (request `/api/auth/me` tra ve sau khi user bat dau nhap).
 * 2. Nguoi dung dang sua thong tin trong form.
 */
export function useShippingAddressPrefill({
  form,
  profile,
  mode,
}: UseShippingAddressPrefillParams) {
  const dirtyRef = useRef(false);
  const lastModeRef = useRef<RecipientMode | null>(null);
  const lastSignatureRef = useRef<string | null>(null);
  // `setFieldsValue` cung kich hoat `onValuesChange` -> can co co de phan biet
  // "thay doi do chinh ta gan" voi "nguoi dung go tay".
  const programmaticRef = useRef(false);

  // Chi dua "chu ky" ho so vao so sanh - dung reference object se sai khi
  // React Query tra ve object moi cung du lieu.
  const signature = profile
    ? `${profile.full_name ?? ''}|${profile.phone ?? ''}|${profile.address ?? ''}`
    : null;

  /** Gan gia tri form ma KHONG danh dau la nguoi dung da sua. */
  const setFieldsSilently = useCallback(
    (values: {
      shipping_name?: string;
      shipping_phone?: string;
      shipping_address?: string;
    }) => {
      programmaticRef.current = true;
      form.setFieldsValue(values);
      programmaticRef.current = false;
    },
    [form],
  );

  useEffect(() => {
    // Đổi chế độ => người dùng chủ động chuyển => cho phép điền lại.
    if (lastModeRef.current !== null && lastModeRef.current !== mode) {
      dirtyRef.current = false;
      lastSignatureRef.current = null;
    }
    lastModeRef.current = mode;
  }, [mode]);

  useEffect(() => {
    if (mode === 'other') {
      // Xoá sạch: giao cho người khác => người dùng nhập tay.
      lastSignatureRef.current = null;
      setFieldsSilently({
        shipping_name: '',
        shipping_phone: '',
        shipping_address: '',
      });
      return;
    }

    if (!profile || signature === null) return;

    // Không ghi đè dữ liệu người dùng đã gõ tay.
    if (dirtyRef.current) return;

    // Chỉ điền lại khi hồ sơ thực sự thay đổi (lần đầu hoặc vừa được sửa).
    if (lastSignatureRef.current === signature) return;
    lastSignatureRef.current = signature;

    setFieldsSilently({
      shipping_name: profile.full_name ?? '',
      // Chỉ điền số điện thoại khớp format VN - tránh mang số sai
      // từ hồ sơ sang form rồi bắt người dùng phải sửa lại.
      shipping_phone: isValidPhone(profile.phone) ? profile.phone : '',
      shipping_address: profile.address ?? '',
    });
  }, [form, profile, signature, mode, setFieldsSilently]);

  /** Đánh dấu form đã bị người dùng chỉnh sửa (để không ghi đè nữa). */
  const markDirty = () => {
    if (programmaticRef.current) return;
    dirtyRef.current = true;
  };

  return { markDirty };
}
