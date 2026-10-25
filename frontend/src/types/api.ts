import { AxiosError } from 'axios';

export interface ApiErrorResponse {
  detail?: string;
  message?: string;
}

export type ApiError = AxiosError<ApiErrorResponse>;

export function getErrorMessage(error: ApiError, fallback = 'Đã xảy ra lỗi'): string {
  return error.response?.data?.detail || error.response?.data?.message || fallback;
}
