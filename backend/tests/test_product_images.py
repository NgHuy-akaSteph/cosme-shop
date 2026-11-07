"""
Test cho API upload/quan ly anh san pham.

KHONG goi Cloudinary that - ham `upload_image` trong service duoc monkeypatch
de tra ve ket qua gia.

Luong test dung `client` fixture (HTTP client tro toi app voi DB test).
"""

import io

import pytest
from sqlalchemy import select

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories

from app.model.order_item import OrderItem
from app.model.order import Order
from app.model.product_image import ProductImage
from app.service import product_image_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Magic bytes hop le cho tung dinh dang
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 100
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 100
# GIF hop le ve magic bytes nhung KHONG duoc phep (khong co trong
# ALLOWED_UPLOAD_FORMATS cua Cloudinary) -> API phai chan o lop validate.
GIF_BYTES = b"GIF89a" + b"\x00" * 100


@pytest.fixture
def mock_cloudinary(monkeypatch):
    """Monkeypatch `upload_image` trong service - khong goi Cloudinary that."""
    counter = {"n": 0}

    def fake_upload(file, folder=None, filename=None):
        counter["n"] += 1
        n = counter["n"]
        public_id = f"cosme-shop/products/test/asset{n}"
        return {
            "public_id": public_id,
            "url": f"https://res.cloudinary.com/test/image/upload/{public_id}.jpg",
            "secure_url": f"https://res.cloudinary.com/test/image/upload/{public_id}.jpg",
            "width": 1600,
            "height": 1600,
            "format": "jpg",
        }

    monkeypatch.setattr(product_image_service, "upload_image", fake_upload)
    return counter


def make_upload(content: bytes, filename: str = "test.jpg", content_type: str = "image/jpeg"):
    """Tao payload multipart cho endpoint upload."""
    return {
        "file": (filename, io.BytesIO(content), content_type),
    }


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_upload_product_image(client, login, product, mock_cloudinary):
    """Admin upload anh -> 201, tao row trong DB, anh dau tien la main."""
    headers = await login("admin@example.com", "admin123")

    res = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES),
        headers=headers,
    )

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["public_id"] == "cosme-shop/products/test/asset1"
    assert body["secure_url"].startswith("https://")
    assert body["position"] == 0
    assert body["is_main"] is True


@pytest.mark.asyncio
async def test_regular_user_cannot_upload(client, login, product, mock_cloudinary):
    """User thuong bi tu choi khi upload."""
    headers = await login("user@example.com", "user123")

    res = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES),
        headers=headers,
    )

    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_upload_requires_auth(client, product, mock_cloudinary):
    """Khong co token -> 401."""
    res = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES),
    )

    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_upload_rejects_invalid_content_type(client, login, product, mock_cloudinary):
    """Content-type khong phai anh -> 400."""
    headers = await login("admin@example.com", "admin123")

    res = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(b"not an image", "doc.txt", "text/plain"),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert res.json()["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_rejects_fake_image(client, login, product, mock_cloudinary):
    """Content-type gia anh nhung magic bytes sai -> 400."""
    headers = await login("admin@example.com", "admin123")

    res = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(b"this is a text file, not an image", "fake.jpg", "image/jpeg"),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert res.json()["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_rejects_file_too_large(client, login, product, mock_cloudinary):
    """File qua 5MB -> 400."""
    headers = await login("admin@example.com", "admin123")

    res = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES + b"\x00" * (5 * 1024 * 1024 + 100)),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert res.json()["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_upload_to_nonexistent_product(client, login, mock_cloudinary):
    """Upload vao product khong ton tai -> 404."""
    headers = await login("admin@example.com", "admin123")

    res = await client.post(
        "/api/upload/product-image/999999",
        files=make_upload(JPEG_BYTES),
        headers=headers,
    )

    assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_upload_png_and_webp_accepted(client, login, product, mock_cloudinary):
    """PNG va WEBP hop le deu duoc accept."""
    headers = await login("admin@example.com", "admin123")

    for content, filename, ctype in [
        (PNG_BYTES, "a.png", "image/png"),
        (WEBP_BYTES, "b.webp", "image/webp"),
    ]:
        res = await client.post(
            f"/api/upload/product-image/{product.id}",
            files=make_upload(content, filename, ctype),
            headers=headers,
        )
        assert res.status_code == 201, res.text


@pytest.mark.asyncio
async def test_upload_rejects_gif(client, login, product, mock_cloudinary):
    """
    GIF bi Cloudinary chan (allowed_formats khong co gif) -> API phai chan
    o lop validate voi 400, khong de user thay loi 502 "Cloudinary that bai".
    """
    headers = await login("admin@example.com", "admin123")

    res = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(GIF_BYTES, "a.gif", "image/gif"),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert res.json()["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_duplicate_public_id_returns_409(
    client, login, product, mock_cloudinary
):
    """Upload trung `public_id` -> 409 CONFLICT (khong phai 500)."""
    headers = await login("admin@example.com", "admin123")

    # Mock upload tra cung public_id cho moi lan -> vi pham unique constraint
    monkey = mock_cloudinary
    assert monkey is not None

    res1 = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES, "a.jpg"),
        headers=headers,
    )
    assert res1.status_code == 201, res1.text

    # Lan 2 se sinh public_id moi (counter tang) -> ep trung bang cach
    # tai lai counter ve gia tri truoc.
    mock_cloudinary["n"] = 0

    res2 = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES, "a.jpg"),
        headers=headers,
    )

    assert res2.status_code == 409, res2.text
    assert res2.json()["code"] == "DUPLICATE_IMAGE"


# ---------------------------------------------------------------------------
# Position / is_main
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_second_image_gets_next_position(client, login, product, mock_cloudinary):
    """Anh thu 2 phai co position = 1 (khong dung position cua anh main)."""
    headers = await login("admin@example.com", "admin123")

    res1 = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES, "first.jpg"),
        headers=headers,
    )
    assert res1.status_code == 201
    assert res1.json()["position"] == 0

    res2 = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(PNG_BYTES, "second.png", "image/png"),
        headers=headers,
    )
    assert res2.status_code == 201
    # Quan trong: anh main (position 0) khong bi ghi de
    assert res2.json()["position"] == 1


@pytest.mark.asyncio
async def test_set_main_unsets_previous_main(client, login, product, mock_cloudinary):
    """Dat anh chinh -> anh truoc do bi unset, chi con 1 anh main."""
    headers = await login("admin@example.com", "admin123")

    res1 = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES, "first.jpg"),
        headers=headers,
    )
    res2 = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(PNG_BYTES, "second.png", "image/png"),
        headers=headers,
    )
    image2_id = res2.json()["id"]

    res = await client.patch(
        f"/api/upload/product-image/{image2_id}/set-main",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["is_main"] is True

    # Anh truoc do khong con la main
    res_check = await client.get(
        f"/api/upload/product-image/product/{product.id}",
        headers=headers,
    )
    images = res_check.json()
    mains = [img for img in images if img["is_main"]]
    assert len(mains) == 1
    assert mains[0]["id"] == image2_id


@pytest.mark.asyncio
async def test_set_main_moves_image_to_front(client, login, product, mock_cloudinary):
    """
    Dat anh chinh -> anh do phai len dau gallery (position 0) va cac anh
    khac lùi xuong, vi storefront hien thi theo `position`.
    """
    headers = await login("admin@example.com", "admin123")

    ids = []
    for name in ["a.jpg", "b.jpg", "c.jpg"]:
        res = await client.post(
            f"/api/upload/product-image/{product.id}",
            files=make_upload(JPEG_BYTES, name),
            headers=headers,
        )
        ids.append(res.json()["id"])

    # Dat anh thu 3 lam main
    res = await client.patch(
        f"/api/upload/product-image/{ids[2]}/set-main",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["position"] == 0

    res_check = await client.get(
        f"/api/upload/product-image/product/{product.id}", headers=headers
    )
    images = res_check.json()
    assert [img["id"] for img in images] == [ids[2], ids[0], ids[1]]
    assert [img["position"] for img in images] == [0, 1, 2]


@pytest.mark.asyncio
async def test_update_image_with_is_main_promotes_to_front(
    client, login, product, mock_cloudinary
):
    """
    PATCH `is_main=true` (khong dung endpoint set-main) cung phai dua anh len
    dau gallery - giữ invariant "ảnh chính luôn ở đầu".
    """
    headers = await login("admin@example.com", "admin123")

    ids = []
    for name in ["a.jpg", "b.jpg"]:
        res = await client.post(
            f"/api/upload/product-image/{product.id}",
            files=make_upload(JPEG_BYTES, name),
            headers=headers,
        )
        ids.append(res.json()["id"])

    res = await client.patch(
        f"/api/upload/product-image/{ids[1]}",
        data={"is_main": "true"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["is_main"] is True
    assert res.json()["position"] == 0

    res_check = await client.get(
        f"/api/upload/product-image/product/{product.id}", headers=headers
    )
    images = res_check.json()
    assert [img["id"] for img in images] == [ids[1], ids[0]]
    assert len([img for img in images if img["is_main"]]) == 1


@pytest.mark.asyncio
async def test_upload_with_is_main_true_goes_to_front(
    client, login, product, mock_cloudinary
):
    """
    Upload 1 anh moi voi `is_main=true` -> anh do phai len dau gallery
    (position 0) va cac anh cu lùi xuong, giu invariant "anh main luon dau".
    """
    headers = await login("admin@example.com", "admin123")

    res1 = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES, "first.jpg"),
        headers=headers,
    )
    first_id = res1.json()["id"]

    res2 = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(PNG_BYTES, "second.png", "image/png"),
        data={"is_main": "true"},
        headers=headers,
    )
    assert res2.status_code == 201, res2.text
    second_id = res2.json()["id"]
    assert res2.json()["is_main"] is True
    assert res2.json()["position"] == 0

    res_check = await client.get(
        f"/api/upload/product-image/product/{product.id}", headers=headers
    )
    images = res_check.json()
    assert [img["id"] for img in images] == [second_id, first_id]
    assert [img["position"] for img in images] == [0, 1]
    assert len([img for img in images if img["is_main"]]) == 1


@pytest.mark.asyncio
async def test_delete_main_promotes_remaining_image(
    client, login, product, db_session, mock_cloudinary
):
    """Xoa anh chinh -> anh con lai dau tien duoc lam main."""
    headers = await login("admin@example.com", "admin123")

    res1 = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES, "first.jpg"),
        headers=headers,
    )
    await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(PNG_BYTES, "second.png", "image/png"),
        headers=headers,
    )

    first_id = res1.json()["id"]
    res = await client.delete(
        f"/api/upload/product-image/{first_id}",
        headers=headers,
    )
    assert res.status_code == 200, res.text

    res_check = await client.get(
        f"/api/upload/product-image/product/{product.id}",
        headers=headers,
    )
    images = res_check.json()
    assert len(images) == 1
    assert images[0]["is_main"] is True
    # Anh con lai phai duoc day len dau gallery (position 0)
    assert images[0]["position"] == 0


@pytest.mark.asyncio
async def test_delete_image_used_in_orders_keeps_cloudinary_asset(
    client, login, product, db_session, monkeypatch
):
    """
    Anh da duoc snapshot vao don hang -> KHONG xoa asset Cloudinary,
    chi go row khoi gallery.
    """
    headers = await login("admin@example.com", "admin123")

    # Tao anh trong DB truc tiep
    image = ProductImage(
        product_id=product.id,
        public_id="cosme-shop/products/test/used",
        secure_url="https://res.cloudinary.com/test/image/upload/used.jpg",
        position=0,
        is_main=True,
    )
    db_session.add(image)
    await db_session.commit()
    await db_session.refresh(image)

    # Tao don hang co snapshot URL anh do
    order = Order(
        user_id=1,
        order_code="ORD-TEST-USED",
        status="pending",
        subtotal=100000,
        total=100000,
        payment_method="sepay",
        payment_status="unpaid",
        shipping_name="Nguyen Van A",
        shipping_phone="0900000000",
        shipping_address="Ha Noi",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    db_session.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            product_price=100000,
            product_image=image.secure_url,
            qty=1,
            subtotal=100000,
        )
    )
    await db_session.commit()

    # Monkeypatch delete_image de theo doi co duoc goi hay khong
    called = {"destroy": False}

    def fake_delete(public_id):
        called["destroy"] = True
        return {"result": "ok"}

    monkeypatch.setattr(product_image_service, "delete_image", fake_delete)

    res = await client.delete(
        f"/api/upload/product-image/{image.id}",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["asset_kept"] is True
    # Cloudinary KHONG bi goi
    assert called["destroy"] is False

    # Row trong DB da bi xoa
    remaining = await db_session.execute(
        select(ProductImage).where(ProductImage.id == image.id)
    )
    assert remaining.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Reorder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_images(client, login, product, mock_cloudinary):
    """Sap xep lai thu tu anh theo danh sach ID client gui len."""
    headers = await login("admin@example.com", "admin123")

    ids = []
    for name in ["a.jpg", "b.jpg", "c.jpg"]:
        res = await client.post(
            f"/api/upload/product-image/{product.id}",
            files=make_upload(JPEG_BYTES, name),
            headers=headers,
        )
        ids.append(res.json()["id"])

    # Dao thu tu: c, a, b
    new_order = [ids[2], ids[0], ids[1]]
    res = await client.patch(
        f"/api/upload/product-image/{product.id}/reorder",
        json={"image_ids": new_order},
        headers=headers,
    )
    assert res.status_code == 200, res.text

    positions = {img["id"]: img["position"] for img in res.json()}
    assert positions[ids[2]] == 0
    assert positions[ids[0]] == 1
    assert positions[ids[1]] == 2


@pytest.mark.asyncio
async def test_reorder_rejects_foreign_image_id(client, login, product, mock_cloudinary):
    """ID anh khong thuoc product -> 400."""
    headers = await login("admin@example.com", "admin123")

    res = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES),
        headers=headers,
    )
    image_id = res.json()["id"]

    res = await client.patch(
        f"/api/upload/product-image/{product.id}/reorder",
        json={"image_ids": [image_id, 999999]},
        headers=headers,
    )
    assert res.status_code == 400, res.text
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_reorder_rejects_duplicate_ids(client, login, product, mock_cloudinary):
    """Danh sach ID trung lap -> 400."""
    headers = await login("admin@example.com", "admin123")

    res = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES),
        headers=headers,
    )
    image_id = res.json()["id"]

    res = await client.patch(
        f"/api/upload/product-image/{product.id}/reorder",
        json={"image_ids": [image_id, image_id]},
        headers=headers,
    )
    assert res.status_code == 400, res.text


# ---------------------------------------------------------------------------
# List / metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_product_images(client, login, product, mock_cloudinary):
    """GET danh sach anh tra ve theo thu tu position."""
    headers = await login("admin@example.com", "admin123")

    for name in ["a.jpg", "b.jpg"]:
        await client.post(
            f"/api/upload/product-image/{product.id}",
            files=make_upload(JPEG_BYTES, name),
            headers=headers,
        )

    res = await client.get(
        f"/api/upload/product-image/product/{product.id}",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    images = res.json()
    assert len(images) == 2
    assert images[0]["position"] == 0
    assert images[1]["position"] == 1


@pytest.mark.asyncio
async def test_list_images_requires_admin(client, login, product, mock_cloudinary):
    """User thuong khong xem duoc danh sach anh qua API upload."""
    headers = await login("user@example.com", "user123")

    res = await client.get(
        f"/api/upload/product-image/product/{product.id}",
        headers=headers,
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_update_alt_text(client, login, product, mock_cloudinary):
    """Cap nhat alt_text cua anh."""
    headers = await login("admin@example.com", "admin123")

    res_upload = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES),
        headers=headers,
    )
    image_id = res_upload.json()["id"]

    res = await client.patch(
        f"/api/upload/product-image/{image_id}",
        data={"alt_text": "Kem chong nang"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["alt_text"] == "Kem chong nang"


@pytest.mark.asyncio
async def test_delete_nonexistent_image_returns_404(client, login, mock_cloudinary):
    """Xoa anh khong ton tai -> 404."""
    headers = await login("admin@example.com", "admin123")

    res = await client.delete(
        "/api/upload/product-image/999999",
        headers=headers,
    )
    assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_set_main_integrity_error_returns_409(
    client, login, product, mock_cloudinary, monkeypatch
):
    """
    Race condition khi 2 request set-main chay song song -> unique index
    `uq_product_images_one_main` reject -> API phai tra 409, khong phai 500.
    """
    from sqlalchemy.exc import IntegrityError

    headers = await login("admin@example.com", "admin123")

    res_upload = await client.post(
        f"/api/upload/product-image/{product.id}",
        files=make_upload(JPEG_BYTES),
        headers=headers,
    )
    image_id = res_upload.json()["id"]

    def raise_integrity(*args, **kwargs):
        raise IntegrityError("UPDATE", {}, Exception("uq_product_images_one_main"))

    monkeypatch.setattr(product_image_service, "set_main_image", raise_integrity)

    res = await client.patch(
        f"/api/upload/product-image/{image_id}/set-main",
        headers=headers,
    )

    assert res.status_code == 409, res.text
    assert res.json()["code"] == "CONFLICT"
