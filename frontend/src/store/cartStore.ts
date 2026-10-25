import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface CartItem {
  product_id: number;
  variant_id?: string;
  qty: number;
  name: string;
  price: number;
  image_url?: string;
  variant_name?: string;
}

interface CartState {
  items: CartItem[];
  
  // Actions
  addItem: (item: Omit<CartItem, 'qty'>, qty?: number) => void;
  removeItem: (product_id: number, variant_id?: string) => void;
  updateQty: (product_id: number, variant_id: string | undefined, qty: number) => void;
  clearCart: () => void;
  
  // Computed
  getTotal: () => number;
  getItemCount: () => number;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      
      addItem: (item, qty = 1) => {
        set((state) => {
          const existingIndex = state.items.findIndex(
            (i) => i.product_id === item.product_id && i.variant_id === item.variant_id
          );
          
          if (existingIndex >= 0) {
            // Update qty - create new array with updated item
            const newItems = state.items.map((i, idx) =>
              idx === existingIndex ? { ...i, qty: i.qty + qty } : i
            );
            return { items: newItems };
          }
          
          // Add new item
          return { items: [...state.items, { ...item, qty }] };
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
        
        set((state) => {
          const newItems = state.items.map((item) => {
            if (item.product_id === product_id && item.variant_id === variant_id) {
              return { ...item, qty };
            }
            return item;
          });
          return { items: newItems };
        });
      },
      
      clearCart: () => {
        set({ items: [] });
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
