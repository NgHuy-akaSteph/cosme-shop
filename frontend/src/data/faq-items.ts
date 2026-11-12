/** Du lieu Q&A (FAQ) tinh trong code - nguon suy duy nhat cho trang /faq */

export interface FaqItem {
  /** Khoa duy nhat, dung lam `key` cho Collapse items */
  id: string;
  /** Nhom chu de, khop voi FAQ_CATEGORIES */
  category: string;
  /** Cau hoi */
  question: string;
  /** Tra loi */
  answer: string;
}

/** Cac nhom chu de hien thi theo thu tu */
export const FAQ_CATEGORIES = [
  'Đặt hàng & Thanh toán',
  'Giao hàng',
  'Đổi trả & Hoàn tiền',
  'Sản phẩm & Tư vấn',
] as const;

export const FAQ_ITEMS: FaqItem[] = [
  {
    id: 'order-process',
    category: 'Đặt hàng & Thanh toán',
    question: 'Làm sao để đặt hàng trên Cosme Shop?',
    answer:
      'Bạn chỉ cần chọn sản phẩm, bấm "Thêm vào giỏ hàng", tiến hành thanh toán và nhập thông tin nhận hàng. Sau khi thanh toán thành công, hệ thống sẽ gửi mã đơn hàng để bạn tra cứu trong mục "Tra cứu đơn hàng".',
  },
  {
    id: 'payment-methods',
    category: 'Đặt hàng & Thanh toán',
    question: 'Cosme Shop chấp nhận những phương thức thanh toán nào?',
    answer:
      'Chúng tôi hỗ trợ thanh toán qua ví điện tử (MoMo, ZaloPay, VNPay), chuyển khoản ngân hàng và thẻ tín dụng/ghi nợ. Thanh toán khi nhận hàng (COD) cũng được áp dụng cho khu vực giao hàng nội thành.',
  },
  {
    id: 'invoice-company',
    category: 'Đặt hàng & Thanh toán',
    question: 'Tôi có thể xuất hóa đơn VAT cho công ty không?',
    answer:
      'Có. Sau khi đơn hàng được xác nhận, bạn liên hệ hotline 1900 6868 kèm mã đơn hàng để được cấp hóa đơn VAT. Với đơn hàng từ 500.000đ trở lên, phí vận chuyển được miễn phí.',
  },
  {
    id: 'order-cancel',
    category: 'Đặt hàng & Thanh toán',
    question: 'Tôi có thể huỷ đơn hàng sau khi đặt không?',
    answer:
      'Bạn có thể huỷ đơn trong vòng 1 giờ sau khi đặt hàng, miễn đơn chưa chuyển sang trạng thái "Đang giao". Liên hệ hotline 1900 6868 hoặc khung chat Fanpage để được hỗ trợ nhanh nhất.',
  },
  {
    id: 'shipping-time',
    category: 'Giao hàng',
    question: 'Thời gian giao hàng mất bao lâu?',
    answer:
      'Đơn hàng nội thành Hà Nội và TP.HCM được giao trong 1-2 ngày làm việc, các tỉnh thành khác trong 2-4 ngày làm việc. Thời gian giao có thể chậm thêm 1 ngày nếu rơi vào ngày lễ hoặc thời tiết xấu.',
  },
  {
    id: 'shipping-fee',
    category: 'Giao hàng',
    question: 'Phí vận chuyển được tính như thế nào?',
    answer:
      'Miễn phí vận chuyển cho đơn hàng từ 500.000đ. Đơn dưới mức này tính phí cố định 30.000đ trong nội thành và tối đa 45.000đ cho các tỉnh thành khác.',
  },
  {
    id: 'shipping-tracking',
    category: 'Giao hàng',
    question: 'Tôi có thể theo dõi đơn hàng đang giao ở đâu?',
    answer:
      'Vào mục "Tra cứu đơn hàng" trên thanh điều hướng, chọn đơn cần xem để biết trạng thái và mã vận đơn. Nếu bạn chưa đăng nhập, hãy đăng nhập bằng tài khoản đã đặt hàng.',
  },
  {
    id: 'return-policy',
    category: 'Đổi trả & Hoàn tiền',
    question: 'Tôi có thể đổi trả sản phẩm trong bao lâu?',
    answer:
      'Bạn được đổi trả trong 7 ngày kể từ khi nhận hàng, với điều kiện sản phẩm chưa sử dụng, còn nguyên tem và bao bì. Riêng mỹ phẩm đã mở seal để kiểm tra vẫn được chấp nhận nếu còn nguyên hạn sử dụng.',
  },
  {
    id: 'refund-process',
    category: 'Đổi trả & Hoàn tiền',
    question: 'Thời gian hoàn tiền mất bao lâu?',
    answer:
      'Sau khi Cosme Shop nhận và kiểm tra sản phẩm trả lại, chúng tôi hoàn tiền trong 3-5 ngày làm việc. Nếu bạn thanh toán qua ví điện tử hoặc thẻ, thời gian hoàn tiền có thể lâu hơn tùy theo bên ngân hàng.',
  },
  {
    id: 'wrong-item',
    category: 'Đổi trả & Hoàn tiền',
    question: 'Tôi nhận sai sản phẩm hoặc sản phẩm bị hỏng thì làm sao?',
    answer:
      'Vui lòng chụp ảnh sản phẩm và vỏ hộp, gửi qua Fanpage hoặc hotline 1900 6868 trong 48 giờ. Chúng tôi sẽ gửi sản phẩm thay thế hoặc hoàn tiền theo yêu cầu của bạn.',
  },
  {
    id: 'authentic-products',
    category: 'Sản phẩm & Tư vấn',
    question: 'Sản phẩm tại Cosme Shop có chính hãng không?',
    answer:
      'Tất cả sản phẩm đều được nhập từ nhà phân phối và nhà sản xuất chính hãng, có tem truy xuất nguồn gốc. Nếu phát hiện sản phẩm không chính hãng, chúng tôi hoàn tiền gấp 2 lần giá trị đơn hàng.',
  },
  {
    id: 'skin-consultation',
    category: 'Sản phẩm & Tư vấn',
    question: 'Tôi không biết nên chọn sản phẩm cho loại da của mình.',
    answer:
      'Mỗi sản phẩm trên website đều có thông tin loại da phù hợp, thành phần nổi bật và các mối lo da được đề xuất. Bạn cũng có thể nhắn Fanpage hoặc gọi 1900 6868 để được đội ngũ tư vấn da gợi ý sản phẩm phù hợp.',
  },
  {
    id: 'product-authenticity-check',
    category: 'Sản phẩm & Tư vấn',
    question: 'Làm sao kiểm tra mã tem truy xuất nguồn gốc?',
    answer:
      'Trên mỗi sản phẩm có tem truy xuất với mã QR. Dùng điện thoại quét mã, truy cập đường dẫn hiển thị và đối chiếu thông tin với tem trên bao bì để xác nhận hàng chính hãng.',
  },
];
