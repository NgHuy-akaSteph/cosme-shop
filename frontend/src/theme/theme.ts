import type { ThemeConfig } from 'antd';
import { colors } from './colors';

/** Theme config antd cho Cosme Shop - mau nude/hong cam cho nganh my pham. */
export const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: colors.primary,
    colorInfo: colors.primary,
    colorSuccess: colors.success,
    colorWarning: colors.warning,
    colorError: colors.error,
    colorTextBase: colors.textBase,
    colorBgLayout: colors.bgLayout,
    colorBorderSecondary: colors.border,
    borderRadius: 10,
    fontFamily:
      "'Be Vietnam Pro', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 14,
    controlHeight: 38,
    boxShadowSecondary: '0 4px 20px rgba(44, 38, 34, 0.08)',
  },
  components: {
    Layout: {
      headerBg: colors.surface,
      headerHeight: 68,
      headerPadding: '0 32px',
      bodyBg: colors.bgLayout,
      footerBg: colors.surface,
    },
    Card: {
      borderRadiusLG: 16,
      paddingLG: 20,
    },
    Menu: {
      horizontalItemSelectedColor: colors.primary,
      horizontalItemHoverColor: colors.primary,
    },
    Table: {
      headerBg: colors.mutedSurface,
      headerColor: colors.textMuted,
    },
  },
};
