/** Type du dung chung cho Product (BE tra camelCase field, gia tien co the string hoac number) */

export interface ProductImage {
  id: number;
  url: string;
  secure_url: string | null;
  alt_text: string | null;
  position: number;
  is_main: boolean;
}

export interface ProductVariant {
  id: string;
  name: string;
  price?: number | null;
  stock?: number | null;
  image_url?: string | null;
}

export interface ProductCategory {
  id: number;
  name: string;
  slug: string;
}

export interface ProductBrand {
  id: number;
  name: string;
  slug: string;
}

export interface Product {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  price: number | string;
  sale_price: number | string | null;
  stock: number;
  image_url: string | null;
  category_id: number;
  brand_id: number;
  skin_types: string[] | null;
  concerns: string[] | null;
  key_ingredients: string[] | null;
  free_from: string[] | null;
  variants: ProductVariant[] | null;
  sold_count: number;
  rating_avg: number;
  rating_count: number;
  is_active: boolean;
  category: ProductCategory | null;
  brand: ProductBrand | null;
  images: ProductImage[] | null;
}

export interface ProductListResponse {
  data: Product[];
  total: number;
  page: number;
  size: number;
}
