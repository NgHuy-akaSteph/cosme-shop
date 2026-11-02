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

// Bo loc theo nganh my pham
export const SKIN_TYPES = [
  { value: 'oily', label: 'Da dầu' },
  { value: 'dry', label: 'Da khô' },
  { value: 'combination', label: 'Da hỗn hợp' },
  { value: 'normal', label: 'Da bình thường' },
  { value: 'sensitive', label: 'Da nhạy cảm' },
];

export const CONCERNS = [
  { value: 'acne', label: 'Mụn' },
  { value: 'dark_spots', label: 'Thâm nám' },
  { value: 'aging', label: 'Lão hoá' },
  { value: 'dehydration', label: 'Mất nước' },
  { value: 'dullness', label: 'Xỉn da' },
  { value: 'pores', label: 'Lỗ chân lông' },
  { value: 'redness', label: 'Đỏ da' },
];

// Khoang gia preset
export const PRICE_RANGES = [
  { value: '0-200000', label: 'Dưới 200k', min: 0, max: 200000 },
  { value: '200000-500000', label: '200k - 500k', min: 200000, max: 500000 },
  { value: '500000-1000000', label: '500k - 1tr', min: 500000, max: 1000000 },
  { value: '1000000-', label: 'Trên 1tr', min: 1000000, max: null },
];

export const SORT_OPTIONS = [
  { value: 'newest', label: 'Mới nhất' },
  { value: 'best_seller', label: 'Bán chạy' },
  { value: 'price_asc', label: 'Giá: Thấp đến cao' },
  { value: 'price_desc', label: 'Giá: Cao đến thấp' },
];

