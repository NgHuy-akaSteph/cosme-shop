import { useQuery } from '@tanstack/react-query';
import { Row, Col, Typography, Skeleton } from 'antd';
import { Link } from 'react-router-dom';
import api from '../../api/axios';
import { colors } from '../../theme';

const { Text } = Typography;

interface Brand {
  id: number;
  name: string;
  slug: string;
  logo_url: string | null;
}

export default function BrandStrip() {
  const { data, isLoading } = useQuery({
    queryKey: ['brands'],
    queryFn: async () => {
      const res = await api.get('/api/brands');
      return res.data.data as Brand[];
    },
  });

  if (isLoading) {
    return (
      <Row gutter={[16, 16]}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Col key={i} xs={12} sm={8} md={4}>
            <Skeleton active paragraph={{ rows: 1 }} />
          </Col>
        ))}
      </Row>
    );
  }

  return (
    <Row gutter={[16, 16]}>
      {(data ?? []).map((brand) => (
        <Col key={brand.id} xs={12} sm={8} md={4}>
          <Link to={`/products?brand_id=${brand.id}`}>
            <div
              style={{
                height: 72,
                borderRadius: 12,
                border: `1px solid ${colors.border}`,
                background: colors.surface,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 12,
              }}
            >
              {brand.logo_url ? (
                <img
                  src={brand.logo_url}
                  alt={brand.name}
                  loading="lazy"
                  style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }}
                />
              ) : (
                <Text strong style={{ color: colors.textSecondary }}>
                  {brand.name}
                </Text>
              )}
            </div>
          </Link>
        </Col>
      ))}
    </Row>
  );
}
