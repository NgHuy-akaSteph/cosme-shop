import { useState } from 'react';
import {
  Button,
  Empty,
  Image,
  Input,
  Popconfirm,
  Space,
  Tag,
  Tooltip,
  Typography,
  Upload,
  App,
} from 'antd';
import type { UploadProps } from 'antd';
import type { UploadRequestFile } from 'rc-upload/lib/interface';
import {
  DeleteOutlined,
  StarFilled,
  StarOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  PictureOutlined,
} from '@ant-design/icons';
import { useProductImages, useProductImageMutations } from '../../hooks/useProductImages';
import type { ProductImage } from '../../types/product';
import { getErrorMessage } from '../../types/api';
import type { ApiError } from '../../types/api';

const { Text } = Typography;

/** Kich thuoc file toi da cho phep (khop voi backend) */
const MAX_FILE_SIZE = 5 * 1024 * 1024;
/** Format duoc phep - phai khop voi `ALLOWED_UPLOAD_FORMATS` cua backend */
const ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp'];
/** Kich thuoc toi thieu khuyen nghi de anh khong mo khi phong to */
const RECOMMENDED_MIN_SIZE = 800;

export interface ProductImageManagerProps {
  /** ID san pham. Neu undefined -> chi stage file, chua upload (dung khi tao moi) */
  productId?: number;
  /** Danh sach anh da upload (dung khi khong co productId) */
  images?: ProductImage[];
  /** File da stage (chua upload) */
  stagedFiles?: File[];
  /** Callback khi danh sach staged thay doi */
  onStagedFilesChange?: (files: File[]) => void;
  /** Disable moi thao tac (vd khi form dang submit) */
  disabled?: boolean;
}

/**
 * Validate file phia client truoc khi upload.
 * Backend cung validate lai (mime + magic bytes) - day la lop filter UI.
 */
function validateFile(file: File): string | null {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return `Định dạng không hỗ trợ (${extension}). Chỉ chấp nhận: ${ALLOWED_EXTENSIONS.join(', ')}`;
  }
  if (file.size > MAX_FILE_SIZE) {
    return `File quá lớn (${(file.size / 1024 / 1024).toFixed(1)}MB). Tối đa 5MB`;
  }
  if (file.size === 0) {
    return 'File rỗng';
  }
  return null;
}

/**
 * Component quan ly anh san pham - dung chung cho:
 * - Form Them/Sua san pham (trong modal)
 * - Modal "Quan ly anh" rieng
 *
 * Neu khong co `productId` -> chi cho stage file (chua upload vi san pham
 * chua duoc tao). Khi tao san pham xong, file staged se duoc upload len.
 */
export default function ProductImageManager({
  productId,
  images: imagesProp,
  stagedFiles,
  onStagedFilesChange,
  disabled = false,
}: ProductImageManagerProps) {
  const { message } = App.useApp();
  const [selectedImageId, setSelectedImageId] = useState<number | null>(null);
  const [altText, setAltText] = useState('');

  // Neu co productId -> lay danh sach anh tu API. Neu khong -> dung prop.
  const { data: fetchedImages } = useProductImages(productId);
  const images = productId ? (fetchedImages ?? []) : (imagesProp ?? []);

  const {
    uploadMutation,
    deleteMutation,
    setMainMutation,
    updateMutation,
    reorderMutation,
  } = useProductImageMutations(productId ?? 0);

  const isStagedMode = !productId;

  // ---- Upload ----
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    listType: 'picture-card',
    // Danh sach file duoc quan ly rieng (staged mode) hoac bo qua (upload mode
    // vi danh sach anh lay tu server) -> tat list mac dinh cua antd.
    showUploadList: false,
    accept: ALLOWED_EXTENSIONS.map((ext) => `.${ext}`).join(','),
    disabled: disabled || uploadMutation.isPending,
    beforeUpload: (file) => {
      const error = validateFile(file);
      if (error) {
        message.error(error);
        return Upload.LIST_IGNORE;
      }
      return true;
    },
    customRequest: async (options) => {
      const { file, onSuccess, onError } = options;
      const selected = file as File;

      // Che do staged: chi giu file trong state, chua upload
      if (isStagedMode) {
        onStagedFilesChange?.([...(stagedFiles ?? []), selected]);
        onSuccess?.({} as UploadRequestFile);
        return;
      }

      try {
        const result = await uploadMutation.mutateAsync({
          file: selected,
          isMain: images.length === 0,
        });
        message.success(`Đã tải lên "${selected.name}"`);
        onSuccess?.(result as unknown as UploadRequestFile);
      } catch (error) {
        const msg = getErrorMessage(error as ApiError, 'Không thể tải ảnh lên');
        message.error(msg);
        onError?.(error as Error);
      }
    },
  };

  // ---- Xoa ----
  const handleDelete = async (image: ProductImage) => {
    try {
      const result = await deleteMutation.mutateAsync(image.id);
      if (result.asset_kept) {
        message.warning(result.message);
      } else {
        message.success('Đã xóa ảnh');
      }
      if (selectedImageId === image.id) {
        setSelectedImageId(null);
        setAltText('');
      }
    } catch (error) {
      message.error(getErrorMessage(error as ApiError, 'Không thể xóa ảnh'));
    }
  };

  // ---- Dat anh chinh ----
  const handleSetMain = async (image: ProductImage) => {
    try {
      await setMainMutation.mutateAsync(image.id);
      message.success('Đã đặt làm ảnh chính');
    } catch (error) {
      message.error(getErrorMessage(error as ApiError, 'Không thể đặt ảnh chính'));
    }
  };

  // ---- Cap nhat alt text ----
  const handleSaveAltText = async () => {
    if (!selectedImageId) return;
    try {
      await updateMutation.mutateAsync({ imageId: selectedImageId, altText });
      message.success('Đã lưu mô tả ảnh');
    } catch (error) {
      message.error(getErrorMessage(error as ApiError, 'Không thể lưu mô tả ảnh'));
    }
  };

  // ---- Sap xep thu tu ----
  const handleMove = async (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= images.length) return;

    const nextIds = images.map((img) => img.id);
    [nextIds[index], nextIds[target]] = [nextIds[target], nextIds[index]];

    try {
      await reorderMutation.mutateAsync(nextIds);
    } catch (error) {
      message.error(getErrorMessage(error as ApiError, 'Không thể đổi thứ tự ảnh'));
    }
  };

  const selectedImage = images.find((img) => img.id === selectedImageId);

  return (
    <div>
      {/* Vung upload */}
      <Upload {...uploadProps}>
        {isStagedMode && (stagedFiles?.length ?? 0) > 0 ? null : (
          <div style={{ padding: 24, textAlign: 'center' }}>
            <PictureOutlined style={{ fontSize: 32, color: '#d9c8c0' }} />
            <div style={{ marginTop: 8 }}>Thêm ảnh</div>
          </div>
        )}
      </Upload>

      {/* File da stage (chua upload) */}
      {isStagedMode && (stagedFiles?.length ?? 0) > 0 && (
        <div style={{ marginTop: 16 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Ảnh sẽ được tải lên sau khi tạo sản phẩm ({stagedFiles?.length} ảnh)
          </Text>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
            {stagedFiles?.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                style={{
                  position: 'relative',
                  width: 104,
                  height: 104,
                  borderRadius: 8,
                  overflow: 'hidden',
                  border: '1px solid #f0e6e1',
                }}
              >
                <img
                  src={URL.createObjectURL(file)}
                  alt={file.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
                <Popconfirm
                  title="Bỏ ảnh này?"
                  onConfirm={() =>
                    onStagedFilesChange?.(
                      (stagedFiles ?? []).filter((_, i) => i !== index)
                    )
                  }
                >
                  <Button
                    size="small"
                    danger
                    shape="circle"
                    icon={<DeleteOutlined />}
                    style={{ position: 'absolute', top: 4, right: 4 }}
                  />
                </Popconfirm>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Danh sach anh da upload */}
      {!isStagedMode && images.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Kéo thả hoặc dùng mũi tên để đổi thứ tự hiển thị
          </Text>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
              gap: 12,
              marginTop: 8,
            }}
          >
            {images.map((image, index) => (
              <div
                key={image.id}
                onClick={() => {
                  setSelectedImageId(image.id);
                  setAltText(image.alt_text ?? '');
                }}
                style={{
                  border:
                    selectedImageId === image.id
                      ? '2px solid #d9736a'
                      : '1px solid #f0e6e1',
                  borderRadius: 12,
                  overflow: 'hidden',
                  cursor: 'pointer',
                  background: '#fff',
                }}
              >
                <div style={{ position: 'relative', height: 120, background: '#f7f2ef' }}>
                  <Image
                    src={image.image_urls?.thumb ?? image.secure_url}
                    alt={image.alt_text ?? `Ảnh ${index + 1}`}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    preview={{
                      src: image.image_urls?.detail ?? image.secure_url,
                    }}
                  />
                  {image.is_main && (
                    <Tag
                      color="gold"
                      icon={<StarFilled />}
                      style={{
                        position: 'absolute',
                        top: 6,
                        left: 6,
                        margin: 0,
                        borderRadius: 6,
                      }}
                    >
                      Chính
                    </Tag>
                  )}
                </div>

                <div style={{ padding: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <Space size={4} wrap>
                    <Tooltip title="Lên trên">
                      <Button
                        size="small"
                        icon={<ArrowLeftOutlined />}
                        disabled={index === 0 || reorderMutation.isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMove(index, -1);
                        }}
                      />
                    </Tooltip>
                    <Tooltip title="Xuống dưới">
                      <Button
                        size="small"
                        icon={<ArrowRightOutlined />}
                        disabled={index === images.length - 1 || reorderMutation.isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMove(index, 1);
                        }}
                      />
                    </Tooltip>
                    <Tooltip
                      title={image.is_main ? 'Ảnh chính' : 'Đặt làm ảnh chính'}
                    >
                      <Button
                        size="small"
                        icon={image.is_main ? <StarFilled /> : <StarOutlined />}
                        disabled={image.is_main || setMainMutation.isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSetMain(image);
                        }}
                      />
                    </Tooltip>
                    <Popconfirm
                      title="Xóa ảnh này?"
                      description="Nếu ảnh đã bán, ảnh sẽ được giữ lại trên server."
                      onConfirm={() => handleDelete(image)}
                    >
                      <Button
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        loading={deleteMutation.isPending}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </Popconfirm>
                  </Space>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Chinh sua alt text */}
      {!isStagedMode && selectedImage && (
        <div style={{ marginTop: 16 }}>
          <Space.Compact style={{ width: '100%' }}>
            <Input
              placeholder="Mô tả ảnh (alt text) cho SEO"
              value={altText}
              onChange={(e) => setAltText(e.target.value)}
              onPressEnter={handleSaveAltText}
            />
            <Button
              onClick={handleSaveAltText}
              loading={updateMutation.isPending}
              disabled={altText === (selectedImage.alt_text ?? '')}
            >
              Lưu
            </Button>
          </Space.Compact>
        </div>
      )}

      {!isStagedMode && images.length === 0 && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Chưa có ảnh nào"
          style={{ marginTop: 16 }}
        />
      )}

      {RECOMMENDED_MIN_SIZE > 0 && (
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 12 }}>
          Khuyến nghị: ảnh vuông hoặc gần vuông, tối thiểu {RECOMMENDED_MIN_SIZE}px, tối đa 5MB.
          Hệ thống tự tạo các kích cỡ nhỏ hơn khi hiển thị.
        </Text>
      )}
    </div>
  );
}
