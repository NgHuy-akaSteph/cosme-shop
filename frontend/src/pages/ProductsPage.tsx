import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { Card, Row, Col, Typography, Spin, Input, Select, Space, Empty, Pagination } from 'antd';
import { ShoppingOutlined, SearchOutlined } from '@ant-design/icons';
import api from '../api/axios';
import { formatPrice } from '../utils/constants';

const { Title, Text } = Typography;
const { Search } = Input;

interface Product {
  id: number;
  name: string;
  slug: string;
  price: number;
  sale_price: number | null;
  image_url: string | null;
  brand: { name: string } | null;
  category: { name: string } | null;
}

interface Category {
  id: number;
  name: string;
}

interface Brand {
  id: number;
  name: string;
}

export default function ProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const pageSize = 20;
  
  const page = Number(searchParams.get('page')) || 1;
  const search = searchParams.get('search') || '';
  const categoryId = searchParams.get('category_id') ? Number(searchParams.get('category_id')) : null;
  const brandId = searchParams.get('brand_id') ? Number(searchParams.get('brand_id')) : null;
  const sort = searchParams.get('sort') || 'newest';
  
  const { data: productsData, isLoading } = useQuery({
    queryKey: ['products', { page, categoryId, brandId, search, sort, pageSize }],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', String(page));
      params.append('size', String(pageSize));
      if (categoryId) params.append('category_id', String(categoryId));
      if (brandId) params.append('brand_id', String(brandId));
      if (search) params.append('search', search);
      if (sort) params.append('sort', sort);
      
      const res = await api.get(`/api/products?${params}`);
      return res.data;
    },
  });
  
  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const res = await api.get('/api/categories');
      return res.data.data as Category[];
    },
  });
  
  const { data: brands } = useQuery({
    queryKey: ['brands'],
    queryFn: async () => {
      const res = await api.get('/api/brands');
      return res.data.data as Brand[];
    },
  });
  
  const handleSearch = (value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set('search', value);
    } else {
      params.delete('search');
    }
    params.set('page', '1'); // Reset to page 1
    setSearchParams(params);
  };
  
  const handleFilter = (key: string, value: number | null) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set(key, String(value));
    } else {
      params.delete(key);
    }
    params.set('page', '1'); // Reset to page 1
    setSearchParams(params);
  };
  
  const handleSortChange = (value: string) => {
    const params = new URLSearchParams(searchParams);
    params.set('sort', value);
    params.set('page', '1');
    setSearchParams(params);
  };
  
  const handlePageChange = (p: number) => {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(p));
    setSearchParams(params);
  };
  
  return (
    <div>
      <Title level={2}>Sản phẩm</Title>
      
      {/* Filters */}
      <Space wrap style={{ marginBottom: 24 }}>
        <Search
          placeholder="Tìm kiếm sản phẩm..."
          allowClear
          style={{ width: 300 }}
          prefix={<SearchOutlined />}
          onSearch={handleSearch}
          defaultValue={search}
        />
        
        <Select
          placeholder="Danh mục"
          allowClear
          style={{ width: 150 }}
          value={categoryId}
          onChange={(v) => handleFilter('category_id', v || null)}
          options={categories?.map((c) => ({ value: c.id, label: c.name }))}
        />
        
        <Select
          placeholder="Thương hiệu"
          allowClear
          style={{ width: 150 }}
          value={brandId}
          onChange={(v) => handleFilter('brand_id', v || null)}
          options={brands?.map((b) => ({ value: b.id, label: b.name }))}
        />
        
        <Select
          style={{ width: 150 }}
          value={sort}
          onChange={handleSortChange}
          options={[
            { value: 'newest', label: 'Mới nhất' },
            { value: 'best_seller', label: 'Bán chạy' },
            { value: 'price_asc', label: 'Giá: Thấp đến cao' },
            { value: 'price_desc', label: 'Giá: Cao đến thấp' },
          ]}
        />
      </Space>
      
      {/* Products Grid */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : productsData?.data && productsData.data.length > 0 ? (
        <>
          <Text type="secondary">{productsData?.total || 0} sản phẩm</Text>
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            {productsData.data.map((product: Product) => (
              <Col key={product.id} xs={24} sm={12} md={8} lg={6}>
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
                          <Text type="secondary">{product.brand?.name} - {product.category?.name}</Text>
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
          
          <div style={{ marginTop: 32, textAlign: 'center' }}>
            <Pagination
              current={page}
              total={productsData.total || 0}
              pageSize={pageSize}
              onChange={handlePageChange}
              showSizeChanger={false}
              showTotal={(total) => `Tổng ${total} sản phẩm`}
            />
          </div>
        </>
      ) : (
        <Empty description="Không tìm thấy sản phẩm" style={{ padding: 60 }} />
      )}
    </div>
  );
}
