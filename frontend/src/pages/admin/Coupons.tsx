import {
  Table,
  Button,
  Card,
  Typography,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  DatePicker,
  Popconfirm,
  App,
  Tag,
} from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs, { type Dayjs } from 'dayjs';
import api from '../../api/axios';
import AdminSearchBox from '../../components/admin/AdminSearchBox';
import { buildSimpleSequenceColumn } from '../../components/admin/sequence-column';

const { Title } = Typography;

interface Coupon {
  id: number;
  code: string;
  discount_type: 'percent' | 'fixed';
  discount_value: number;
  min_order_amount: number;
  max_discount: number | null;
  max_uses: number | null;
  used_count: number;
  expires_at: string | null;
  is_active: boolean;
  description: string | null;
}

interface CouponPayload {
  code?: string;
  discount_type: 'percent' | 'fixed';
  discount_value: number;
  min_order_amount: number;
  max_discount: number | null;
  max_uses: number | null;
  expires_at: string | null;
  is_active: boolean;
  description: string | null;
}

/** Form chi co `expires_at` la DatePicker -> chuyen sang chuoi ISO. */
interface CouponFormValues extends Omit<CouponPayload, 'expires_at'> {
  expires_at?: Dayjs | null;
}

const DISCOUNT_TYPE_OPTIONS = [
  { value: 'percent', label: 'Phần trăm (%)' },
  { value: 'fixed', label: 'Số tiền cố định (đ)' },
];

export default function AdminCoupons() {
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState<Coupon | null>(null);
  const [search, setSearch] = useState('');
  const [form] = Form.useForm<CouponFormValues>();
  const discountType = Form.useWatch('discount_type', form);

  const { data: coupons, isLoading } = useQuery({
    queryKey: ['admin-coupons'],
    queryFn: async () => {
      const res = await api.get('/api/admin/coupons');
      return res.data.data as Coupon[];
    },
  });

  // Loc client-side: danh sach ma giam gia nho, khong can round-trip server.
  // Tieu chi CHINH la ten/mo ta chien dich (`description`); `code` la truong phu.
  const filteredCoupons = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return coupons ?? [];
    return (coupons ?? []).filter(
      (c) =>
        (c.description ?? '').toLowerCase().includes(keyword) ||
        c.code.toLowerCase().includes(keyword),
    );
  }, [coupons, search]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['admin-coupons'] });

  const createMutation = useMutation({
    mutationFn: async (values: CouponPayload) => {
      const res = await api.post('/api/admin/coupons', values);
      return res.data;
    },
    onSuccess: () => {
      invalidate();
      message.success('Tạo mã giảm giá thành công!');
      handleCloseModal();
    },
    onError: (error) => {
      message.error(extractError(error));
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...values }: CouponPayload & { id: number }) => {
      const res = await api.patch(`/api/admin/coupons/${id}`, values);
      return res.data;
    },
    onSuccess: () => {
      invalidate();
      message.success('Cập nhật thành công!');
      handleCloseModal();
    },
    onError: (error) => {
      message.error(extractError(error));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/admin/coupons/${id}`);
    },
    onSuccess: () => {
      invalidate();
      message.success('Xóa mã giảm giá thành công!');
    },
    onError: (error) => {
      message.error(extractError(error));
    },
  });

  const handleOpenModal = (coupon?: Coupon) => {
    if (coupon) {
      setEditingCoupon(coupon);
      form.setFieldsValue({
        ...coupon,
        expires_at: coupon.expires_at ? dayjs(coupon.expires_at) : null,
      });
    } else {
      setEditingCoupon(null);
      form.resetFields();
      form.setFieldsValue({ discount_type: 'percent', is_active: true });
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingCoupon(null);
    form.resetFields();
  };

  const handleSubmit = (values: CouponFormValues) => {
    const payload: CouponPayload = {
      ...values,
      expires_at: values.expires_at ? values.expires_at.toISOString() : null,
    };

    if (editingCoupon) {
      // Code khong doi duoc khi update - bo field de tranh conflict DB.
      delete payload.code;
      updateMutation.mutate({ id: editingCoupon.id, ...payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const columns = [
    buildSimpleSequenceColumn<Coupon>(),
    { title: 'Mã', dataIndex: 'code', width: 160 },
    {
      title: 'Giảm',
      width: 160,
      render: (_: unknown, record: Coupon) =>
        record.discount_type === 'percent'
          ? `${record.discount_value}%`
          : `${record.discount_value.toLocaleString('vi-VN')} đ`,
    },
    {
      title: 'Đơn tối thiểu',
      dataIndex: 'min_order_amount',
      width: 140,
      render: (v: number) => (v > 0 ? `${v.toLocaleString('vi-VN')} đ` : '—'),
    },
    {
      title: 'Trần giảm',
      dataIndex: 'max_discount',
      width: 120,
      render: (v: number | null) => (v ? `${v.toLocaleString('vi-VN')} đ` : '—'),
    },
    {
      title: 'Đã dùng',
      width: 120,
      render: (_: unknown, record: Coupon) =>
        record.max_uses ? `${record.used_count}/${record.max_uses}` : `${record.used_count}/∞`,
    },
    {
      title: 'Hết hạn',
      dataIndex: 'expires_at',
      width: 160,
      render: (v: string | null) =>
        v ? dayjs(v).format('DD/MM/YYYY') : <Tag color="default">Không</Tag>,
    },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      width: 100,
      render: (v: boolean) =>
        v ? <Tag color="success">Đang chạy</Tag> : <Tag color="default">Tắt</Tag>,
    },
    {
      title: '',
      width: 100,
      render: (_: unknown, record: Coupon) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleOpenModal(record)} />
          <Popconfirm title="Xóa mã giảm giá này?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}>Quản lý mã giảm giá</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
          Thêm mã giảm giá
        </Button>
      </div>

      <Card>
        <AdminSearchBox
          value={search}
          onChange={setSearch}
          placeholder="Tìm theo tên hoặc mã chiến dịch"
        />
        <Table
          dataSource={filteredCoupons}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          locale={{ emptyText: 'Không tìm thấy mã giảm giá phù hợp' }}
        />
      </Card>

      <Modal
        title={editingCoupon ? 'Sửa mã giảm giá' : 'Thêm mã giảm giá mới'}
        open={isModalOpen}
        onCancel={handleCloseModal}
        footer={null}
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="code"
            label="Mã giảm giá"
            rules={[{ required: true, message: 'Vui lòng nhập mã!' }]}
            extra="Chỉ chữ, số, gạch dưới và gạch ngang. Không thể đổi sau khi tạo."
          >
            <Input disabled={!!editingCoupon} placeholder="WELCOME10" />
          </Form.Item>

          <Space.Compact style={{ width: '100%' }}>
            <Form.Item
              name="discount_type"
              label="Loại giảm"
              rules={[{ required: true }]}
              style={{ flex: 1 }}
            >
              <Select options={DISCOUNT_TYPE_OPTIONS} />
            </Form.Item>
            <Form.Item
              name="discount_value"
              label="Mức giảm"
              rules={[{ required: true }]}
              style={{ flex: 1 }}
            >
              <InputNumber
                min={1}
                max={discountType === 'percent' ? 100 : undefined}
                style={{ width: '100%' }}
                suffix={discountType === 'percent' ? '%' : 'đ'}
              />
            </Form.Item>
          </Space.Compact>

          <Form.Item
            name="min_order_amount"
            label="Đơn hàng tối thiểu (đ)"
            extra="0 = không giới hạn"
          >
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>

          {discountType === 'percent' && (
            <Form.Item
              name="max_discount"
              label="Trần giảm tối đa (đ)"
              extra="Để trống = không giới hạn. VD: mã 20% nhưng chỉ giảm tối đa 50.000 đ."
            >
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          )}

          <Form.Item name="max_uses" label="Số lần tối đa được dùng" extra="Để trống = không giới hạn">
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="expires_at" label="Ngày hết hạn" extra="Để trống = không hết hạn">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="is_active" label="Đang hoạt động" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="description" label="Mô tả">
            <Input.TextArea rows={2} placeholder="VD: Chiến dịnh chào mừng khách hàng mới" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={createMutation.isPending || updateMutation.isPending}>
                {editingCoupon ? 'Cập nhật' : 'Tạo mới'}
              </Button>
              <Button onClick={handleCloseModal}>Hủy</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

/** Lay thong bao loi tu API (detail dang object {message, code}). */
function extractError(error: unknown): string {
  const err = error as {
    response?: { data?: { detail?: string | { message?: string } } };
  };
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (detail && typeof detail === 'object' && detail.message) return detail.message;
  return 'Thao tác thất bại';
}
