/** Config lien ket mang xa hoi cho footer. URL doc tu bien moi truong VITE_SOCIAL_* */

import type { ComponentType } from 'react';
import {
  FacebookOutlined,
  InstagramOutlined,
  TikTokOutlined,
  YoutubeOutlined,
} from '@ant-design/icons';

export interface SocialLink {
  /** Khoa duy nhat, dung lam `key` cho React list */
  key: string;
  /** Ten hien thi + aria-label */
  label: string;
  /** Icon hien thi */
  icon: ComponentType;
  /** URL trang fanpage/profile */
  url: string;
}

/** Ten bien moi truong chua URL tung kenh */
const SOCIAL_ENV_KEYS = {
  facebook: 'VITE_SOCIAL_FACEBOOK',
  instagram: 'VITE_SOCIAL_INSTAGRAM',
  tiktok: 'VITE_SOCIAL_TIKTOK',
  youtube: 'VITE_SOCIAL_YOUTUBE',
} as const;

/** Danh sach kenh mang xa hoi theo thu tu uu tien hien thi */
const SOCIAL_SOURCES: {
  key: keyof typeof SOCIAL_ENV_KEYS;
  label: string;
  icon: ComponentType;
}[] = [
  { key: 'facebook', label: 'Facebook', icon: FacebookOutlined },
  { key: 'instagram', label: 'Instagram', icon: InstagramOutlined },
  { key: 'tiktok', label: 'TikTok', icon: TikTokOutlined },
  { key: 'youtube', label: 'YouTube', icon: YoutubeOutlined },
];

/**
 * Lay danh sach link mang xa hoi da duoc cau hinh.
 * Bo qua cac kenh chua co URL de khong render icon treo (link chet).
 */
export function getSocialLinks(): SocialLink[] {
  const env = import.meta.env as unknown as Record<string, string | undefined>;

  return SOCIAL_SOURCES.reduce<SocialLink[]>((links, source) => {
    const url = (env[SOCIAL_ENV_KEYS[source.key]] ?? '').trim();
    if (url) {
      links.push({ key: source.key, label: source.label, icon: source.icon, url });
    }
    return links;
  }, []);
}

/** Lay URL cua mot kenh theo key (vd: 'facebook'), tra '' neu chua cau hinh */
export function getSocialUrl(key: keyof typeof SOCIAL_ENV_KEYS): string {
  return getSocialLinks().find((link) => link.key === key)?.url ?? '';
}
