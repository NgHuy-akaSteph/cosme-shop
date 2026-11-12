import { Table, Card, Typography, Tag, Select, Button, Descriptions, Modal, Input, Table as AntTable } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import api from '../../api/axios';
import { formatPrice, statusColors, statusText } from '../../utils/constants';
import type { ApiError } from '../../types/api';
import { getErrorMessage } from '../../types/api';
import AdminSearchBox from '../../components/admin/AdminSearchBox';
import { buildSequenceColumn } from '../../components/admin/sequence-column';
import { App } from 'antd';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface OrderItem {
  id: number;
  product_name: string;
  product_price: string;
  qty: number;
  subtotal: string;
  variant_info: { id?: string; name?: string } | null;
}

interface Order {
  id: number;
  order_code: string;
  status: string;
  total: string;
  payment_method: string;
  payment_status: string;
  shipping_name: string;
  shipping_phone: string;
  shipping_address: string;
  created_at: string;
  user_id: number;
  items: OrderItem[];
}

interface OrderListResponse {
  data: Order[];
  total: number;
  page: number;
  size: number;
}

const statusOptions = [
  { value: 'pending', label: 'Chờ xác nhận' },
  { value: 'confirmed', label: 'Đã xác nhận' },
  { value: 'packing', label: 'Đang đóng gói' },
  { value: 'shipping', label: 'Đang giao' },
  { value: 'delivered', label: 'Đã giao' },
  { value: 'cancelled', label: 'Đã hủy' },
];

/** Bo loc trang thai: them "Tất cả" de xoa loc. */
const statusFilterOptions = [{ value: 'all', label: 'Tất cả' }, ...statusOptions];

/** May trang thai don hang: chi cho chuyen sang trang thai hop le. */
const NEXT_STATUS: Record<string, string[]> = {
  pending: ['confirmed', 'cancelled'],
  confirmed: ['packing', 'cancelled'],
  packing: ['shipping'],
  shipping: ['delivered'],
  delivered: [],
  cancelled: [],
};

const PAGE_SIZE = 20;

export default function AdminOrders() {
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  // `undefined` (khong phai `''`) de antd hien thi `placeholder` khi chua chon.
  const [newStatus, setNewStatus] = useState<string | undefined>(undefined);
  const [note, setNote] = useState('');

  // Tim kiem server-side: don hang phan trang o server nen client-side chi
  // loc duoc 20 don cua trang hien tai -> sai.
  const { data: ordersData, isLoading } = useQuery({
    queryKey: ['admin', 'orders', statusFilter, page, search],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', String(page));
      params.append('size', String(PAGE_SIZE));
      // `all` = khong loc, khong gui len server.
      if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);
      if (search.trim()) params.append('search', search.trim());

      const res = await api.get(`/api/admin/orders?${params}`);
      return res.data as OrderListResponse;
    },
  });

  const orders = ordersData?.data ?? [];

  /** Doi tu khoa tim kiem -> quay ve trang 1. */
  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status, note }: { id: number; status: string; note?: string }) => {
      const res = await api.patch(`/api/admin/orders/${id}/status`, { status, note });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'orders'] });
      message.success('Cập nhật trạng thái thành công!');
      setIsModalOpen(false);
      setSelectedOrder(null);
    },
    onError: (error: ApiError) => {
      message.error(getErrorMessage(error, 'Cập nhật trạng thái thất bại'));
    },
  });

  const handleUpdateStatus = () => {
    if (selectedOrder && newStatus) {
      updateStatusMutation.mutate({
        id: selectedOrder.id,
        status: newStatus,
        note: note || undefined,
      });
    }
  };

  const allowedStatusOptions = selectedOrder
    ? statusOptions.filter((o) => NEXT_STATUS[selectedOrder.status]?.includes(o.value))
    : [];

  const columns = [
    buildSequenceColumn<Order>(page, PAGE_SIZE),
    { title: 'Mã đơn', dataIndex: 'order_code' },
    {
      title: 'Ngày đặt',
      dataIndex: 'created_at',
      render: (d: string) => new Date(d).toLocaleDateString('vi-VN'),
    },
    { title: 'Khách hàng ID', dataIndex: 'user_id', width: 100 },
    {
      title: 'Tổng tiền',
      dataIndex: 'total',
      render: (t: string) => <Text strong>{formatPrice(t)}</Text>,
    },
    {
      title: 'Thanh toán',
      dataIndex: 'payment_method',
      render: (m: string) => m.toUpperCase(),
    },
    {
      title: 'TT Thanh toán',
      dataIndex: 'payment_status',
      render: (s: string) => (
        <Tag color={s === 'paid' ? 'green' : 'orange'}>
          {s === 'paid' ? 'Đã thanh toán' : 'Chưa thanh toán'}
        </Tag>
      ),
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      render: (s: string) => (
        <Tag color={statusColors[s] || 'default'}>{statusText[s] || s}</Tag>
      ),
    },
    {
      title: '',
      render: (_record: unknown, record: Order) => (
        <Button
          type="link"
          onClick={() => {
            setSelectedOrder(record);
            // Reset de trang thai moi (chua chon) - KHONG preset `record.status`.
            // `options` chi chua cac trang thai DEN, nen preset trang thai hien
            // tai se bi antd render bang MA tieng Anh ("pending") thay vi nhan
            // tieng Viet, gay hien thi "ca tieng Anh va tieng Viet".
            setNewStatus(undefined);
            setNote('');
            setIsModalOpen(true);
          }}
        >
          Cập nhật
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Title level={2}>Quản lý đơn hàng</Title>
      </div>

      <Card>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 16,
            marginBottom: 16,
          }}
        >
          <AdminSearchBox
            value={search}
            onChange={handleSearchChange}
            placeholder="Tìm theo mã đơn"
            loading={isLoading}
            style={{ marginBottom: 0 }}
          />
          <Select
            value={statusFilter}
            style={{ width: 200 }}
            onChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
            options={statusFilterOptions}
          />
        </div>
        <Table
          dataSource={orders}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total: ordersData?.total ?? 0,
            showSizeChanger: false,
            onChange: setPage,
          }}
          locale={{ emptyText: 'Không tìm thấy đơn hàng phù hợp' }}
        />
      </Card>

      <Modal
        title={`Cập nhật đơn ${selectedOrder?.order_code}`}
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        onOk={handleUpdateStatus}
        okButtonProps={{ disabled: !newStatus }}
        confirmLoading={updateStatusMutation.isPending}
      >
        {selectedOrder && (
          <>
            <Descriptions column={1} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Trạng thái hiện tại">
                <Tag color={statusColors[selectedOrder.status] || 'default'}>
                  {statusText[selectedOrder.status] || selectedOrder.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Khách hàng">
                {selectedOrder.shipping_name} - {selectedOrder.shipping_phone}
              </Descriptions.Item>
              <Descriptions.Item label="Địa chỉ">
                {selectedOrder.shipping_address}
              </Descriptions.Item>
              <Descriptions.Item label="Tổng tiền">
                {formatPrice(selectedOrder.total)}
              </Descriptions.Item>
            </Descriptions>

            <AntTable
              size="small"
              rowKey="id"
              pagination={false}
              style={{ marginBottom: 16 }}
              dataSource={selectedOrder.items ?? []}
              columns={[
                { title: 'Sản phẩm', dataIndex: 'product_name' },
                {
                  title: 'Phân loại',
                  dataIndex: 'variant_info',
                  render: (v: OrderItem['variant_info']) => v?.name ?? '-',
                },
                { title: 'SL', dataIndex: 'qty', width: 60 },
                {
                  title: 'Tổng',
                  dataIndex: 'subtotal',
                  render: (s: string) => formatPrice(s),
                },
              ]}
            />

            <div style={{ marginBottom: 16 }}>
              <label>Trạng thái mới:</label>
              <Select
                placeholder="Chọn trạng thái tiếp theo"
                value={newStatus}
                onChange={setNewStatus}
                options={allowedStatusOptions}
                style={{ width: '100%', marginTop: 8 }}
              />
            </div>

            <div>
              <label>Ghi chú:</label>
              <TextArea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={3}
                placeholder="VD: Đã lấy hàng tại kho HN"
                style={{ marginTop: 8 }}
              />
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
