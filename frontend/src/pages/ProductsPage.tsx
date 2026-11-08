import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Row, Col, Typography, Spin, Input, Select, Empty, Pagination, Checkbox, Divider, Button, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import api from '../api/axios';
import ProductCard from '../components/ProductCard';
import { useProducts } from '../hooks/useProducts';
import { useAddToCartFromCard } from '../hooks/useAddToCartFromCard';
import { CONCERNS, PRICE_RANGES, SKIN_TYPES, SORT_OPTIONS } from '../utils/constants';
import { colors } from '../theme';

const { Title, Text } = Typography;
const { Search } = Input;

const PAGE_SIZE = 20;

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

  const page = Number(searchParams.get('page')) || 1;
  const search = searchParams.get('search') || '';
  const categoryId = searchParams.get('category_id') ? Number(searchParams.get('category_id')) : null;
  const brandId = searchParams.get('brand_id') ? Number(searchParams.get('brand_id')) : null;
  const sort = searchParams.get('sort') || 'newest';
  const skinTypes = searchParams.get('skin_types')?.split(',').filter(Boolean) ?? [];
  const concerns = searchParams.get('concerns')?.split(',').filter(Boolean) ?? [];
  const priceRange = searchParams.get('price_range') ?? '';
  const pricePreset = PRICE_RANGES.find((r) => r.value === priceRange);

  const { data: productsData, isLoading } = useProducts({
    page,
    size: PAGE_SIZE,
    category_id: categoryId,
    brand_id: brandId,
    search,
    sort,
    skin_types: skinTypes,
    concerns,
    min_price: pricePreset?.min ?? null,
    max_price: pricePreset?.max ?? null,
  });

  const handleAddToCart = useAddToCartFromCard();

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

  const updateParams = (mutate: (params: URLSearchParams) => void) => {
    const params = new URLSearchParams(searchParams);
    mutate(params);
    params.set('page', '1');
    setSearchParams(params);
  };

  const handleSearch = (value: string) => {
    updateParams((params) => {
      if (value) params.set('search', value);
      else params.delete('search');
    });
  };

  const handleFilter = (key: string, value: number | null) => {
    updateParams((params) => {
      if (value) params.set(key, String(value));
      else params.delete(key);
    });
  };

  const handlePriceRange = (value: string | undefined) => {
    updateParams((params) => {
      if (value) params.set('price_range', value);
      else params.delete('price_range');
    });
  };

  const handleSortChange = (value: string) => {
    updateParams((params) => params.set('sort', value));
  };

  const handlePageChange = (p: number) => {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(p));
    setSearchParams(params);
  };

  const clearAllFilters = () => {
    const params = new URLSearchParams();
    params.set('page', '1');
    if (sort) params.set('sort', sort);
    setSearchParams(params);
  };

  const hasActiveFilter =
    Boolean(search) ||
    Boolean(categoryId) ||
    Boolean(brandId) ||
    skinTypes.length > 0 ||
    concerns.length > 0 ||
    Boolean(priceRange);

  const products = productsData?.data ?? [];

  return (
    <div>
      <Title level={2}>Sản phẩm</Title>

      <Row gutter={[24, 24]}>
        {/* Sidebar filter */}
        <Col xs={24} lg={6}>
          <div style={{ position: 'sticky', top: 92 }}>
            <Divider orientation="left" plain>
              Bộ lọc
            </Divider>

            <Space direction="vertical" size={20} style={{ width: '100%' }}>
              <div>
                <Text strong>Tìm kiếm</Text>
                <Search
                  placeholder="Tên sản phẩm..."
                  allowClear
                  style={{ width: '100%', marginTop: 8 }}
                  prefix={<SearchOutlined />}
                  onSearch={handleSearch}
                  defaultValue={search}
                />
              </div>

              <div>
                <Text strong>Danh mục</Text>
                <Select
                  placeholder="Tất cả danh mục"
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  style={{ width: '100%', marginTop: 8 }}
                  value={categoryId}
                  onChange={(v) => handleFilter('category_id', v ?? null)}
                  options={categories?.map((c) => ({ value: c.id, label: c.name }))}
                />
              </div>

              <div>
                <Text strong>Thương hiệu</Text>
                <Select
                  placeholder="Tất cả thương hiệu"
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  style={{ width: '100%', marginTop: 8 }}
                  value={brandId}
                  onChange={(v) => handleFilter('brand_id', v ?? null)}
                  options={brands?.map((b) => ({ value: b.id, label: b.name }))}
                />
              </div>

              <div>
                <Text strong>Loại da</Text>
                <Checkbox.Group
                  style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}
                  value={skinTypes}
                  onChange={(values) =>
                    updateParams((params) => {
                      if (values.length) params.set('skin_types', values.join(','));
                      else params.delete('skin_types');
                    })
                  }
                  options={SKIN_TYPES}
                />
              </div>

              <div>
                <Text strong>Vấn đề da</Text>
                <Checkbox.Group
                  style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}
                  value={concerns}
                  onChange={(values) =>
                    updateParams((params) => {
                      if (values.length) params.set('concerns', values.join(','));
                      else params.delete('concerns');
                    })
                  }
                  options={CONCERNS}
                />
              </div>

              <div>
                <Text strong>Khoảng giá</Text>
                <Select
                  placeholder="Tất cả khoảng giá"
                  allowClear
                  style={{ width: '100%', marginTop: 8 }}
                  value={priceRange || undefined}
                  onChange={handlePriceRange}
                  options={PRICE_RANGES.map((r) => ({ value: r.value, label: r.label }))}
                />
              </div>

              {hasActiveFilter && (
                <Button block onClick={clearAllFilters} style={{ color: colors.primary }}>
                  Xoá tất cả bộ lọc
                </Button>
              )}
            </Space>
          </div>
        </Col>

        {/* Product grid */}
        <Col xs={24} lg={18}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 16,
              flexWrap: 'wrap',
              gap: 12,
            }}
          >
            <Text type="secondary">{productsData?.total ?? 0} sản phẩm</Text>
            <Select
              style={{ width: 200 }}
              value={sort}
              onChange={handleSortChange}
              options={SORT_OPTIONS}
            />
          </div>

          {isLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin size="large" />
            </div>
          ) : products.length > 0 ? (
            <>
              <Row gutter={[16, 16]}>
                {products.map((product) => (
                  <Col key={product.id} xs={12} sm={8} md={8} lg={6}>
                    <ProductCard product={product} onAddToCart={handleAddToCart} />
                  </Col>
                ))}
              </Row>

              <div style={{ marginTop: 32, textAlign: 'center' }}>
                <Pagination
                  current={page}
                  total={productsData?.total ?? 0}
                  pageSize={PAGE_SIZE}
                  onChange={handlePageChange}
                  showSizeChanger={false}
                  showTotal={(total) => `Tổng ${total} sản phẩm`}
                />
              </div>
            </>
          ) : (
            <Empty description="Không tìm thấy sản phẩm" style={{ padding: 60 }} />
          )}
        </Col>
      </Row>
    </div>
  );
}
