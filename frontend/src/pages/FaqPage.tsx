import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Collapse, Typography, Grid, Space, Button, Anchor, Row, Col } from 'antd';
import {
  CustomerServiceOutlined,
  PhoneOutlined,
  ShopOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { FAQ_CATEGORIES, FAQ_ITEMS } from '../data/faq-items';
import { getSocialUrl } from '../config/social-links';
import { colors } from '../theme';

const { Title, Text, Paragraph } = Typography;

const HOTLINE = '1900 6868';
const FANPAGE_URL = getSocialUrl('facebook') || 'https://m.me/cosmeshop';

/** Tao id hop le cho DOM tu ten nhom chu de (bo khoang trang dau) */
function toAnchorId(category: string): string {
  return `faq-${category
    .toLowerCase()
    .replace(/đ/g, 'd')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')}`;
}

export default function FaqPage() {
  const screens = Grid.useBreakpoint();

  /** Gom cac cau hoi theo tung nhom chu de */
  const groupedItems = useMemo(
    () =>
      FAQ_CATEGORIES.map((category) => ({
        category,
        anchorId: toAnchorId(category),
        items: FAQ_ITEMS.filter((item) => item.category === category),
      })),
    []
  );

  const anchorItems = useMemo(
    () =>
      groupedItems.map(({ category, anchorId, items }) => ({
        key: anchorId,
        href: `#${anchorId}`,
        title: category,
        label: `${category} (${items.length})`,
      })),
    [groupedItems]
  );

  return (
    <div>
      <div style={{ maxWidth: 760, marginBottom: 32 }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          Câu hỏi thường gặp
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 15 }}>
          Tổng hợp các thắc mắc về đặt hàng, giao hàng, đổi trả và cách chọn mỹ phẩm phù hợp.
          Nếu chưa tìm thấy câu trả lời, đội ngũ tư vấn của Cosme Shop sẵn sàng hỗ trợ bạn.
        </Paragraph>
      </div>

      <Row gutter={[32, 24]}>
        {screens.lg && (
          <Col xs={24} lg={6}>
            <div
              style={{
                position: 'sticky',
                top: 96,
                background: colors.surface,
                border: `1px solid ${colors.border}`,
                borderRadius: 16,
                padding: 20,
              }}
            >
              <Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>
                Nội dung
              </Title>
              <Anchor items={anchorItems} />
            </div>
          </Col>
        )}

        <Col xs={24} lg={18}>
          <Space direction="vertical" size={32} style={{ display: 'flex' }}>
            {groupedItems.map(({ category, anchorId, items }) => (
              <section key={category} id={anchorId}>
                <Title level={4} style={{ marginBottom: 12 }}>
                  {category}
                </Title>
                <Collapse
                  accordion
                  ghost
                  items={items.map((item) => ({
                    key: item.id,
                    label: <Text strong>{item.question}</Text>,
                    children: (
                      <Paragraph style={{ marginBottom: 0, color: colors.textMuted }}>
                        {item.answer}
                      </Paragraph>
                    ),
                  }))}
                />
              </section>
            ))}
          </Space>

          <div
            style={{
              marginTop: 40,
              background: colors.primarySoft,
              border: `1px solid ${colors.border}`,
              borderRadius: 16,
              padding: 24,
            }}
          >
            <Title level={4} style={{ marginTop: 0, marginBottom: 8 }}>
              Vẫn chưa tìm thấy câu trả lời?
            </Title>
            <Paragraph style={{ color: colors.textMuted, marginBottom: 16 }}>
              Liên hệ ngay với đội ngũ tư vấn Cosme Shop để được hỗ trợ nhanh nhất.
            </Paragraph>
            <Space wrap>
              <Button type="primary" icon={<PhoneOutlined />} href={`tel:${HOTLINE}`}>
                Gọi {HOTLINE}
              </Button>
              <Button
                icon={<MessageOutlined />}
                href={FANPAGE_URL}
                target="_blank"
                rel="noopener noreferrer"
              >
                Nhắn Fanpage
              </Button>
              <Link to="/products">
                <Button icon={<ShopOutlined />}>Xem tất cả sản phẩm</Button>
              </Link>
            </Space>
          </div>

          <div
            style={{
              marginTop: 24,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              color: colors.textSecondary,
            }}
          >
            <CustomerServiceOutlined style={{ fontSize: 20, color: colors.primary }} />
            <Text type="secondary" style={{ fontSize: 13 }}>
              Hotline tư vấn {HOTLINE} hoạt động 8:00 - 21:00, tất cả các ngày trong tuần.
            </Text>
          </div>
        </Col>
      </Row>
    </div>
  );
}
