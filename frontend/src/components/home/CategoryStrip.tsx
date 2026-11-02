import { useQuery } from '@tanstack/react-query';
import { Row, Col, Typography, Skeleton } from 'antd';
import { Link } from 'react-router-dom';
import api from '../../api/axios';
import { colors } from '../../theme';

const { Text } = Typography;

interface Category {
  id: number;
  name: string;
  slug: string;
  image_url: string | null;
}

export default function CategoryStrip() {
  const { data, isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const res = await api.get('/api/categories');
      return res.data.data as Category[];
    },
  });

  if (isLoading) {
    return (
      <Row gutter={[16, 16]}>
        {Array.from({ length: 8 }).map((_, i) => (
          <Col key={i} xs={12} sm={8} md={6} lg={3}>
            <Skeleton.Image active style={{ width: '100%', height: 120, borderRadius: 16 }} />
          </Col>
        ))}
      </Row>
    );
  }

  return (
    <Row gutter={[16, 16]}>
      {(data ?? []).map((category) => (
        <Col key={category.id} xs={12} sm={8} md={6} lg={3}>
          <Link to={`/products?category_id=${category.id}`}>
            <div
              style={{
                height: 120,
                borderRadius: 16,
                overflow: 'hidden',
                background: `linear-gradient(160deg, ${colors.primarySoft} 0%, ${colors.gradientTint} 100%)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
              }}
            >
              {category.image_url ? (
                <img
                  src={category.image_url}
                  alt={category.name}
                  loading="lazy"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : (
                <Text strong style={{ color: colors.primary }}>
                  {category.name}
                </Text>
              )}
            </div>
            <div style={{ textAlign: 'center', marginTop: 8, fontWeight: 500 }}>
              {category.name}
            </div>
          </Link>
        </Col>
      ))}
    </Row>
  );
}
