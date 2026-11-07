import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Button, Input, Space, Tag, Typography } from 'antd';
import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons';
import api from '../api/axios';
import type { ApiError } from '../types/api';
import { getErrorMessage } from '../types/api';

const { Text } = Typography;

interface CouponValidateResponse {
  data?: {
    code: string;
    discount_amount: number;
    total: number;
  };
}

interface CouponInputProps {
  /** Tong tien hang (truoc giam gia) - server tinh lai tu day. */
  subtotal: number;
  /** Ma giam gia da ap dung (null = chua ap dung). */
  appliedCode: string | null;
  /** So tien giam server da xac nhan. */
  discountAmount: number;
  /** Callback khi ap dung / bo ma giam gia. */
  onChange: (code: string | null, discountAmount: number) => void;
}

/**
 * O nhap ma giam gia o man thanh toan.
 *
 * Server la noi duy nhat tinh tien giam - FE chi hien thi preview.
 * Khi dat hang, `coupon_code` duoc gui len va server validate + tinh lai.
 */
export default function CouponInput({
  subtotal,
  appliedCode,
  discountAmount,
  onChange,
}: CouponInputProps) {
  const [code, setCode] = useState('');

  const validateMutation = useMutation({
    mutationFn: async (value: string) => {
      const res = await api.post<CouponValidateResponse>('/api/coupons/validate', {
        code: value,
        subtotal: Math.round(subtotal),
      });
      return res.data.data;
    },
    onSuccess: (data) => {
      if (!data) return;
      onChange(data.code, data.discount_amount);
      setCode('');
    },
    onError: () => {
      onChange(null, 0);
    },
  });

  const handleApply = () => {
    const trimmed = code.trim();
    if (!trimmed) return;
    validateMutation.mutate(trimmed);
  };

  const handleRemove = () => {
    onChange(null, 0);
    setCode('');
  };

  if (appliedCode) {
    return (
      <Space wrap>
        <Tag
          icon={<CheckCircleFilled />}
          color="success"
          style={{ padding: '4px 10px', marginInlineEnd: 0 }}
        >
          {appliedCode} — giảm {discountAmount.toLocaleString('vi-VN')} đ
        </Tag>
        <Button size="small" type="link" onClick={handleRemove}>
          Bỏ mã
        </Button>
      </Space>
    );
  }

  return (
    <div>
      <Space.Compact style={{ width: '100%' }}>
        <Input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onPressEnter={handleApply}
          placeholder="Nhập mã giảm giá"
          disabled={validateMutation.isPending}
          status={validateMutation.isError ? 'error' : undefined}
        />
        <Button
          onClick={handleApply}
          loading={validateMutation.isPending}
          disabled={!code.trim()}
        >
          Áp dụng
        </Button>
      </Space.Compact>
      {validateMutation.isError && (
        <Text type="danger" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
          <CloseCircleFilled /> {getErrorMessage(validateMutation.error as ApiError, 'Mã giảm giá không hợp lệ')}
        </Text>
      )}
    </div>
  );
}
