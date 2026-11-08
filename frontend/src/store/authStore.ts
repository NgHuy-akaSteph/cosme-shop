import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { useCartStore } from './cartStore';

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone?: string;
  address?: string;
  avatar_url?: string;
  role: string;
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  
  // Actions
  login: (user: User, token: string) => void;
  /**
   * Đăng xuất.
   *
   * `clearCart: true` chỉ dùng cho **đăng xuất chủ động** (người dùng bấm nút).
   * Khi token hết hạn (401 interceptor gọi `logout()` không tham số) → GIỮ giỏ hàng,
   * tránh mất giỏ chỉ vì hết phiên đăng nhập.
   */
  logout: (options?: { clearCart?: boolean }) => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      login: (user, token) => {
        localStorage.setItem('auth_token', token);
        set({ user, token, isAuthenticated: true });
      },
      
      logout: (options) => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        set({ user: null, token: null, isAuthenticated: false });
        // Chỉ xoá giỏ khi user chủ động đăng xuất.
        if (options?.clearCart) {
          useCartStore.getState().clearCart();
        }
      },
      
      updateUser: (userData) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        }));
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
