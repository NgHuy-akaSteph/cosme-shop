import { Row, Col, Typography } from 'antd';
import {
  SafetyCertificateOutlined,
  TruckOutlined,
  SwapOutlined,
  CustomerServiceOutlined,
} from '@ant-design/icons';
import { colors } from '../../theme';

const { Text } = Typography;

const TRUST_POINTS = [
  {
    icon: <SafetyCertificateOutlined />,
    title: 'Chính hãng 100%',
    desc: 'Nguồn gốc rõ ràng từ nhà phân phối chính thức',
  },
  {
    icon: <TruckOutlined />,
    title: 'Miễn phí vận chuyển',
    desc: 'Giao hàng toàn quốc 2-4 ngày làm việc',
  },
  {
    icon: <SwapOutlined />,
    title: 'Đổi trả 7 ngày',
    desc: 'Hoàn tiền nhanh chóng nếu sản phẩm không hợp lý',
  },
  {
    icon: <CustomerServiceOutlined />,
    title: 'Tư vấn da',
    desc: 'Đội ngũ tư vấn chuyên sâu theo từng loại da',
  },
];

export default function TrustBanner() {
  return (
    <Row gutter={[16, 16]}>
      {TRUST_POINTS.map((point) => (
        <Col key={point.title} xs={24} sm={12} lg={6}>
          <div
            style={{
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
              background: colors.surface,
              borderRadius: 16,
              padding: 20,
              border: `1px solid ${colors.border}`,
            }}
          >
            <span style={{ fontSize: 24, color: colors.primary }}>{point.icon}</span>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{point.title}</div>
              <Text type="secondary" style={{ fontSize: 13 }}>
                {point.desc}
              </Text>
            </div>
          </div>
        </Col>
      ))}
    </Row>
  );
}
