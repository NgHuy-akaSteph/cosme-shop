import type { TableColumnType } from 'antd';

/**
 * Helper tao cot STT cho cac bang danh sach trong trang Admin.
 *
 * STT (so thu tu) thay the cot ID raw de danh sach de doc: ID la khoa ky
 * thuat co lo hong (tao 22 roi xoa -> id tiep theo la 23) nhìn rat roi.
 *
 * Voi bang co phan trang, STT phai tinh ca tren trang hien tai:
 * `STT = (page - 1) * pageSize + index + 1` -> danh so lien tuc 1,2,3...
 */

/** Kich thuoc cot STT mac dinh. */
const SEQUENCE_COLUMN_WIDTH = 64;

/** Trang dau tien (theo convention cua antd pagination: bat dau tu 1). */
const FIRST_PAGE = 1;

/**
 * Cot STT cho bang co phan trang (server-side).
 *
 * @param page Trang hien tai (bat dau tu 1).
 * @param pageSize So ban ghi tren moi trang.
 */
export function buildSequenceColumn<T>(
  page: number,
  pageSize: number,
): TableColumnType<T> {
  const offset = (Math.max(page, FIRST_PAGE) - FIRST_PAGE) * pageSize;
  return {
    title: 'STT',
    key: 'sequence',
    width: SEQUENCE_COLUMN_WIDTH,
    align: 'center',
    render: (_: unknown, __: T, index: number) => offset + index + 1,
  };
}

/**
 * Cot STT cho bang khong phan trang (du lieu da load het ve FE).
 *
 * STT bat dau tu 1 va danh so lai theo ket qua loc hien tai.
 */
export function buildSimpleSequenceColumn<T>(): TableColumnType<T> {
  return {
    title: 'STT',
    key: 'sequence',
    width: SEQUENCE_COLUMN_WIDTH,
    align: 'center',
    render: (_: unknown, __: T, index: number) => index + 1,
  };
}
