"""Trang thai don hang - nguon su that thu cho backend.

NGUYEN TAC:
- Noi luu trang thai (DB, API) LUON luu bang MA tieng Anh (`pending`,
  `confirmed`, ...). MA la dinh danh, khong phai noi dung hien thi.
- Nhan tieng Viet CHI dung o tang hien thi. Backend can cau thong bao loi
  cho admin thi dung `label_for` de tra ve tieng Viet - tranh thong bao
  tron ma tieng Anh va tieng Viet (VD: "Khong the chuyen tu pending sang
  shipping").

FE dich MA -> tieng Viet bang `ORDER_STATUS_TEXT`
(`frontend/src/utils/constants.ts`). Hai noi PHAI khop nhau.
"""

# --- Ma trang thai ---
PENDING = "pending"
CONFIRMED = "confirmed"
PACKING = "packing"
SHIPPING = "shipping"
DELIVERED = "delivered"
CANCELLED = "cancelled"

#: Trang thai khoi tao don (user checkout).
INITIAL_STATUS = PENDING

#: Nhan tieng Viet cho thong bao loi.
STATUS_LABELS_VI: dict[str, str] = {
    PENDING: "Chờ xác nhận",
    CONFIRMED: "Đã xác nhận",
    PACKING: "Đang đóng gói",
    SHIPPING: "Đang giao hàng",
    DELIVERED: "Đã giao hàng",
    CANCELLED: "Đã hủy",
}


def label_for(status: str) -> str:
    """Nhan tieng Viet cua trang thai.

    Tra ve chinh `status` khi la trang thai la (khong nam trong bang) - an toan
    khi hien thi, khong bao gio render `undefined`.
    """
    return STATUS_LABELS_VI.get(status, status)
