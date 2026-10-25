import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Row, Col, Typography, Spin, Button, message, Breadcrumb, Select } from 'antd';
import { ShoppingOutlined, HeartOutlined, ShoppingCartOutlined } from '@ant-design/icons';
import { useState } from 'react';
import api from '../api/axios';
import { useCartStore } from '../store/cartStore';
import { useAuthStore } from '../store/authStore';
import { formatPrice } from '../utils/constants';

const { Title, Text, Paragraph } = Typography;

interface Product {
  id: number;
  name: string;
  price: number;
  sale_price: number | null;
  stock: number;
  description: string | null;
  image_url: string | null;
  images: string[] | null;
  variants: any[] | null;
  brand: { name: string } | null;
  category: { name: string } | null;
  skin_types: string[] | null;
  concerns: string[] | null;
  key_ingredients: string[] | null;
}

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { addItem } = useCartStore();
  
  const [selectedVariant, setSelectedVariant] = useState<string | undefined>(undefined);
  const [qty, setQty] = useState(1);
  
  const { data: product, isLoading } = useQuery({
    queryKey: ['product', id],
    queryFn: async () => {
      const res = await api.get(`/api/products/${id}`);
      return res.data.data as Product;
    },
  });
  
  const addToCartMutation = useMutation({
    mutationFn: async () => {
      if (!product) return;
      
      const effectivePrice = selectedVariant
        ? product.variants?.find((v) => v.id === selectedVariant)?.price || product.price
        : product.sale_price || product.price;
      
      addItem({
        product_id: product.id,
        variant_id: selectedVariant,
        name: product.name,
        price: Number(effectivePrice),
        image_url: product.image_url || undefined,
        variant_name: selectedVariant
          ? product.variants?.find((v) => v.id === selectedVariant)?.name
          : undefined,
      }, qty);
      
      message.success('Đã thêm vào giỏ hàng');
    },
  });
  
  const addToWishlistMutation = useMutation({
    mutationFn: async () => {
      if (!product) return;
      await api.post(`/api/wishlist/${product.id}`);
    },
    onSuccess: () => {
      message.success('Đã thêm vào danh sách yêu thích');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Không thể thêm vào yêu thích');
    },
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
        {/* Image */}
        <Col xs={24} md={12}>
          <div style={{
            background: '#f5f5f5',
            height: 400,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 8,
            overflow: 'hidden',
          }}>
            {product.image_url ? (
              <img
                src={product.image_url}
                alt={product.name}
                style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }}
              />
            ) : (
              <ShoppingOutlined style={{ fontSize: 100, color: '#ccc' }} />
            )}
          </div>
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
                <Text strong style={{ fontSize: 28, color: '#fa8c16' }}>
                  {formatPrice(product.sale_price)}
                </Text>
              </>
            ) : (
              <Text strong style={{ fontSize: 28, color: '#fa8c16' }}>
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
                  label: `${v.name} - ${formatPrice(v.price)}`,
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
              <Button onClick={() => setQty(Math.min(product.stock || 1, qty + 1))}>+</Button>
              <Text type="secondary" style={{ marginLeft: 16 }}>
                {product.stock > 0 ? `${product.stock} sản phẩm có sẵn` : 'Hết hàng'}
              </Text>
            </div>
          </div>
          
          {/* Actions */}
          <div style={{ marginTop: 32, display: 'flex', gap: 16 }}>
            <Button
              type="primary"
              size="large"
              icon={<ShoppingCartOutlined />}
              onClick={() => {
                if (product.variants && product.variants.length > 0 && !selectedVariant) {
                  message.error('Vui lòng chọn phân loại');
                  return;
                }
                addToCartMutation.mutate();
              }}
              disabled={product.stock === 0}
            >
              Thêm vào giỏ
            </Button>
            <Button
              size="large"
              icon={<HeartOutlined />}
              onClick={() => {
                if (!user) {
                  navigate('/login');
                } else {
                  addToWishlistMutation.mutate();
                }
              }}
              loading={addToWishlistMutation.isPending}
            >
              Yêu thích
            </Button>
          </div>
          
          {/* Description */}
          {product.description && (
            <div style={{ marginTop: 32 }}>
              <Title level={4}>Mô tả</Title>
              <Paragraph>{product.description}</Paragraph>
            </div>
          )}
          
          {/* Ingredients */}
          {product.key_ingredients && product.key_ingredients.length > 0 && (
            <div style={{ marginTop: 24 }}>
              <Title level={4}>Thành phần chính</Title>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {product.key_ingredients.map((ing) => (
                  <span key={ing} style={{
                    background: '#f0f0f0',
                    padding: '4px 12px',
                    borderRadius: 16,
                  }}>
                    {ing}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Col>
      </Row>
    </div>
  );
}
