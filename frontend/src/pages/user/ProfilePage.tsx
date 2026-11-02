import { Form, Input, Button, Card, Typography, App } from 'antd';
import { useMutation } from '@tanstack/react-query';
import { UserOutlined, MailOutlined, PhoneOutlined, LockOutlined } from '@ant-design/icons';
import api from '../../api/axios';
import type { ApiError } from '../../types/api';
import { getErrorMessage } from '../../types/api';
import { useAuthStore } from '../../store/authStore';

const { Title } = Typography;

/** Payload cập nhật profile. */
interface ProfilePayload {
  full_name: string;
  phone?: string;
  address?: string;
}

/** Payload đổi mật khẩu. */
interface ChangePasswordPayload {
  old_password: string;
  new_password: string;
}

export default function ProfilePage() {
  const { user, updateUser } = useAuthStore();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();

  const updateMutation = useMutation({
    mutationFn: async (values: ProfilePayload) => {
      const res = await api.patch('/api/auth/me', values);
      return res.data;
    },
    onSuccess: (data) => {
      updateUser(data.data);
      message.success('Cập nhật thành công!');
    },
    onError: (error: ApiError) => {
      message.error(getErrorMessage(error, 'Cập nhật thất bại'));
    },
  });
  
  const changePasswordMutation = useMutation({
    mutationFn: async (values: ChangePasswordPayload) => {
      await api.post('/api/auth/change-password', values);
    },
    onSuccess: () => {
      message.success('Đổi mật khẩu thành công!');
      passwordForm.resetFields();
    },
    onError: (error: ApiError) => {
      message.error(getErrorMessage(error, 'Đổi mật khẩu thất bại'));
    },
  });
  
  const onFinish = (values: ProfilePayload) => {
    updateMutation.mutate(values);
  };

  const onPasswordFinish = (values: ChangePasswordPayload) => {
    changePasswordMutation.mutate(values);
  };
  
  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <Title level={2}>Tài khoản của tôi</Title>
      
      <Card title="Thông tin cá nhân">
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            full_name: user?.full_name,
            phone: user?.phone || '',
            address: user?.address || '',
          }}
          onFinish={onFinish}
        >
          <Form.Item label="Email">
            <Input prefix={<MailOutlined />} value={user?.email} disabled />
          </Form.Item>
          
          <Form.Item
            name="full_name"
            label="Họ và tên"
            rules={[{ required: true, message: 'Vui lòng nhập họ tên!' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="Nguyễn Văn A" />
          </Form.Item>
          
          <Form.Item name="phone" label="Số điện thoại">
            <Input prefix={<PhoneOutlined />} placeholder="0901234567" />
          </Form.Item>
          
          <Form.Item name="address" label="Địa chỉ">
            <Input.TextArea
              placeholder="123 Đường ABC, Quận 1, TP. HCM"
              rows={3}
            />
          </Form.Item>
          
          <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>
            Lưu thay đổi
          </Button>
        </Form>
      </Card>
      
      <Card title="Đổi mật khẩu" style={{ marginTop: 24 }}>
        <Form
          form={passwordForm}
          layout="vertical"
          onFinish={onPasswordFinish}
        >
          <Form.Item
            name="old_password"
            label="Mật khẩu hiện tại"
            rules={[{ required: true, message: 'Vui lòng nhập mật khẩu hiện tại!' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Mật khẩu hiện tại"
            />
          </Form.Item>
          
          <Form.Item
            name="new_password"
            label="Mật khẩu mới"
            rules={[
              { required: true, message: 'Vui lòng nhập mật khẩu mới!' },
              { min: 6, message: 'Mật khẩu tối thiểu 6 ký tự!' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Mật khẩu mới"
            />
          </Form.Item>
          
          <Button type="primary" htmlType="submit" loading={changePasswordMutation.isPending}>
            Đổi mật khẩu
          </Button>
        </Form>
      </Card>
    </div>
  );
}
