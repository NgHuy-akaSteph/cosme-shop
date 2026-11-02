import { Form, Input, Button, Card, Typography, App } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { MailOutlined, LockOutlined } from '@ant-design/icons';
import api from '../../api/axios';
import { useAuthStore } from '../../store/authStore';
import type { ApiError } from '../../types/api';
import { getErrorMessage } from '../../types/api';

const { Title, Text } = Typography;

interface LoginForm {
  email: string;
  password: string;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuthStore();
  const { message } = App.useApp();
  
  const loginMutation = useMutation({
    mutationFn: async (data: LoginForm) => {
      const res = await api.post('/api/auth/login', data);
      return res.data;
    },
    onSuccess: (data) => {
      const { user, access_token } = data.data;
      login(user, access_token);
      message.success('Đăng nhập thành công!');
      
      // Redirect to previous page or home
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';
      navigate(from);
    },
    onError: (error: ApiError) => {
      message.error(getErrorMessage(error));
    },
  });
  
  const onFinish = (values: LoginForm) => {
    loginMutation.mutate(values);
  };
  
  return (
    <div style={{ maxWidth: 400, margin: '0 auto', padding: '60px 0' }}>
      <Card>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={2}>Đăng nhập</Title>
          <Text type="secondary">Chào mừng bạn quay trở lại!</Text>
        </div>
        
        <Form
          name="login"
          onFinish={onFinish}
          layout="vertical"
          initialValues={{ email: '', password: '' }}
        >
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
            rules={[{ required: true, message: 'Vui lòng nhập mật khẩu!' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Mật khẩu"
              size="large"
            />
          </Form.Item>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={loginMutation.isPending}
            >
              Đăng nhập
            </Button>
          </Form.Item>
        </Form>
        
        <div style={{ textAlign: 'center' }}>
          <Text>Chưa có tài khoản? </Text>
          <a onClick={() => navigate('/register', { state: { from: location.state?.from } })}>Đăng ký ngay</a>
        </div>
      </Card>
    </div>
  );
}
