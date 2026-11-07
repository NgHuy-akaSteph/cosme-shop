import { Radio, Typography } from 'antd';
import type { RecipientMode } from '../../types/checkout';

const { Text } = Typography;

interface RecipientSelectorProps {
  value: RecipientMode;
  onChange: (value: RecipientMode) => void;
}

/**
 * Chon nhan hang: giao cho ban than (dien ho so) hoac cho nguoi khac (nhap tay).
 */
export default function RecipientSelector({ value, onChange }: RecipientSelectorProps) {
  return (
    <div style={{ marginBottom: 16 }}>
      <Text strong>Giao hàng cho:</Text>
      <Radio.Group
        value={value}
        onChange={(e) => onChange(e.target.value as RecipientMode)}
        style={{ marginTop: 8 }}
      >
        <Radio value="self">
          <Text>Giao cho tôi (dùng thông tin trong hồ sơ)</Text>
        </Radio>
        <br />
        <Radio value="other">
          <Text>Giao cho người khác</Text>
        </Radio>
      </Radio.Group>
    </div>
  );
}
