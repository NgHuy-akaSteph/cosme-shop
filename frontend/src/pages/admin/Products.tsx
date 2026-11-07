import {
  Table,
  Button,
  Card,
  Typography,
  Space,
  Tag,
  Popconfirm,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  App,
  Tooltip,
  Image,
} from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PictureOutlined,
} from '@ant-design/icons';
import api from '../../api/axios';
import type { ApiError } from '../../types/api';
import { getErrorMessage } from '../../types/api';
import { CONCERNS, SKIN_TYPES } from '../../utils/constants';
import { colors } from '../../theme';
import ProductImageManager from '../../components/admin/ProductImageManager';
import ProductImageGalleryModal from '../../components/admin/ProductImageGalleryModal';
import ProductStagedUploader from '../../components/admin/ProductStagedUploader';
import type { PendingUpload } from '../../components/admin/ProductStagedUploader';
import type { ProductImage, ProductVariant } from '../../types/product';

const { Title, Text } = Typography;

/** 1 bien the trong form admin. `id` tu sinh neu admin de trong. */
interface VariantFormRow {
  id?: string;
  name?: string;
  price?: number | null;
  stock?: number | null;
}

interface AdminProduct {
    id: number;
  name: string;
  price: number;
  sale_price: number | null;
  stock: number;
  is_active: boolean;
  description?: string | null;
  category_id: number;
  brand_id: number;
  category: { name: string } | null;
    brand: { name: string } | null;
  skin_types?: string[] | null;
  concerns?: string[] | null;
  key_ingredients?: string[] | null;
  free_from?: string[] | null;
  variants?: VariantFormRow[] | null;
  image_url?: string | null;
  images?: ProductImage[] | null;
}

interface Category {
  id: number;
  name: string;
}

interface Brand {
  id: number;
  name: string;
}

interface ProductFormValues {
    name: string;
  price: number;
  sale_price?: number | null;
  stock: number;
  category_id: number;
  brand_id: number;
  description?: string;
  skin_types?: string[];
  concerns?: string[];
  key_ingredients?: string[];
    free_from?: string[];
  variants?: VariantFormRow[];
}

/**
 * Payload gui len BE. `variants` cho phep `null` (san pham khong co bien the)
 * va dung shape `ProductVariant` de khop schema `VariantInfo` cua backend.
 */
type ProductSubmitValues = Omit<ProductFormValues, 'variants'> & {
  variants?: ProductVariant[] | null;
};

/**
 * Sinh `id` cho bien the khi admin de trong.
 * `id` phai duy nhat trong 1 san pham (cart key = product_id + variant_id).
 */
function buildVariantId(taken: Set<string>, index: number): string {
  let counter = index + 1;
  let candidate = `v${counter}`;
  while (taken.has(candidate)) {
    counter += 1;
    candidate = `v${counter}`;
  }
  return candidate;
}

/**
 * Chuan hoa variants truoc khi gui BE:
 * - bo dong rong (khong co ten)
 * - gan `id` neu admin de trong, hoac khi id bi trung
 * - ep `price`/`stock` thanh number, `stock` null -> 0
 */
function normalizeVariants(rows: VariantFormRow[] | undefined): ProductVariant[] {
  if (!rows?.length) return [];

  const taken = new Set<string>();
  const result: ProductVariant[] = [];

  rows.forEach((row, index) => {
    const name = row.name?.trim();
    if (!name) return; // dong rong -> bo qua

    let id = row.id?.trim();
    if (!id || taken.has(id)) {
      id = buildVariantId(taken, index);
    }
    taken.add(id);

    result.push({
      id,
      name,
      price: row.price ?? null,
      stock: row.stock ?? 0,
    });
  });

  return result;
}

function formatPrice(price: number): string {
  return new Intl.NumberFormat('vi-VN').format(price) + ' đ';
}

export default function AdminProducts() {
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<AdminProduct | null>(null);
  const [form] = Form.useForm<ProductFormValues>();

  // San pham co bien the -> `stock` la gia tri dan xuat (tong stock variants),
  // BE tu tinh lai. Admin khong nhap tay de tranh 2 nguon stock lech nhau.
  const watchedVariants = Form.useWatch('variants', form);
  const hasVariantRows = (watchedVariants?.length ?? 0) > 0;

  // Modal quan ly anh rieng
  const [galleryProduct, setGalleryProduct] = useState<AdminProduct | null>(null);

  // File anh da chon nhung chua upload (chi dung khi TAO san pham moi)
  const [stagedFiles, setStagedFiles] = useState<File[]>([]);

  // Upload dang cho: san pham da tao xong, can day file anh len
  const [pendingUpload, setPendingUpload] = useState<PendingUpload | null>(null);

  const { data: products, isLoading } = useQuery({
    queryKey: ['admin', 'products'],
    queryFn: async () => {
      const res = await api.get('/api/products?size=100');
      return res.data.data as AdminProduct[];
    },
  });

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const res = await api.get('/api/categories');
      return res.data.data as Category[];
    },
  });

  const { data: brands } = useQuery({
    queryKey: ['brands'],
    queryFn: async () => {
      const res = await api.get('/api/brands');
      return res.data.data as Brand[];
    },
  });

  const createMutation = useMutation({
    mutationFn: async (values: ProductSubmitValues) => {
      const res = await api.post('/api/products', values);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'products'] });
      message.success('Tạo sản phẩm thành công!');
      handleCloseModal();
      // Upload file anh da staged - xem ProductStagedUploader
      setPendingUpload({ productId: data?.data?.id as number, files: stagedFiles });
    },
    onError: (error: ApiError) => {
      message.error(getErrorMessage(error, 'Có lỗi xảy ra'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...values }: ProductSubmitValues & { id: number }) => {
      const res = await api.patch(`/api/products/${id}`, values);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'products'] });
      message.success('Cập nhật thành công!');
      handleCloseModal();
    },
    onError: (error: ApiError) => {
      message.error(getErrorMessage(error, 'Có lỗi xảy ra'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/products/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'products'] });
      message.success('Xóa sản phẩm thành công!');
    },
  });

  const handleOpenModal = (product?: AdminProduct) => {
    if (product) {
      setEditingProduct(product);
      form.setFieldsValue({
        name: product.name,
        price: product.price,
        sale_price: product.sale_price,
        stock: product.stock,
        category_id: product.category_id,
        brand_id: product.brand_id,
        description: product.description ?? undefined,
        skin_types: product.skin_types ?? [],
        concerns: product.concerns ?? [],
        key_ingredients: product.key_ingredients ?? [],
        free_from: product.free_from ?? [],
        variants: (product.variants ?? []).map((v) => ({
          id: v.id,
          name: v.name,
          price: v.price ?? null,
          stock: v.stock ?? 0,
        })),
      });
    } else {
      setEditingProduct(null);
      form.resetFields();
    }
    // Reset file da staged
    setStagedFiles([]);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingProduct(null);
    form.resetFields();
    setStagedFiles([]);
  };

  const handleSubmit = (values: ProductFormValues) => {
    // Chuan hoa variants: bo dong rong, gan id, ep number.
    // Khong co bien the -> null de BE luu NULL (khong phai mang rong).
    const normalized = normalizeVariants(values.variants);
    const payload = {
      ...values,
      variants: normalized.length ? normalized : null,
      // San pham co bien the -> `stock` la gia tri dan xuat (= tong stock
      // variants). BE se tinh lai, gui len de UI hien thi dung ngay.
      stock: normalized.length
        ? normalized.reduce((sum, v) => sum + (v.stock ?? 0), 0)
        : values.stock,
    };

    if (editingProduct) {
      updateMutation.mutate({ id: editingProduct.id, ...payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: 'Ảnh',
      dataIndex: 'image_url',
      width: 90,
      render: (_: unknown, record: AdminProduct) => {
        const thumb =
          record.images?.find((img) => img.is_main)?.image_urls?.thumb ??
          record.images?.[0]?.image_urls?.thumb ??
          record.image_url;
        if (!thumb) {
          return (
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 8,
                background: colors.galleryPlaceholder,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <PictureOutlined style={{ color: colors.placeholderIcon }} />
            </div>
          );
        }
        return (
          <Image
            src={thumb}
            alt={record.name}
            width={56}
            height={56}
            style={{ objectFit: 'cover', borderRadius: 8 }}
            preview={false}
          />
        );
      },
    },
    { title: 'Tên sản phẩm', dataIndex: 'name' },
    { title: 'Danh mục', dataIndex: ['category', 'name'] },
    { title: 'Thương hiệu', dataIndex: ['brand', 'name'] },
    {
      title: 'Giá',
      dataIndex: 'price',
      render: (price: number, record: AdminProduct) =>
        record.sale_price ? (
          <>
            <Text delete>{formatPrice(price)}</Text>
            <br />
            <Text strong style={{ color: colors.primary }}>
              {formatPrice(record.sale_price)}
            </Text>
          </>
        ) : (
          <Text strong>{formatPrice(price)}</Text>
        ),
    },
    { title: 'Stock', dataIndex: 'stock' },
    {
      title: 'Biến thể',
      dataIndex: 'variants',
      render: (variants: VariantFormRow[] | null | undefined) =>
        variants?.length ? (
          <Tag color="blue">{variants.length} phân loại</Tag>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>{active ? 'Hoạt động' : 'Ẩn'}</Tag>
      ),
    },
    {
      title: '',
      render: (_: unknown, record: AdminProduct) => (
        <Space>
          <Tooltip title="Quản lý ảnh">
            <Button
              type="link"
              icon={<PictureOutlined />}
              onClick={() => setGalleryProduct(record)}
            />
          </Tooltip>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          />
          <Popconfirm
            title="Xóa sản phẩm này?"
            onConfirm={() => deleteMutation.mutate(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={2}>Quản lý sản phẩm</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
          Thêm sản phẩm
        </Button>
      </div>

      <Card>
        <Table
          dataSource={products}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={editingProduct ? 'Sửa sản phẩm' : 'Thêm sản phẩm mới'}
        open={isModalOpen}
        onCancel={handleCloseModal}
        footer={null}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Tên sản phẩm" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Space style={{ width: '100%' }}>
            <Form.Item name="price" label="Giá" rules={[{ required: true }]} style={{ flex: 1 }}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="sale_price" label="Giá khuyến mãi" style={{ flex: 1 }}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </Space>

          <Space style={{ width: '100%' }}>
            <Form.Item
              name="stock"
              label="Stock"
              rules={hasVariantRows ? [] : [{ required: true }]}
              style={{ flex: 1 }}
              extra={
                hasVariantRows
                  ? 'Tự tính = tổng stock các biến thể'
                  : undefined
              }
            >
              <InputNumber
                min={0}
                style={{ width: '100%' }}
                disabled={hasVariantRows}
                placeholder={hasVariantRows ? 'Tự động tính' : undefined}
              />
            </Form.Item>

            <Form.Item
              name="category_id"
              label="Danh mục"
              rules={[{ required: true }]}
              style={{ flex: 1 }}
            >
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="Chọn danh mục"
                options={categories?.map((c) => ({ value: c.id, label: c.name }))}
              />
            </Form.Item>
          </Space>

          <Form.Item name="brand_id" label="Thương hiệu" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Chọn thương hiệu"
              options={brands?.map((b) => ({ value: b.id, label: b.name }))}
            />
          </Form.Item>

          <Form.Item name="skin_types" label="Loại da phù hợp">
            <Select
              mode="multiple"
              placeholder="Chọn loại da"
              options={SKIN_TYPES}
            />
          </Form.Item>

          <Form.Item name="concerns" label="Vấn đề da giải quyết">
            <Select mode="multiple" placeholder="Chọn vấn đề da" options={CONCERNS} />
          </Form.Item>

          <Space style={{ width: '100%' }}>
            <Form.Item name="key_ingredients" label="Thành phần chính" style={{ flex: 1 }}>
              <Select mode="tags" placeholder="Nhập thành phần" />
            </Form.Item>

            <Form.Item name="free_from" label="Không chứa" style={{ flex: 1 }}>
              <Select mode="tags" placeholder="Nhập thành phần loại trừ" />
            </Form.Item>
          </Space>

          <Form.Item name="description" label="Mô tả">
            <Input.TextArea rows={3} />
          </Form.Item>

          {/* Bien the (phan loai) - dung Form.List de them/xoa dong */}
          <Form.Item
            label="Biến thể (phân loại)"
            extra="Để trống nếu sản phẩm không có phân loại. Mỗi biến thể có giá và tồn kho riêng."
          >
            <Form.List name="variants">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field) => (
                    <Space key={field.key} align="start" style={{ marginBottom: 8 }}>
                      <Form.Item
                        {...field}
                        name={[field.name, 'id']}
                        label="ID"
                        rules={[{ required: true, message: 'Cần ID' }]}
                      >
                        <Input placeholder="v1" style={{ width: 90 }} />
                      </Form.Item>

                      <Form.Item
                        {...field}
                        name={[field.name, 'name']}
                        label="Tên"
                        rules={[{ required: true, message: 'Cần tên biến thể' }]}
                      >
                        <Input placeholder="Đỏ Ruby" style={{ width: 160 }} />
                      </Form.Item>

                      <Form.Item
                        {...field}
                        name={[field.name, 'price']}
                        label="Giá"
                      >
                        <InputNumber
                          min={0}
                          step={1000}
                          placeholder="350000"
                          style={{ width: 140 }}
                        />
                      </Form.Item>

                      <Form.Item
                        {...field}
                        name={[field.name, 'stock']}
                        label="Stock"
                      >
                        <InputNumber min={0} placeholder="20" style={{ width: 100 }} />
                      </Form.Item>

                      <Button
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => remove(field.name)}
                      />
                    </Space>
                  ))}

                  <Button
                    type="dashed"
                    block
                    icon={<PlusOutlined />}
                    onClick={() => add({ id: undefined, name: '', price: null, stock: 0 })}
                  >
                    Thêm biến thể
                  </Button>
                </>
              )}
            </Form.List>
          </Form.Item>

          {/* Phan quan ly anh san pham */}
          <Form.Item label="Ảnh sản phẩm">
            <ProductImageManager
              productId={editingProduct?.id}
              stagedFiles={stagedFiles}
              onStagedFilesChange={setStagedFiles}
              disabled={
                createMutation.isPending ||
                updateMutation.isPending ||
                deleteMutation.isPending
              }
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingProduct ? 'Cập nhật' : 'Tạo mới'}
              </Button>
              <Button onClick={handleCloseModal}>Hủy</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Modal quan ly anh rieng */}
      <ProductImageGalleryModal
        open={Boolean(galleryProduct)}
        productId={galleryProduct?.id ?? null}
        productName={galleryProduct?.name}
        onClose={() => setGalleryProduct(null)}
      />

      {/* Upload file anh da staged sau khi tao san pham */}
      <ProductStagedUploader
        pending={pendingUpload}
        onDone={() => setPendingUpload(null)}
      />
    </div>
  );
}
