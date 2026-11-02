/** Type du dung chung cho Product (BE tra camelCase field, gia tien co the string hoac number) */

/** Cac bien the URL theo kich co hien thi, sinh tu Cloudinary public_id */
export interface ProductImageUrls {
  /** Card san pham - vuong 600x600 */
  card: string;
  /** Trang chi tiet - 1200x840 */
  detail: string;
  /** Thumbnail nho - 160x160 (gio hang, wishlist) */
  thumb: string;
}

export interface ProductImage {
  id: number;
  product_id: number;
  public_id: string;
  secure_url: string;
  alt_text: string | null;
  width: number | null;
  height: number | null;
  format: string | null;
  position: number;
  is_main: boolean;
  image_urls?: ProductImageUrls | null;
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
  image_urls?: ProductImageUrls | null;
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
