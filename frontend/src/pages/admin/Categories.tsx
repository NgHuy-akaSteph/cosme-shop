import { Table, Button, Card, Typography, Space, Modal, Form, Input, Popconfirm, App } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../../api/axios';
import AdminSearchBox from '../../components/admin/AdminSearchBox';
import { buildSimpleSequenceColumn } from '../../components/admin/sequence-column';

const { Title } = Typography;

interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
}

/** Payload gửi lên API khi tạo/cập nhật danh mục. */
interface CategoryPayload {
  name: string;
  slug: string;
  description?: string | null;
}

export default function AdminCategories() {
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [search, setSearch] = useState('');
  const [form] = Form.useForm();

  // QueryKey rieng cho admin (khong dung chung `['categories']` voi public)
  // vi du lieu sap xep khac nhau.
  const { data: categories, isLoading } = useQuery({
    queryKey: ['admin', 'categories'],
    queryFn: async () => {
      const res = await api.get('/api/categories?sort=newest&size=200');
      return res.data.data as Category[];
    },
  });

  // Loc client-side: danh muc it, khong can round-trip server.
  const filteredCategories = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return categories ?? [];
    return (categories ?? []).filter(
      (c) =>
        c.name.toLowerCase().includes(keyword) ||
        c.slug.toLowerCase().includes(keyword),
    );
  }, [categories, search]);

  /** Invalidate ca cache public (trang chu) va cache admin. */
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'categories'] });
    queryClient.invalidateQueries({ queryKey: ['categories'] });
  };

  const createMutation = useMutation({
    mutationFn: async (values: CategoryPayload) => {
      const res = await api.post('/api/categories', values);
      return res.data;
    },
    onSuccess: () => {
      invalidate();
      message.success('Tạo danh mục thành công!');
      handleCloseModal();
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...values }: CategoryPayload & { id: number }) => {
      const res = await api.patch(`/api/categories/${id}`, values);
      return res.data;
    },
    onSuccess: () => {
      invalidate();
      message.success('Cập nhật thành công!');
      handleCloseModal();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/categories/${id}`);
    },
    onSuccess: () => {
      invalidate();
      message.success('Xóa danh mục thành công!');
    },
  });
  
  const handleOpenModal = (category?: Category) => {
    if (category) {
      setEditingCategory(category);
      form.setFieldsValue(category);
    } else {
      setEditingCategory(null);
      form.resetFields();
    }
    setIsModalOpen(true);
  };
  
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingCategory(null);
    form.resetFields();
  };
  
  const handleSubmit = (values: CategoryPayload) => {
    if (editingCategory) {
      updateMutation.mutate({ id: editingCategory.id, ...values });
    } else {
      createMutation.mutate(values);
    }
  };
  
  const columns = [
    buildSimpleSequenceColumn<Category>(),
    { title: 'Tên danh mục', dataIndex: 'name' },
    { title: 'Slug', dataIndex: 'slug' },
    { title: 'Mô tả', dataIndex: 'description' },
    {
      title: '',
      render: (_: unknown, record: Category) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleOpenModal(record)} />
          <Popconfirm title="Xóa danh mục này?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}>Quản lý danh mục</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
          Thêm danh mục
        </Button>
      </div>
      
      <Card>
        <AdminSearchBox
          value={search}
          onChange={setSearch}
          placeholder="Tìm theo tên danh mục"
        />
        <Table
          dataSource={filteredCategories}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          locale={{ emptyText: 'Không tìm thấy danh mục phù hợp' }}
        />
      </Card>
      
      <Modal
        title={editingCategory ? 'Sửa danh mục' : 'Thêm danh mục mới'}
        open={isModalOpen}
        onCancel={handleCloseModal}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Tên danh mục" rules={[{ required: true }]}>
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
                {editingCategory ? 'Cập nhật' : 'Tạo mới'}
              </Button>
              <Button onClick={handleCloseModal}>Hủy</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
