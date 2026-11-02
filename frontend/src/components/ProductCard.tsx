import { Link } from 'react-router-dom';
import { Card, Tag, Typography, Button, Skeleton } from 'antd';
import { ShoppingCartOutlined, ShoppingOutlined } from '@ant-design/icons';
import { formatPrice } from '../utils/constants';
import { colors } from '../theme';
import type { Product } from '../types/product';

const { Text } = Typography;

interface ProductCardProps {
  product: Product;
  onAddToCart?: (product: Product) => void;
}

/** Card san pham dung chung cho trang chu, danh sach san pham, san pham tuong tu. */
export default function ProductCard({ product, onAddToCart }: ProductCardProps) {
  const hasDiscount = Boolean(product.sale_price);
  const discountPercent =
    hasDiscount && Number(product.price) > 0
      ? Math.round((1 - Number(product.sale_price) / Number(product.price)) * 100)
      : 0;

  return (
    <Link to={`/products/${product.id}`} style={{ display: 'block', height: '100%' }}>
      <Card
        hoverable
        variant="borderless"
        styles={{ body: { padding: 16 } }}
        style={{ height: '100%', borderRadius: 16, overflow: 'hidden' }}
        cover={
          <div
            style={{
              height: 220,
              background: `linear-gradient(160deg, ${colors.gradientWarmEnd} 0%, ${colors.gradientTint} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
            }}
          >
            {product.image_url ? (
              <img
                src={product.image_url}
                alt={product.name}
                loading="lazy"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <ShoppingOutlined style={{ fontSize: 48, color: colors.placeholderIcon }} />
            )}

            {hasDiscount && (
              <Tag
                color={colors.primary}
                style={{ position: 'absolute', top: 12, left: 12, margin: 0, borderRadius: 8 }}
              >
                -{discountPercent}%
              </Tag>
            )}

            {product.stock === 0 && (
              <Tag
                color="default"
                style={{ position: 'absolute', top: 12, right: 12, margin: 0, borderRadius: 8 }}
              >
                Hết hàng
              </Tag>
            )}
          </div>
        }
      >
        <Text type="secondary" style={{ fontSize: 12 }}>
          {product.brand?.name}
        </Text>

        <div
          style={{
            fontWeight: 600,
            margin: '4px 0 8px',
            minHeight: 44,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {product.name}
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          {hasDiscount ? (
            <>
              <Text delete type="secondary" style={{ fontSize: 13 }}>
                {formatPrice(product.price)}
              </Text>
              <Text strong style={{ color: colors.primary, fontSize: 16 }}>
                {formatPrice(product.sale_price as number | string)}
              </Text>
            </>
          ) : (
            <Text strong style={{ color: colors.primary, fontSize: 16 }}>
              {formatPrice(product.price)}
            </Text>
          )}
        </div>

        {onAddToCart && (
          <Button
            type="primary"
            block
            icon={<ShoppingCartOutlined />}
            style={{ marginTop: 12 }}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onAddToCart(product);
            }}
            disabled={product.stock === 0}
          >
            Thêm vào giỏ
          </Button>
        )}
      </Card>
    </Link>
  );
}

export function ProductCardSkeleton() {
  return (
    <Card variant="borderless" style={{ borderRadius: 16 }}>
      <Skeleton.Image style={{ width: '100%', height: 220, marginBottom: 16 }} active />
      <Skeleton active paragraph={{ rows: 2 }} />
    </Card>
  );
}
