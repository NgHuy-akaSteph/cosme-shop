import { Form, Input, Button, Card, Typography, message } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { MailOutlined, LockOutlined, UserOutlined } from '@ant-design/icons';
import api from '../../api/axios';
import { useAuthStore, type User } from '../../store/authStore';
import type { ApiError } from '../../types/api';
import { getErrorMessage } from '../../types/api';

const { Title, Text } = Typography;

interface RegisterForm {
  email: string;
  password: string;
  full_name: string;
}

export default function RegisterPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuthStore();
  
  const registerMutation = useMutation({
    mutationFn: async (data: RegisterForm) => {
      const res = await api.post('/api/auth/register', data);
      return res.data;
    },
    onSuccess: (data: { data: { user: User; access_token: string } }) => {
      const { user, access_token } = data.data;
      login(user, access_token);
      message.success('Đăng ký thành công!');
      
      // Redirect to previous page or home
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';
      navigate(from);
    },
    onError: (error: ApiError) => {
      message.error(getErrorMessage(error));
    },
  });
  
  const onFinish = (values: RegisterForm) => {
    registerMutation.mutate(values);
  };
  
  return (
    <div style={{ maxWidth: 400, margin: '0 auto', padding: '60px 0' }}>
      <Card>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={2}>Đăng ký</Title>
          <Text type="secondary">Tạo tài khoản mới</Text>
        </div>
        
        <Form
          name="register"
          onFinish={onFinish}
          layout="vertical"
          initialValues={{ email: '', password: '', full_name: '' }}
        >
          <Form.Item
            name="full_name"
            rules={[{ required: true, message: 'Vui lòng nhập họ tên!' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Họ và tên"
              size="large"
            />
          </Form.Item>
          
          <Form.Item
            name="email"
            rules={[
              { required: true, message: 'Vui lòng nhập email!' },
              { type: 'email', message: 'Email không hợp lệ!' },
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="Email"
              size="large"
            />
          </Form.Item>
          
          <Form.Item
            name="password"
            rules={[
              { required: true, message: 'Vui lòng nhập mật khẩu!' },
              { min: 6, message: 'Mật khẩu tối thiểu 6 ký tự!' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Mật khẩu (tối thiểu 6 ký tự)"
              size="large"
            />
          </Form.Item>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={registerMutation.isPending}
            >
              Đăng ký
            </Button>
          </Form.Item>
        </Form>
        
        <div style={{ textAlign: 'center' }}>
          <Text>Đã có tài khoản? </Text>
          <a onClick={() => navigate('/login', { state: { from: location.state?.from } })}>Đăng nhập</a>
        </div>
      </Card>
    </div>
  );
}
