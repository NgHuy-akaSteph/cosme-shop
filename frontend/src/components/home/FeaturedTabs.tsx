import { Tabs, Row, Col } from 'antd';
import ProductCard, { ProductCardSkeleton } from '../ProductCard';
import { useProducts } from '../../hooks/useProducts';
import { useAddToCartFromCard } from '../../hooks/useAddToCartFromCard';

interface ProductGridProps {
  sort: string;
}

function ProductGrid({ sort }: ProductGridProps) {
  const { data, isLoading } = useProducts({ sort, size: 8 });
  const handleAddToCart = useAddToCartFromCard();

  if (isLoading) {
    return (
      <Row gutter={[16, 16]}>
        {Array.from({ length: 8 }).map((_, i) => (
          <Col key={i} xs={12} sm={8} md={6} lg={6}>
            <ProductCardSkeleton />
          </Col>
        ))}
      </Row>
    );
  }

  return (
    <Row gutter={[16, 16]}>
      {(data?.data ?? []).map((product) => (
        <Col key={product.id} xs={12} sm={8} md={6} lg={6}>
          <ProductCard product={product} onAddToCart={handleAddToCart} />
        </Col>
      ))}
    </Row>
  );
}

const TABS = [
  { key: 'best_seller', label: 'Bán chạy', sort: 'best_seller' },
  { key: 'newest', label: 'Mới về', sort: 'newest' },
  { key: 'price_asc', label: 'Giá thấp nhất', sort: 'price_asc' },
];

export default function FeaturedTabs() {
  return (
    <Tabs
      defaultActiveKey="best_seller"
      items={TABS.map((tab) => ({
        key: tab.key,
        label: tab.label,
        children: <ProductGrid sort={tab.sort} />,
      }))}
    />
  );
}
