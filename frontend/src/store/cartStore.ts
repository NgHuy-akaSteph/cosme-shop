import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Số lượng tối đa cho 1 dòng giỏ.
 * Khớp với validation backend: `qty: int = Field(..., gt=0, le=99)`
 * trong `backend/app/schemas/order.py` (vượt sẽ bị API trả 422).
 */
export const MAX_QTY_PER_ITEM = 99;

export interface CartItem {
  product_id: number;
  variant_id?: string;
  qty: number;
  name: string;
  price: number;
  image_url?: string;
  variant_name?: string;
  /** Tồn kho hiện tại từ server (undefined = chưa đồng bộ). */
  stock?: number;
  /** Sản phẩm còn bán hay không (undefined = chưa đồng bộ). */
  is_active?: boolean;
}

interface CartState {
  items: CartItem[];

  // Actions
  addItem: (item: Omit<CartItem, 'qty'>, qty?: number) => void;
  removeItem: (product_id: number, variant_id?: string) => void;
  updateQty: (product_id: number, variant_id: string | undefined, qty: number) => void;
  clearCart: () => void;
  /**
   * Đồng bộ metadata (giá, tên, ảnh, tồn kho) từ server cho các dòng trong giỏ.
   * KHÔNG thay đổi `qty` — số lượng do người dùng tự chỉnh.
   */
  syncItems: (items: CartItem[]) => void;

  // Computed
  getTotal: () => number;
  getItemCount: () => number;
}

/** Clamp số lượng về [1, MAX_QTY_PER_ITEM]. */
function clampQty(qty: number): number {
  if (!Number.isFinite(qty)) return 1;
  return Math.min(MAX_QTY_PER_ITEM, Math.max(1, Math.trunc(qty)));
}

/** Khoá dòng giỏ = product_id + variant_id (cùng sản phẩm khác phân loại là 2 dòng). */
function itemKey(product_id: number, variant_id?: string): string {
  return `${product_id}-${variant_id ?? ''}`;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: (item, qty = 1) => {
        const safeQty = clampQty(qty);
        set((state) => {
          const existingIndex = state.items.findIndex(
            (i) => i.product_id === item.product_id && i.variant_id === item.variant_id
          );

          if (existingIndex >= 0) {
            // Update qty - create new array with updated item
            const newItems = state.items.map((i, idx) =>
              idx === existingIndex ? { ...i, qty: clampQty(i.qty + safeQty) } : i
            );
            return { items: newItems };
          }

          // Add new item
          return { items: [...state.items, { ...item, qty: safeQty }] };
        });
      },

      removeItem: (product_id, variant_id) => {
        set((state) => ({
          items: state.items.filter(
            (i) => !(i.product_id === product_id && i.variant_id === variant_id)
          ),
        }));
      },

      updateQty: (product_id, variant_id, qty) => {
        if (qty <= 0) {
          get().removeItem(product_id, variant_id);
          return;
        }

        const safeQty = clampQty(qty);
        set((state) => {
          const newItems = state.items.map((item) => {
            if (item.product_id === product_id && item.variant_id === variant_id) {
              return { ...item, qty: safeQty };
            }
            return item;
          });
          return { items: newItems };
        });
      },

      clearCart: () => {
        set({ items: [] });
      },

      syncItems: (newItems) => {
        set((state) => {
          // Giữ nguyên `qty` của từng dòng (người dùng tự chỉnh, không lấy từ server).
          const qtyMap = new Map(
            state.items.map((i) => [itemKey(i.product_id, i.variant_id), i.qty]),
          );
          return {
            items: newItems.map((i) => ({
              ...i,
              qty: qtyMap.get(itemKey(i.product_id, i.variant_id)) ?? i.qty,
            })),
          };
        });
      },

      getTotal: () => {
        return get().items.reduce((sum, item) => sum + item.price * item.qty, 0);
      },

      getItemCount: () => {
        return get().items.reduce((sum, item) => sum + item.qty, 0);
      },
    }),
    {
      name: 'cart-storage',
    }
  )
);
