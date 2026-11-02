import { Card, Table, Button, Empty, Typography, Popconfirm } from 'antd';
import { DeleteOutlined, ShoppingOutlined, HeartOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../api/axios';
import { colors } from '../../theme';

const { Title, Text } = Typography;

interface WishlistItem {
  id: number;
  product_id: number;
  product: {
    id: number;
    name: string;
    price: number;
    sale_price: number | null;
    image_url: string | null;
    image_urls?: { card: string; detail: string; thumb: string } | null;
    brand: { name: string } | null;
  };
}

function formatPrice(price: number): string {
  return new Intl.NumberFormat('vi-VN').format(price) + ' đ';
}

export default function WishlistPage() {
  const queryClient = useQueryClient();
  
  const { data: wishlist } = useQuery({
    queryKey: ['wishlist'],
    queryFn: async () => {
      const res = await api.get('/api/wishlist');
      return res.data.data as WishlistItem[];
    },
  });
  
  const removeMutation = useMutation({
    mutationFn: async (productId: number) => {
      await api.delete(`/api/wishlist/${productId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wishlist'] });
    },
  });
  
  const columns = [
    {
      title: 'Sản phẩm',
      render: (_: unknown, record: WishlistItem) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {(record.product.image_urls?.thumb || record.product.image_url) && (
            <img
              src={record.product.image_urls?.thumb ?? record.product.image_url ?? ''}
              alt={record.product.name}
              style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 4 }}
            />
          )}
          <div>
            <Link to={`/products/${record.product.id}`}>
              <Text strong>{record.product.name}</Text>
            </Link>
            <Text type="secondary" style={{ display: 'block' }}>
              {record.product.brand?.name}
            </Text>
          </div>
        </div>
      ),
    },
    {
      title: 'Giá',
      render: (_: unknown, record: WishlistItem) => (
        record.product.sale_price ? (
          <>
            <Text delete style={{ marginRight: 8 }}>{formatPrice(record.product.price)}</Text>
            <Text strong style={{ color: colors.primary }}>{formatPrice(record.product.sale_price)}</Text>
          </>
        ) : (
          <Text strong style={{ color: colors.primary }}>{formatPrice(record.product.price)}</Text>
        )
      ),
    },
    {
      title: '',
      render: (_: unknown, record: WishlistItem) => (
        <Popconfirm
          title="Xóa khỏi wishlist?"
          onConfirm={() => removeMutation.mutate(record.product_id)}
          okText="Xóa"
          cancelText="Hủy"
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];
  
  if (!wishlist || wishlist.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <Empty
          image={<HeartOutlined style={{ fontSize: 64, color: colors.iconMuted }} />}
          description="Chưa có sản phẩm yêu thích"
        >
          <Link to="/products">
            <Button type="primary" icon={<ShoppingOutlined />}>
              Khám phá sản phẩm
            </Button>
          </Link>
        </Empty>
      </div>
    );
  }
  
  return (
    <div>
      <Title level={2}>Sản phẩm yêu thích</Title>
      
      <Card>
        <Table
          dataSource={wishlist}
          columns={columns}
          rowKey="id"
          pagination={false}
        />
      </Card>
    </div>
  );
}
