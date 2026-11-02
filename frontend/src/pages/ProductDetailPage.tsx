import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Row,
  Col,
  Typography,
  Spin,
  Button,
  message,
  Breadcrumb,
  Select,
  Tabs,
  Tag,
  Descriptions,
  Image,
} from 'antd';
import { ShoppingOutlined, HeartOutlined, ShoppingCartOutlined } from '@ant-design/icons';
import { useState } from 'react';
import api from '../api/axios';
import { useCartStore } from '../store/cartStore';
import { useAuthStore } from '../store/authStore';
import { formatPrice } from '../utils/constants';
import type { ApiError } from '../types/api';
import { getErrorMessage } from '../types/api';
import type { Product } from '../types/product';
import ProductCard from '../components/ProductCard';
import { colors } from '../theme';

const { Title, Text, Paragraph } = Typography;

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { addItem } = useCartStore();

  const [selectedVariant, setSelectedVariant] = useState<string | undefined>(undefined);
  const [qty, setQty] = useState(1);
  const [activeImage, setActiveImage] = useState(0);

  const { data: product, isLoading } = useQuery({
    queryKey: ['product', id],
    queryFn: async () => {
      const res = await api.get(`/api/products/${id}`);
      return res.data.data as Product;
    },
  });

  const { data: similarData } = useQuery({
    queryKey: ['product', id, 'similar'],
    queryFn: async () => {
      const res = await api.get(`/api/products/${id}/similar?limit=8`);
      return res.data.data as Product[];
    },
    enabled: Boolean(id),
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!product) {
    return <Text>Không tìm thấy sản phẩm</Text>;
  }

  const galleryImages = product.images?.length
    ? product.images.map((img) => img.secure_url || img.url)
    : product.image_url
      ? [product.image_url]
      : [];

  const selectedVariantObj = product.variants?.find((v) => v.id === selectedVariant);
  const maxQty = selectedVariantObj?.stock ?? product.stock ?? 0;

  const handleAddToWishlist = async () => {
    if (!user) {
      navigate('/login');
      return;
    }
    try {
      await api.post(`/api/wishlist/${product.id}`);
      message.success('Đã thêm vào danh sách yêu thích');
    } catch (error) {
      message.error(getErrorMessage(error as ApiError, 'Không thể thêm vào yêu thích'));
    }
  };

  const handleAddToCart = () => {
    if (product.variants && product.variants.length > 0 && !selectedVariant) {
      message.error('Vui lòng chọn phân loại');
      return;
    }

    const effectivePrice = selectedVariantObj
      ? selectedVariantObj.price ?? product.price
      : product.sale_price ?? product.price;

    addItem(
      {
        product_id: product.id,
        variant_id: selectedVariant,
        name: product.name,
        price: Number(effectivePrice),
        image_url: product.image_url || undefined,
        variant_name: selectedVariantObj?.name,
      },
      qty
    );

    message.success('Đã thêm vào giỏ hàng');
  };

  const detailTab = (
    <Paragraph style={{ marginBottom: 0 }}>
      {product.description || 'Chưa có mô tả cho sản phẩm này.'}
    </Paragraph>
  );

  const ingredientsTab = (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {product.key_ingredients?.length ? (
        product.key_ingredients.map((ing) => <Tag key={ing}>{ing}</Tag>)
      ) : (
        <Text type="secondary">Chưa có thông tin thành phần chính.</Text>
      )}
    </div>
  );

  const infoTab = (
    <Descriptions column={2} size="small" bordered>
      <Descriptions.Item label="Thương hiệu">{product.brand?.name ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="Danh mục">{product.category?.name ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="Loại da phù hợp">
        {product.skin_types?.length ? product.skin_types.join(', ') : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="Vấn đề giải quyết">
        {product.concerns?.length ? product.concerns.join(', ') : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="Tồn kho">{product.stock}</Descriptions.Item>
      <Descriptions.Item label="Đã bán">{product.sold_count}</Descriptions.Item>
      <Descriptions.Item label="Đánh giá">
        {product.rating_avg ?? 0} ({product.rating_count ?? 0} lượt)
      </Descriptions.Item>
      <Descriptions.Item label="Không chứa">
        {product.free_from?.length ? product.free_from.join(', ') : '-'}
      </Descriptions.Item>
    </Descriptions>
  );

  return (
    <div>
      <Breadcrumb
        items={[
          { title: <Link to="/">Trang chủ</Link> },
          { title: <Link to="/products">Sản phẩm</Link> },
          { title: product.name },
        ]}
        style={{ marginBottom: 16 }}
      />

      <Row gutter={[32, 32]}>
        {/* Gallery */}
        <Col xs={24} md={12}>
          <div
            style={{
              background: colors.galleryPlaceholder,
              height: 420,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 16,
              overflow: 'hidden',
            }}
          >
            {galleryImages[activeImage] ? (
              <Image
                src={galleryImages[activeImage]}
                alt={product.name}
                style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }}
              />
            ) : (
              <ShoppingOutlined style={{ fontSize: 100, color: colors.iconMuted }} />
            )}
          </div>

          {galleryImages.length > 1 && (
            <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              {galleryImages.map((src, index) => (
                <img
                  key={src}
                  src={src}
                  alt={`${product.name} ${index + 1}`}
                  onClick={() => setActiveImage(index)}
                  style={{
                    width: 64,
                    height: 64,
                    objectFit: 'cover',
                    borderRadius: 8,
                    cursor: 'pointer',
                    border:
                      index === activeImage
                        ? `2px solid ${colors.primary}`
                        : `1px solid ${colors.border}`,
                  }}
                />
              ))}
            </div>
          )}
        </Col>

        {/* Info */}
        <Col xs={24} md={12}>
          <Title level={2}>{product.name}</Title>

          <Text type="secondary" style={{ fontSize: 16 }}>
            {product.brand?.name} | {product.category?.name}
          </Text>

          <div style={{ marginTop: 24 }}>
            {product.sale_price ? (
              <>
                <Text delete style={{ fontSize: 20, marginRight: 16 }}>
                  {formatPrice(product.price)}
                </Text>
                <Text strong style={{ fontSize: 28, color: colors.primary }}>
                  {formatPrice(product.sale_price)}
                </Text>
              </>
            ) : (
              <Text strong style={{ fontSize: 28, color: colors.primary }}>
                {formatPrice(product.price)}
              </Text>
            )}
          </div>

          {/* Variants */}
          {product.variants && product.variants.length > 0 && (
            <div style={{ marginTop: 24 }}>
              <Text strong>Phân loại:</Text>
              <Select
                placeholder="Chọn phân loại"
                style={{ width: '100%', marginTop: 8 }}
                value={selectedVariant}
                onChange={setSelectedVariant}
                options={product.variants.map((v) => ({
                  value: v.id,
                  label: `${v.name} - ${formatPrice(v.price ?? product.price)}`,
                }))}
              />
            </div>
          )}

          {/* Quantity */}
          <div style={{ marginTop: 24 }}>
            <Text strong>Số lượng:</Text>
            <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 16 }}>
              <Button onClick={() => setQty(Math.max(1, qty - 1))}>-</Button>
              <span style={{ minWidth: 40, textAlign: 'center' }}>{qty}</span>
              <Button onClick={() => setQty(Math.min(Math.max(maxQty, 1), qty + 1))}>+</Button>
              <Text type="secondary" style={{ marginLeft: 16 }}>
                {maxQty > 0 ? `${maxQty} sản phẩm có sẵn` : 'Hết hàng'}
              </Text>
            </div>
          </div>

          {/* Actions */}
          <div style={{ marginTop: 32, display: 'flex', gap: 16 }}>
            <Button
              type="primary"
              size="large"
              icon={<ShoppingCartOutlined />}
              onClick={handleAddToCart}
              disabled={maxQty === 0}
            >
              Thêm vào giỏ
            </Button>
            <Button size="large" icon={<HeartOutlined />} onClick={handleAddToWishlist}>
              Yêu thích
            </Button>
          </div>

          <Tabs
            style={{ marginTop: 32 }}
            items={[
              { key: 'description', label: 'Mô tả', children: detailTab },
              { key: 'ingredients', label: 'Thành phần chính', children: ingredientsTab },
              { key: 'info', label: 'Thông tin', children: infoTab },
            ]}
          />
        </Col>
      </Row>

      {/* San pham tuong tu */}
      {similarData && similarData.length > 0 && (
        <div style={{ marginTop: 48 }}>
          <Title level={3}>Sản phẩm tương tự</Title>
          <Row gutter={[16, 16]}>
            {similarData.map((item) => (
              <Col key={item.id} xs={12} sm={8} md={6} lg={6}>
                <ProductCard product={item} />
              </Col>
            ))}
          </Row>
        </div>
      )}
    </div>
  );
}
