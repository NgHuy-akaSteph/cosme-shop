import { useQuery } from '@tanstack/react-query';
import api from '../api/axios';
import type { ProductListResponse } from '../types/product';

export interface ProductQueryParams {
  page?: number;
  size?: number;
  category_id?: number | null;
  brand_id?: number | null;
  search?: string;
  sort?: string;
  skin_types?: string[];
  concerns?: string[];
  min_price?: number | null;
  max_price?: number | null;
}

/** Hook goi GET /api/products voi tham so loc, dung chung cho HomePage/ProductsPage. */
export function useProducts(params: ProductQueryParams) {
  return useQuery({
    queryKey: ['products', params],
    queryFn: async () => {
      const query = new URLSearchParams();
      query.append('page', String(params.page ?? 1));
      query.append('size', String(params.size ?? 20));
      if (params.category_id) query.append('category_id', String(params.category_id));
      if (params.brand_id) query.append('brand_id', String(params.brand_id));
      if (params.search) query.append('search', params.search);
      if (params.sort) query.append('sort', params.sort);
      if (params.skin_types?.length) query.append('skin_types', params.skin_types.join(','));
      if (params.concerns?.length) query.append('concerns', params.concerns.join(','));
      if (params.min_price != null) query.append('min_price', String(params.min_price));
      if (params.max_price != null) query.append('max_price', String(params.max_price));

      const res = await api.get(`/api/products?${query.toString()}`);
      return res.data as ProductListResponse;
    },
  });
}
