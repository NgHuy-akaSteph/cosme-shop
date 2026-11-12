import { Link } from 'react-router-dom';
import { Layout, Typography, Space, Divider, Tooltip } from 'antd';
import { colors } from '../theme';
import { getSocialLinks } from '../config/social-links';

const { Footer } = Layout;
const { Text, Title } = Typography;

export default function SiteFooter() {
  const socialLinks = getSocialLinks();

  return (
    <Footer style={{ padding: '48px 32px 24px' }}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 40,
          justifyContent: 'space-between',
        }}
      >
        <div style={{ maxWidth: 280 }}>
          <Title level={4} style={{ marginTop: 0 }}>
            Cosme<span style={{ color: colors.primary }}>Shop</span>
          </Title>
          <Text type="secondary">
            Mỹ phẩm chính hãng từ các thương hiệu uy tín trong nước và quốc tế. Giao hàng toàn
            quốc, đổi trả trong 7 ngày.
          </Text>
        </div>

        <div>
          <Title level={5}>Mua sắm</Title>
          <Space direction="vertical" size={6}>
            <Link to="/products">Tất cả sản phẩm</Link>
            <Link to="/products?sort=best_seller">Bán chạy</Link>
            <Link to="/products?sort=newest">Mới về</Link>
            <Link to="/cart">Giỏ hàng</Link>
          </Space>
        </div>

        <div>
          <Title level={5}>Hỗ trợ</Title>
          <Space direction="vertical" size={6}>
            <Link to="/orders">Tra cứu đơn hàng</Link>
            <Link to="/profile">Tài khoản</Link>
            <Link to="/faq">Câu hỏi thường gặp</Link>
            <span>Chính sách đổi trả</span>
            <span>Liên hệ: 1900 6868</span>
          </Space>
        </div>

        <div>
          <Title level={5}>Kết nối</Title>
          {socialLinks.length > 0 ? (
            <Space size={16}>
              {socialLinks.map(({ key, label, icon: Icon, url }) => (
                <Tooltip key={key} title={label}>
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={label}
                    style={{ color: colors.textBase, fontSize: 20, lineHeight: 1 }}
                  >
                    <Icon />
                  </a>
                </Tooltip>
              ))}
            </Space>
          ) : (
            <Text type="secondary" style={{ fontSize: 13 }}>
              Fanpage chính thức đang được cập nhật
            </Text>
          )}
        </div>
      </div>

      <Divider />
      <div style={{ textAlign: 'center' }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          © {new Date().getFullYear()} Cosme Shop. Giao hàng toàn quốc — Miễn phí vận chuyển.
        </Text>
      </div>
    </Footer>
  );
}
