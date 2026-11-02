import { Table, Button, Card, Typography, Space, Modal, Form, Input, Popconfirm, message } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../../api/axios';

const { Title } = Typography;

interface Brand {
  id: number;
  name: string;
  slug: string;
  description: string | null;
}

/** Payload gửi lên API khi tạo/cập nhật thương hiệu. */
interface BrandPayload {
  name: string;
  slug: string;
  description?: string | null;
}

export default function AdminBrands() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);
  const [form] = Form.useForm();
  
  const { data: brands, isLoading } = useQuery({
    queryKey: ['brands'],
    queryFn: async () => {
      const res = await api.get('/api/brands');
      return res.data.data as Brand[];
    },
  });
  
  const createMutation = useMutation({
    mutationFn: async (values: BrandPayload) => {
      const res = await api.post('/api/brands', values);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      message.success('Tạo thương hiệu thành công!');
      handleCloseModal();
    },
  });
  
  const updateMutation = useMutation({
    mutationFn: async ({ id, ...values }: BrandPayload & { id: number }) => {
      const res = await api.patch(`/api/brands/${id}`, values);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      message.success('Cập nhật thành công!');
      handleCloseModal();
    },
  });
  
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/brands/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      message.success('Xóa thương hiệu thành công!');
    },
  });
  
  const handleOpenModal = (brand?: Brand) => {
    if (brand) {
      setEditingBrand(brand);
      form.setFieldsValue(brand);
    } else {
      setEditingBrand(null);
      form.resetFields();
    }
    setIsModalOpen(true);
  };
  
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingBrand(null);
    form.resetFields();
  };
  
  const handleSubmit = (values: BrandPayload) => {
    if (editingBrand) {
      updateMutation.mutate({ id: editingBrand.id, ...values });
    } else {
      createMutation.mutate(values);
    }
  };
  
  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Tên thương hiệu', dataIndex: 'name' },
    { title: 'Slug', dataIndex: 'slug' },
    { title: 'Mô tả', dataIndex: 'description' },
    {
      title: '',
      render: (_: unknown, record: Brand) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleOpenModal(record)} />
          <Popconfirm title="Xóa thương hiệu này?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}>Quản lý thương hiệu</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
          Thêm thương hiệu
        </Button>
      </div>
      
      <Card>
        <Table dataSource={brands} columns={columns} rowKey="id" loading={isLoading} />
      </Card>
      
      <Modal
        title={editingBrand ? 'Sửa thương hiệu' : 'Thêm thương hiệu mới'}
        open={isModalOpen}
        onCancel={handleCloseModal}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Tên thương hiệu" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Mô tả">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingBrand ? 'Cập nhật' : 'Tạo mới'}
              </Button>
              <Button onClick={handleCloseModal}>Hủy</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
