# Thư mục ảnh minh họa

Thư mục này chứa ảnh giao diện được chèn vào báo cáo `../Bao_cao_BTL_PTHT_TMDT.md`.

## Quy tắc đặt tên

Tên tệp theo định dạng `hinh-4-<số hình>.png`, trong đó `<số hình>` là số hình hai chữ số trong báo cáo.

| Tệp | Nội dung | Mục trong báo cáo |
| --- | --- | --- |
| `hinh-4-02.png` | Trang chủ | Mục 4.3.1 |
| `hinh-4-03.png` | Danh sách sản phẩm | Mục 4.3.2 |
| `hinh-4-04.png` | Chi tiết sản phẩm | Mục 4.3.3 |
| `hinh-4-05.png` | Kết quả tìm kiếm | Mục 4.3.4 |
| `hinh-4-06.png` | Đăng ký tài khoản | Mục 4.3.5 |
| `hinh-4-07.png` | Đăng nhập | Mục 4.3.6 |
| `hinh-4-08.png` | Giỏ hàng | Mục 4.3.7 |
| `hinh-4-09.png` | Xác nhận đặt hàng | Mục 4.3.8 |
| `hinh-4-10.png` | QR thanh toán SePay | Mục 4.3.9 |
| `hinh-4-11.png` | Đơn hàng của tôi | Mục 4.3.10 |
| `hinh-4-12.png` | Chi tiết đơn hàng | Mục 4.3.11 |
| `hinh-4-13.png` | Tài khoản của tôi | Mục 4.3.12 |
| `hinh-4-14.png` | Sản phẩm yêu thích | Mục 4.3.13 |
| `hinh-4-15.png` | Câu hỏi thường gặp | Mục 4.3.14 |
| `hinh-4-16.png` | Liên kết mạng xã hội | Mục 4.3.15 |
| `hinh-4-17.png` | Trang 404 | Mục 4.3.16 |
| `hinh-4-18.png` | Đăng nhập quản trị | Mục 4.4.1 |
| `hinh-4-19.png` | Tổng quan quản trị | Mục 4.4.2 |
| `hinh-4-20.png` | Quản lý sản phẩm | Mục 4.4.3 |
| `hinh-4-21.png` | Biểu mẫu thêm sản phẩm | Mục 4.4.3 |
| `hinh-4-22.png` | Biểu mẫu sửa sản phẩm | Mục 4.4.3 |
| `hinh-4-23.png` | Khung quản lý ảnh sản phẩm | Mục 4.4.3 |
| `hinh-4-24.png` | Quản lý đơn hàng | Mục 4.4.4 |
| `hinh-4-25.png` | Cập nhật trạng thái đơn hàng | Mục 4.4.4 |
| `hinh-4-26.png` | Quản lý người dùng | Mục 4.4.5 |
| `hinh-4-27.png` | Quản lý danh mục | Mục 4.4.6 |
| `hinh-4-28.png` | Quản lý thương hiệu | Mục 4.4.7 |
| `hinh-4-29.png` | Quản lý mã giảm giá | Mục 4.4.8 |

Hình 4.1 là sơ đồ kiến trúc dựng bằng Mermaid nên không cần ảnh chụp.

## Quy trình chụp ảnh

1. Khởi động máy chủ phía sau: `cd backend && python -m uvicorn app.main:app --reload --port 8000`
2. Khởi động giao diện: `cd frontend && npm run dev`
3. Nạp dữ liệu mẫu: `cd backend && python -m app.scripts.seed`
4. Mở <http://localhost:5173>, thực hiện đúng thao tác mô tả trong khối `[CẦN BỔ SUNG ẢNH: ...]` của mục tương ứng trong báo cáo, rồi chụp màn hình.

## Lưu ý bảo mật

- Không chụp màn hình khi mật khẩu đã điền sẵn.
- Không chụp nội dung tệp `.env` hay thông tin kết nối cơ sở dữ liệu.
- Dùng tài khoản dữ liệu mẫu, không dùng tài khoản cá nhân.
- Không hiển thị thông tin định danh cá nhân trên màn hình đơn hàng.
