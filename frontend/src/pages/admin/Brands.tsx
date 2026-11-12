import { Table, Button, Card, Typography, Space, Modal, Form, Input, Popconfirm, App } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../../api/axios';
import AdminSearchBox from '../../components/admin/AdminSearchBox';
import { buildSimpleSequenceColumn } from '../../components/admin/sequence-column';

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
  const { message } = App.useApp();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);
  const [search, setSearch] = useState('');
  const [form] = Form.useForm();

  // QueryKey rieng cho admin (khong dung chung `['brands']` voi public)
  // vi du lieu sap xep khac nhau.
  const { data: brands, isLoading } = useQuery({
    queryKey: ['admin', 'brands'],
    queryFn: async () => {
      const res = await api.get('/api/brands?sort=newest&size=200');
      return res.data.data as Brand[];
    },
  });

  // Loc client-side: thuong hieu it, khong can round-trip server.
  const filteredBrands = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return brands ?? [];
    return (brands ?? []).filter(
      (b) =>
        b.name.toLowerCase().includes(keyword) ||
        b.slug.toLowerCase().includes(keyword),
    );
  }, [brands, search]);

  /** Invalidate ca cache public (trang chu) va cache admin. */
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'brands'] });
    queryClient.invalidateQueries({ queryKey: ['brands'] });
  };

  const createMutation = useMutation({
    mutationFn: async (values: BrandPayload) => {
      const res = await api.post('/api/brands', values);
      return res.data;
    },
    onSuccess: () => {
      invalidate();
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
      invalidate();
      message.success('Cập nhật thành công!');
      handleCloseModal();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/brands/${id}`);
    },
    onSuccess: () => {
      invalidate();
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
    buildSimpleSequenceColumn<Brand>(),
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
        <AdminSearchBox
          value={search}
          onChange={setSearch}
          placeholder="Tìm theo tên thương hiệu"
        />
        <Table
          dataSource={filteredBrands}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          locale={{ emptyText: 'Không tìm thấy thương hiệu phù hợp' }}
        />
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
