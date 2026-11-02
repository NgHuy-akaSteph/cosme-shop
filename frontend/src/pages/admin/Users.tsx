import { Table, Card, Typography, Tag, Switch, App } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import api from '../../api/axios';

const { Title } = Typography;

interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface UserListResponse {
  data: User[];
  total: number;
  page: number;
  size: number;
}

const PAGE_SIZE = 20;

export default function AdminUsers() {
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [page, setPage] = useState(1);

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['admin', 'users', page],
    queryFn: async () => {
      const res = await api.get(`/api/admin/users?page=${page}&size=${PAGE_SIZE}`);
      return res.data as UserListResponse;
    },
  });

  const users = usersData?.data ?? [];

  const toggleMutation = useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) => {
      const res = await api.patch(`/api/admin/users/${id}/toggle-active`, null, {
        params: { is_active },
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      message.success('Cập nhật trạng thái thành công!');
    },
  });

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Email', dataIndex: 'email' },
    { title: 'Họ tên', dataIndex: 'full_name' },
    { title: 'SĐT', dataIndex: 'phone' },
    {
      title: 'Vai trò',
      dataIndex: 'role',
      render: (role: string) => (
        <Tag color={role === 'admin' ? 'red' : 'blue'}>
          {role === 'admin' ? 'Admin' : 'User'}
        </Tag>
      ),
    },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      render: (active: boolean, record: User) => (
        <Switch
          checked={active}
          onChange={(checked) =>
            toggleMutation.mutate({ id: record.id, is_active: checked })
          }
          checkedChildren="Active"
          unCheckedChildren="Locked"
        />
      ),
    },
    { title: 'Ngày tạo', dataIndex: 'created_at' },
  ];

  return (
    <div>
      <Title level={2}>Quản lý người dùng</Title>

      <Card>
        <Table
          dataSource={users}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total: usersData?.total ?? 0,
            showSizeChanger: false,
            onChange: setPage,
          }}
        />
      </Card>
    </div>
  );
}
