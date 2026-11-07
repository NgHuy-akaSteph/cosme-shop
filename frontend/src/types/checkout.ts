/** Kieu du lieu dung chung cho qua thanh toan (checkout). */

/** Che do nhan hang: giao cho ban than (dien ho so) hoac cho nguoi khac (nhap tay). */
export type RecipientMode = 'self' | 'other';

/** Gia tri form thong tin giao hang. */
export interface CheckoutFormValues {
  shipping_name: string;
  shipping_phone: string;
  shipping_address: string;
  note?: string;
}

/**
 * Regex so dien thoai Viet Nam.
 * Dung chung de validate form va kiem tra ho so truoc khi prefill
 * (khong mang so khong hop le tu ho so sang form).
 */
export const PHONE_PATTERN = /^0\d{9,10}$/;

/** Kiem tra so dien thoai hop le dang chuoi Viet Nam. */
export function isValidPhone(phone: string | null | undefined): boolean {
  return Boolean(phone && PHONE_PATTERN.test(phone));
}
