import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../api/axios';
import { useAuthStore, type User } from '../store/authStore';

/** Khoa query cho thong tin nguoi dung hien tai. */
export const currentUserKey = ['current-user'] as const;

/** Response cua `GET /api/auth/me`. */
interface CurrentUserResponse {
  data: User;
}

/**
 * Lay thong tin nguoi dung hien tai tu server (nguon su that duy nhat).
 *
 * Server state -> TanStack Query (theo `docs/rules.md` §6.2).
 * `useAuthStore` chi giu ban sao client-side de UI hien thi nhanh; khi server
 * tra du lieu moi thi store duoc dong bo lai qua `updateUser` de khong bi stale.
 */
export function useCurrentUser() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const updateUser = useAuthStore((state) => state.updateUser);

  const query = useQuery({
    queryKey: currentUserKey,
    queryFn: async () => {
      const res = await api.get<CurrentUserResponse>('/api/auth/me');
      return res.data.data;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  // TanStack Query v5 bo `onSuccess` khoi `useQuery` -> dong bo store qua effect.
  const user = query.data;
  useEffect(() => {
    if (user) {
      updateUser(user);
    }
  }, [user, updateUser]);

  return query;
}
