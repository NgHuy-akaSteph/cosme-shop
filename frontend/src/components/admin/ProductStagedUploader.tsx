import { useEffect, useRef } from 'react';
import { App } from 'antd';
import { useProductImageMutations } from '../../hooks/useProductImages';
import { getErrorMessage } from '../../types/api';
import type { ApiError } from '../../types/api';

export interface PendingUpload {
  productId: number;
  files: File[];
}

export interface ProductStagedUploaderProps {
  /** Thong tin upload dang cho. Null = khong co gi de upload. */
  pending: PendingUpload | null;
  /** Callback goi sau khi upload xong (ke ca khi that bai) */
  onDone: () => void;
}

/**
 * Upload cac file anh da chon truoc khi tao san pham.
 *
 * Luong: admin chon anh o form "Them san pham" -> file duoc stage trong state
 * -> san pham duoc tao -> component nay upload file len `/api/upload/product-image/{id}`.
 *
 * Tach rieng thanh component de hook React duoc goi dung cap component
 * (khong goi hook trong callback).
 */
export default function ProductStagedUploader({
  pending,
  onDone,
}: ProductStagedUploaderProps) {
  const { message } = App.useApp();
  const { uploadMutation } = useProductImageMutations(pending?.productId ?? 0);

  // Ref giu mutation de effect khong chay lai khi identity thay doi
  const mutateRef = useRef(uploadMutation.mutateAsync);
  const messageRef = useRef(message);
  const onDoneRef = useRef(onDone);

  useEffect(() => {
    mutateRef.current = uploadMutation.mutateAsync;
    messageRef.current = message;
    onDoneRef.current = onDone;
  });

  useEffect(() => {
    if (!pending || pending.files.length === 0) {
      if (pending) onDoneRef.current();
      return;
    }

    let cancelled = false;

    const run = async () => {
      for (const file of pending.files) {
        if (cancelled) return;
        try {
          await mutateRef.current({
            file,
            isMain: false,
          });
        } catch (error) {
          messageRef.current.error(
            `Tải ảnh "${file.name}" thất bại: ` +
              getErrorMessage(error as ApiError, 'Lỗi không xác định')
          );
        }
      }
      if (!cancelled) onDoneRef.current();
    };

    void run();

    // StrictMode goi effect 2 lan -> cleanup huy vong chay dau tien,
    // tranh upload trung.
    return () => {
      cancelled = true;
    };
  }, [pending]);

  return null;
}
