import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { Card, Row, Col, Typography, Spin, Button } from 'antd';
import { ShoppingOutlined } from '@ant-design/icons';
import api from '../api/axios';
import { formatPrice } from '../utils/constants';

const { Title, Text } = Typography;

interface Product {
  id: number;
  name: string;
  slug: string;
  price: number;
  sale_price: number | null;
  image_url: string | null;
  brand: { name: string } | null;
}

export default function HomePage() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ['products', 'best-sellers'],
    queryFn: async () => {
      const res = await api.get('/api/products/best-sellers?limit=8');
      return res.data.data as Product[];
    },
  });
  
  return (
    <div>
      {/* Hero Section */}
      <div style={{
        background: 'linear-gradient(135deg, #fa8c16 0%, #ff7a45 100%)',
        color: 'white',
        padding: '80px 50px',
        textAlign: 'center',
        borderRadius: 8,
        marginBottom: 40,
      }}>
        <Title level={1} style={{ color: 'white', marginBottom: 16, fontSize: 48 }}>
          Mỹ phẩm chính hãng cao cấp
        </Title>
        <Text style={{ color: 'white', fontSize: 18, display: 'block', marginBottom: 32 }}>
          Làm đẹp an toàn - Chất lượng đảm bảo - Giao hàng toàn quốc
        </Text>
        <Button
          type="default"
          size="large"
          icon={<ShoppingOutlined />}
          onClick={() => navigate('/products')}
          style={{
            height: 50,
            fontSize: 16,
            padding: '0 40px',
            backgroundColor: 'white',
            borderColor: 'white',
            color: '#fa8c16',
          }}
        >
          Khám phá ngay
        </Button>
      </div>
      
      {/* Best Sellers */}
      <div style={{ marginTop: 40 }}>
        <Title level={2}>Sản phẩm bán chạy</Title>
        
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : (
          <Row gutter={[16, 16]}>
            {data?.map((product) => (
              <Col key={product.id} xs={24} sm={12} md={6}>
                <Link to={`/products/${product.id}`}>
                  <Card
                    hoverable
                    cover={
                      <div style={{
                        height: 200,
                        background: '#f5f5f5',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        overflow: 'hidden',
                      }}>
                        {product.image_url ? (
                          <img
                            src={product.image_url}
                            alt={product.name}
                            loading="lazy"
                            style={{ height: '100%', width: '100%', objectFit: 'contain' }}
                          />
                        ) : (
                          <ShoppingOutlined style={{ fontSize: 48, color: '#ccc' }} />
                        )}
                      </div>
                    }
                  >
                    <Card.Meta
                      title={product.name}
                      description={
                        <div>
                          <Text type="secondary">{product.brand?.name}</Text>
                          <div style={{ marginTop: 8 }}>
                            {product.sale_price ? (
                              <>
                                <Text delete style={{ marginRight: 8 }}>
                                  {formatPrice(product.price)}
                                </Text>
                                <Text strong style={{ color: '#fa8c16' }}>
                                  {formatPrice(product.sale_price)}
                                </Text>
                              </>
                            ) : (
                              <Text strong style={{ color: '#fa8c16' }}>
                                {formatPrice(product.price)}
                              </Text>
                            )}
                          </div>
                        </div>
                      }
                    />
                  </Card>
                </Link>
              </Col>
            ))}
          </Row>
        )}
      </div>
    </div>
  );
}
