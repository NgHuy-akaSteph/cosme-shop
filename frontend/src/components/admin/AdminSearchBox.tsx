import { useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { Input, Space } from 'antd';
import { LoadingOutlined, SearchOutlined } from '@ant-design/icons';

/**
 * O tim kiem dung chung cho cac trang Admin.
 *
 * Goc "de" (debounce): chi goi `onChange` sau khi nguoi dung ngung go 300ms.
 * Neu khong debounce, moi ky tu go se tao 1 request API - rat lau voi
 * tim kiem server-side (san pham / nguoi dung / don hang).
 */

/** Thoi gian cho (ms) truoc khi gui gia tri search len tren. */
const DEBOUNCE_MS = 300;

/** Do rong mac dinh cua o tim kiem. */
const DEFAULT_WIDTH = 280;

interface AdminSearchBoxProps {
  /** Gia tri search hien tai (giu o page cha de dua vao query key). */
  value: string;
  /** Duoc goi sau khi debounce xong voi gia tri moi. */
  onChange: (value: string) => void;
  /** Chuoi goi y trong o nhap. */
  placeholder?: string;
  /** Hien thi trang thai dang tai. */
  loading?: boolean;
  /** Ghi de style cua wrapper (vd dung chung hang voi bo loc). */
  style?: CSSProperties;
}

export default function AdminSearchBox({
  value,
  onChange,
  placeholder = 'Tìm kiếm...',
  loading = false,
  style,
}: AdminSearchBoxProps) {
  // Gia tri hien thi trong input - phai cap nhat ngay de viet duoc.
  const [inputValue, setInputValue] = useState(value);

  // `value` cua cha co the doi lap (vd cha reset search) -> can dong bo
  // `inputValue`. Dung khu mau "adjust state during render" cua React thay vi
  // setState trong effect (gop render, khong gay cascading render).
  const [syncedValue, setSyncedValue] = useState(value);
  if (value !== syncedValue) {
    setSyncedValue(value);
    setInputValue(value);
  }

  // `onChange` thuong la inline arrow function -> danh moi moi render.
  // Giu trong ref de hieu ung cua debounce khong bi reset moi render.
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  // Debounce: gui gia tri len tren sau khi nguoi dung ngung go.
  useEffect(() => {
    if (inputValue === value) return;

    const timer = setTimeout(() => {
      onChangeRef.current(inputValue);
    }, DEBOUNCE_MS);

    // Clear timer neu nguoi dung van go tiep -> chi gui gia tri cuoi cung.
    return () => clearTimeout(timer);
  }, [inputValue, value]);

  return (
    <Space style={{ marginBottom: 16, display: 'flex', ...style }}>
      <Input
        allowClear
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        prefix={<SearchOutlined />}
        suffix={loading ? <LoadingOutlined /> : undefined}
        placeholder={placeholder}
        style={{ width: DEFAULT_WIDTH }}
      />
    </Space>
  );
}
