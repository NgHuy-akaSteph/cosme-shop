import { Button, Typography } from 'antd';
import { Link } from 'react-router-dom';
import { colors } from '../../theme';

const { Title, Text } = Typography;

export default function HeroSection() {
  return (
    <div
      style={{
        borderRadius: 24,
        overflow: 'hidden',
        background: `linear-gradient(120deg, ${colors.primarySoft} 0%, ${colors.gradientWarm} 55%, ${colors.gradientWarmEnd} 100%)`,
        display: 'flex',
        alignItems: 'center',
        minHeight: 380,
        padding: '48px 40px',
        marginBottom: 48,
      }}
    >
      <div style={{ maxWidth: 560 }}>
        <Text
          strong
          style={{
            display: 'inline-block',
            background: colors.surface,
            color: colors.primary,
            borderRadius: 999,
            padding: '6px 16px',
            marginBottom: 20,
          }}
        >
          Chăm sóc da đúng cách — Chính hãng 100%
        </Text>

        <Title level={1} style={{ marginBottom: 16, color: colors.textBase }}>
          Mỹ phẩm chính hãng cho làn da khoẻ đẹp
        </Title>

        <Text type="secondary" style={{ fontSize: 16, display: 'block', marginBottom: 28 }}>
          Hơn 200 sản phẩm chăm sóc da được tuyển chọn từ các thương hiệu uy tín, giao hàng
          nhanh toàn quốc và đổi trả linh hoạt trong 7 ngày.
        </Text>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Link to="/products">
            <Button type="primary" size="large">
              Mua sắm ngay
            </Button>
          </Link>
          <Link to="/products?sort=best_seller">
            <Button size="large">Sản phẩm bán chạy</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
