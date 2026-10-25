// Formatting utilities
export function formatPrice(price: number | string): string {
  return new Intl.NumberFormat('vi-VN').format(Number(price)) + ' đ';
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('vi-VN');
}

// Order status
export const statusColors: Record<string, string> = {
  pending: 'orange',
  confirmed: 'blue',
  packing: 'cyan',
  shipping: 'purple',
  delivered: 'green',
  cancelled: 'red',
};

export const statusText: Record<string, string> = {
  pending: 'Chờ xác nhận',
  confirmed: 'Đã xác nhận',
  packing: 'Đang đóng gói',
  shipping: 'Đang giao hàng',
  delivered: 'Đã giao hàng',
  cancelled: 'Đã hủy',
};

// Shipping
export const SHIPPING_FREE_THRESHOLD = 500000;
export const SHIPPING_FEE = 30000;
