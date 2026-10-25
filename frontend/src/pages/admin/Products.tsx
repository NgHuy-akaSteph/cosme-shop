import { Table, Button, Card, Typography, Space, Tag, Popconfirm, Modal, Form, Input, InputNumber, message } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../../api/axios';

const { Title, Text } = Typography;

interface Product {
  id: number;
  name: string;
  price: number;
  sale_price: number | null;
  stock: number;
  is_active: boolean;
  category: { name: string } | null;
  brand: { name: string } | null;
}

function formatPrice(price: number): string {
  return new Intl.NumberFormat('vi-VN').format(price) + ' đ';
}

export default function AdminProducts() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [form] = Form.useForm();
  
  const { data: products, isLoading } = useQuery({
    queryKey: ['admin', 'products'],
    queryFn: async () => {
      const res = await api.get('/api/products?size=100');
      return res.data.data as Product[];
    },
  });
  
  const createMutation = useMutation({
    mutationFn: async (values: any) => {
      const res = await api.post('/api/products', values);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'products'] });
      message.success('Tạo sản phẩm thành công!');
      handleCloseModal();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Có lỗi xảy ra');
    },
  });
  
  const updateMutation = useMutation({
    mutationFn: async ({ id, ...values }: any) => {
      const res = await api.patch(`/api/products/${id}`, values);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'products'] });
      message.success('Cập nhật thành công!');
      handleCloseModal();
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Có lỗi xảy ra');
    },
  });
  
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/products/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'products'] });
      message.success('Xóa sản phẩm thành công!');
    },
  });
  
  const handleOpenModal = (product?: Product) => {
    if (product) {
      setEditingProduct(product);
      form.setFieldsValue(product);
    } else {
      setEditingProduct(null);
      form.resetFields();
    }
    setIsModalOpen(true);
  };
  
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingProduct(null);
    form.resetFields();
  };
  
  const handleSubmit = (values: any) => {
    if (editingProduct) {
      updateMutation.mutate({ id: editingProduct.id, ...values });
    } else {
      createMutation.mutate(values);
    }
  };
  
  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Tên sản phẩm', dataIndex: 'name' },
    { title: 'Danh mục', dataIndex: ['category', 'name'] },
    { title: 'Thương hiệu', dataIndex: ['brand', 'name'] },
    {
      title: 'Giá',
      dataIndex: 'price',
      render: (price: number, record: Product) => (
        record.sale_price ? (
          <>
            <Text delete>{formatPrice(price)}</Text>
            <br />
            <Text strong style={{ color: '#fa8c16' }}>{formatPrice(record.sale_price)}</Text>
          </>
        ) : (
          <Text strong>{formatPrice(price)}</Text>
        )
      ),
    },
    { title: 'Stock', dataIndex: 'stock' },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? 'Hoạt động' : 'Ẩn'}
        </Tag>
      ),
    },
    {
      title: '',
      render: (_: any, record: Product) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          />
          <Popconfirm
            title="Xóa sản phẩm này?"
            onConfirm={() => deleteMutation.mutate(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}>Quản lý sản phẩm</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
          Thêm sản phẩm
        </Button>
      </div>
      
      <Card>
        <Table
          dataSource={products}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 20 }}
        />
      </Card>
      
      <Modal
        title={editingProduct ? 'Sửa sản phẩm' : 'Thêm sản phẩm mới'}
        open={isModalOpen}
        onCancel={handleCloseModal}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Tên sản phẩm" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          
          <Space style={{ width: '100%' }}>
            <Form.Item name="price" label="Giá" rules={[{ required: true }]} style={{ flex: 1 }}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            
            <Form.Item name="sale_price" label="Giá khuyến mãi" style={{ flex: 1 }}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          
          <Space style={{ width: '100%' }}>
            <Form.Item name="stock" label="Stock" rules={[{ required: true }]} style={{ flex: 1 }}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            
            <Form.Item name="category_id" label="Danh mục" rules={[{ required: true }]} style={{ flex: 1 }}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            
            <Form.Item name="brand_id" label="Thương hiệu" rules={[{ required: true }]} style={{ flex: 1 }}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          
          <Form.Item name="description" label="Mô tả">
            <Input.TextArea rows={3} />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={createMutation.isPending || updateMutation.isPending}>
                {editingProduct ? 'Cập nhật' : 'Tạo mới'}
              </Button>
              <Button onClick={handleCloseModal}>Hủy</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
