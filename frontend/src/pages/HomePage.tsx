import { Typography } from 'antd';
import HeroSection from '../components/home/HeroSection';
import CategoryStrip from '../components/home/CategoryStrip';
import FeaturedTabs from '../components/home/FeaturedTabs';
import BrandStrip from '../components/home/BrandStrip';
import TrustBanner from '../components/home/TrustBanner';

const { Title } = Typography;

export default function HomePage() {
  return (
    <div>
      <HeroSection />

      <section style={{ marginBottom: 48 }}>
        <Title level={2}>Danh mục nổi bật</Title>
        <CategoryStrip />
      </section>

      <section style={{ marginBottom: 48 }}>
        <Title level={2}>Sản phẩm nổi bật</Title>
        <FeaturedTabs />
      </section>

      <section style={{ marginBottom: 48 }}>
        <Title level={2}>Thương hiệu uy tín</Title>
        <BrandStrip />
      </section>

      <section>
        <TrustBanner />
      </section>
    </div>
  );
}
