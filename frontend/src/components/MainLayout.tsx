import { Outlet } from 'react-router-dom';
import { Layout } from 'antd';
import SiteHeader from './SiteHeader';
import SiteFooter from './SiteFooter';

const { Content } = Layout;

export default function MainLayout() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <SiteHeader />
      <Content style={{ padding: '0 32px' }}>
        <div
          style={{
            padding: '24px 0',
            minHeight: 'calc(100vh - 300px)',
            maxWidth: 1280,
            margin: '0 auto',
          }}
        >
          <Outlet />
        </div>
      </Content>
      <SiteFooter />
    </Layout>
  );
}
