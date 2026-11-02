import { AxiosError } from 'axios';

export interface ApiErrorResponse {
  /** Backend co the tra detail la string hoac object {message, code} */
  detail?: string | { message?: string; code?: string };
  message?: string;
}

export type ApiError = AxiosError<ApiErrorResponse>;

/**
 * Lay thong bao loi tu response cua API.
 *
 * Backend tra 2 dang:
 * - `detail` la string (FastAPI default)
 * - `detail` la object `{message, code}` (loi custom cua project)
 */
export function getErrorMessage(error: ApiError, fallback = 'Đã xảy ra lỗi'): string {
  const detail = error.response?.data?.detail;

  if (typeof detail === 'string' && detail) {
    return detail;
  }
  if (detail && typeof detail === 'object' && detail.message) {
    return detail.message;
  }
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  return fallback;
}

/**
 * Lay ma loi (VD: "VALIDATION_ERROR") tu response - dung de xu ly logic
 * thay vi so sanh message.
 */
export function getErrorCode(error: ApiError): string | undefined {
  const detail = error.response?.data?.detail;
  if (detail && typeof detail === 'object' && detail.code) {
    return detail.code;
  }
  return undefined;
}
