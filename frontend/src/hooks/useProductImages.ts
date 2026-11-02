import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../api/axios';
import type { ProductImage } from '../types/product';

/** Khoa query cho danh sach anh cua 1 san pham */
export const productImagesKey = (productId: number) => ['product-images', productId];

/** Timeout rieng cho upload anh (file 5MB tren mang cham can nhieu thoi gian hon) */
const UPLOAD_TIMEOUT = 120000;

/**
 * Lay danh sach anh cua 1 san pham.
 * `staleTime: 0` vi anh thay doi thuong xuyen (upload/xoa/set-main).
 */
export function useProductImages(productId: number | undefined) {
  return useQuery({
    queryKey: productImagesKey(productId ?? 0),
    queryFn: async () => {
      const res = await api.get(`/api/upload/product-image/product/${productId}`);
      return res.data as ProductImage[];
    },
    enabled: Boolean(productId),
    staleTime: 0,
  });
}

export interface UploadImagePayload {
  file: File;
  altText?: string | null;
  isMain?: boolean;
}

/**
 * Hook chua cac mutation quan ly anh cua 1 san pham.
 *
 * Chi lay `productId` khi hook duoc goi -> moi mutation invalidate dung
 * query cache can thiet.
 */
export function useProductImageMutations(productId: number) {
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: productImagesKey(productId) });
    queryClient.invalidateQueries({ queryKey: ['admin', 'products'] });
    queryClient.invalidateQueries({ queryKey: ['product', productId] });
    queryClient.invalidateQueries({ queryKey: ['products'] });
  };

  const uploadMutation = useMutation({
    mutationFn: async ({ file, altText, isMain }: UploadImagePayload) => {
      const formData = new FormData();
      formData.append('file', file);
      if (altText) formData.append('alt_text', altText);
      formData.append('is_main', String(Boolean(isMain)));

      const res = await api.post(
        `/api/upload/product-image/${productId}`,
        formData,
        { timeout: UPLOAD_TIMEOUT }
      );
      return res.data as ProductImage;
    },
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: async (imageId: number) => {
      const res = await api.delete(`/api/upload/product-image/${imageId}`);
      return res.data as { message: string; image_id: number; asset_kept: boolean };
    },
    onSuccess: invalidate,
  });

  const setMainMutation = useMutation({
    mutationFn: async (imageId: number) => {
      const res = await api.patch(`/api/upload/product-image/${imageId}/set-main`);
      return res.data as ProductImage;
    },
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: async ({
      imageId,
      altText,
    }: {
      imageId: number;
      altText: string;
    }) => {
      const formData = new FormData();
      formData.append('alt_text', altText);

      const res = await api.patch(
        `/api/upload/product-image/${imageId}`,
        formData
      );
      return res.data as ProductImage;
    },
    onSuccess: invalidate,
  });

  const reorderMutation = useMutation({
    mutationFn: async (imageIds: number[]) => {
      const res = await api.patch(
        `/api/upload/product-image/${productId}/reorder`,
        { image_ids: imageIds }
      );
      return res.data as ProductImage[];
    },
    onSuccess: invalidate,
  });

  return {
    uploadMutation,
    deleteMutation,
    setMainMutation,
    updateMutation,
    reorderMutation,
  };
}
