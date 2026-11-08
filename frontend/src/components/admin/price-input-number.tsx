import { InputNumber } from 'antd';
import type { InputNumberProps } from 'antd';

/**
 * InputNumber cho GIA tien (VND).
 *
 * 2 van de giay ra o form Admin:
 * 1. BE tra gia chuoi "290000" -> InputNumber mac dinh hien thi "290000" (khong
 *    co dau phan cach) va `rc-input-number` KHONG parse duoc chuoi dang kho
 *    hoc "1.8E+5" -> hien thi sai ("1E"). Component nay luon nhan gia tri NUMBER
 *    nen ke co gia tri loi cung khong lam input vo.
 * 2. De doc de voi nguoi dung VN, hien thi dau phan cach nghin "290.000".
 *
 * `parser` bo moi dau phan cach -> gia tri gui len BE luon la so nguyen.
 * Xoa het o -> gia tri trong form la `null` (dung cho truong optional).
 */
export type PriceInputNumberProps = Omit<
  InputNumberProps<number>,
  'formatter' | 'parser'
>;

/**
 * Chuyen gia tri thanh chuoi co dau phan cach nghin theo chuan vi-VN.
 *
 * `rc-input-number` goi `formatter` voi gia tri co the la NUMBER hoac STRING
 * (tuong doi `MiniDecimal.toString()`) => phai chuan hoa ve number truoc.
 */
function formatWithSeparator(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '';
  const numeric =
    typeof value === 'number' ? value : Number(String(value).replace(/[^\d.-]/g, ''));
  if (!Number.isFinite(numeric)) return '';
  return new Intl.NumberFormat('vi-VN').format(numeric);
}

export default function PriceInputNumber(props: PriceInputNumberProps) {
  return (
    <InputNumber<number>
      {...props}
      // Dang go: giu nguyen chuoi nguoi dung dang nhap (tranh nhay con tro).
      formatter={(value, info) =>
        info.userTyping ? info.input : formatWithSeparator(value)
      }
      // Bo dau phan cach -> gia tri trong form luon la so nguyen.
      // Chuoi rong -> gia tri rong (rc-input-number hieu la "xoa het").
      parser={(displayValue) => {
        const digits = String(displayValue ?? '').replace(/\D/g, '');
        // `rc-input-number` khai bao parser tra `number`, nhung tra chuoi
        // rong la cach chuan de bao "khong co gia tri" (onChange -> null).
        return (digits === '' ? '' : Number(digits)) as unknown as number;
      }}
    />
  );
}
