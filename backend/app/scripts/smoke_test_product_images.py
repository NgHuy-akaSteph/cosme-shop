"""
Smoke test API anh san pham - chay truc tiep voi DB dev (khong dung pytest).

Kiem tra vong tron: upload -> list -> set-main -> reorder -> xoa.

An toan:
- Tao product tam rieng de khong dung du lieu san pham that.
- Mock `upload_image` va `delete_image` -> KHONG goi Cloudinary that.
- Xoa product tam o cuoi (cascade xoa anh).

Usage:
    cd backend && .venv/bin/python -m app.scripts.smoke_test_product_images
"""

import asyncio
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from httpx import ASGITransport, AsyncClient

from app.db.session import AsyncSessionLocal, get_db
from app.main import app
from app.model.product import Product
from app.service import product_image_service

JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 100

_counter = {"n": 0}


def fake_upload(file, folder=None, filename=None):
    _counter["n"] += 1
    n = _counter["n"]
    # Timestamp de public_id luon duy nhat (tranh trung voi asset con la
    # tu lan chay truoc da crash giua chung).
    public_id = f"cosme-shop/products/smoke/asset{time.time()}_{n}"
    return {
        "public_id": public_id,
        "url": f"https://res.cloudinary.com/test/image/upload/{public_id}.jpg",
        "secure_url": f"https://res.cloudinary.com/test/image/upload/{public_id}.jpg",
        "width": 1600,
        "height": 1600,
        "format": "jpg",
    }


def fake_delete(public_id):
    """Mock xoa asset Cloudinary - KHONG goi API that (asset gia)."""
    return {"result": "ok"}


def check(label: str, condition: bool, extra: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" - {extra}" if extra else ""))
    if not condition:
        raise AssertionError(label)


async def create_temp_product() -> int:
    """Tao product tam de test (khong anh, khong dung du lieu that)."""
    async with AsyncSessionLocal() as db:
        product = Product(
            name="[SMOKE TEST] Product tam",
            slug=f"smoke-test-{int(time.time())}",
            price=100000,
            stock=1,
            category_id=1,
            brand_id=1,
            is_active=False,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product.id


async def delete_temp_product(product_id: int) -> None:
    """Xoa product tam (cascade xoa anh)."""
    async with AsyncSessionLocal() as db:
        product = await db.get(Product, product_id)
        if product:
            await db.delete(product)
            await db.commit()


async def main() -> None:
    # Mock Cloudinary - khong goi API that
    product_image_service.upload_image = fake_upload
    product_image_service.delete_image = fake_delete

    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    product_id = await create_temp_product()

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # --- 1. Login admin ---
            print("\n1. Dang nhap admin")
            res = await client.post(
                "/api/auth/login",
                json={"email": "admin@cosme-shop.com", "password": "admin123"},
            )
            if res.status_code != 200:
                print(f"  [!] Login that bai ({res.status_code}): {res.text}")
                print("  [!] Hay chay seed truoc: python -m app.scripts.seed")
                return
            token = res.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            check("Dang nhap thanh cong", True)

            # --- 2. Upload ---
            print("\n2. Upload 2 anh")
            res = await client.post(
                f"/api/upload/product-image/{product_id}",
                files={"file": ("a.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg")},
                headers=headers,
            )
            check("Upload anh 1 -> 201", res.status_code == 201, res.text[:200])
            image1 = res.json()

            res = await client.post(
                f"/api/upload/product-image/{product_id}",
                files={"file": ("b.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg")},
                headers=headers,
            )
            check("Upload anh 2 -> 201", res.status_code == 201, res.text[:200])
            image2 = res.json()

            check("Anh 1 co position 0", image1["position"] == 0, str(image1["position"]))
            check("Anh 2 co position 1", image2["position"] == 1, str(image2["position"]))
            check("Anh 1 la main", image1["is_main"] is True)

            # --- 3. Validate ---
            print("\n3. Validate file khong hop le")
            res = await client.post(
                f"/api/upload/product-image/{product_id}",
                files={"file": ("x.txt", io.BytesIO(b"hello"), "text/plain")},
                headers=headers,
            )
            check("Content-type sai -> 400", res.status_code == 400, str(res.status_code))

            res = await client.post(
                f"/api/upload/product-image/{product_id}",
                files={"file": ("fake.jpg", io.BytesIO(b"not an image"), "image/jpeg")},
                headers=headers,
            )
            check("Magic bytes sai -> 400", res.status_code == 400, str(res.status_code))

            # --- 4. List ---
            print("\n4. Lay danh sach anh")
            res = await client.get(
                f"/api/upload/product-image/product/{product_id}", headers=headers
            )
            check("GET list -> 200", res.status_code == 200)
            images = res.json()
            check("Co 2 anh", len(images) == 2, str(len(images)))
            check("Sap xep theo position", [i["position"] for i in images] == [0, 1])

            # --- 5. Set main ---
            print("\n5. Dat anh 2 lam chinh")
            res = await client.patch(
                f"/api/upload/product-image/{image2['id']}/set-main", headers=headers
            )
            check("set-main -> 200", res.status_code == 200, res.text[:200])
            check("Anh 2 is_main", res.json()["is_main"] is True)

            res = await client.get(
                f"/api/upload/product-image/product/{product_id}", headers=headers
            )
            mains = [i for i in res.json() if i["is_main"]]
            check("Chi con 1 anh main", len(mains) == 1, str(len(mains)))
            check("Anh main la anh 2", mains[0]["id"] == image2["id"])

            # --- 6. Reorder ---
            print("\n6. Sap xep lai thu tu")
            res = await client.patch(
                f"/api/upload/product-image/{product_id}/reorder",
                json={"image_ids": [image2["id"], image1["id"]]},
                headers=headers,
            )
            check("reorder -> 200", res.status_code == 200, res.text[:200])
            positions = {i["id"]: i["position"] for i in res.json()}
            check("Anh 2 -> position 0", positions[image2["id"]] == 0)
            check("Anh 1 -> position 1", positions[image1["id"]] == 1)

            res = await client.patch(
                f"/api/upload/product-image/{product_id}/reorder",
                json={"image_ids": [image1["id"], 999999]},
                headers=headers,
            )
            check("Reorder ID la -> 400", res.status_code == 400, str(res.status_code))

            # --- 7. Alt text ---
            print("\n7. Cap nhat alt text")
            res = await client.patch(
                f"/api/upload/product-image/{image1['id']}",
                data={"alt_text": "Kem chong nang"},
                headers=headers,
            )
            check("update alt_text -> 200", res.status_code == 200)
            check("alt_text da luu", res.json()["alt_text"] == "Kem chong nang")

            # --- 8. Permission ---
            print("\n8. Kiem tra phan quyen")
            res = await client.post(
                "/api/auth/login",
                json={"email": "user@cosme-shop.com", "password": "user123"},
            )
            if res.status_code == 200:
                user_token = res.json()["data"]["access_token"]
                res = await client.post(
                    f"/api/upload/product-image/{product_id}",
                    files={"file": ("a.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg")},
                    headers={"Authorization": f"Bearer {user_token}"},
                )
                check(
                    "User thuong upload -> 403", res.status_code == 403, str(res.status_code)
                )
            else:
                print("  [SKIP] Khong co user test de kiem tra 403")

            res = await client.post(
                f"/api/upload/product-image/{product_id}",
                files={"file": ("a.jpg", io.BytesIO(JPEG_BYTES), "image/jpeg")},
            )
            check("Khong token -> 401", res.status_code == 401, str(res.status_code))

            # --- 9. Product API ---
            print("\n9. Product API co image_urls")
            res = await client.get(f"/api/products/{product_id}", headers=headers)
            check("GET product -> 200", res.status_code == 200)
            data = res.json()["data"]
            check("Co image_urls", bool(data.get("image_urls")), str(data.get("image_urls")))
            check(
                "image_urls co 3 bien the",
                set(data.get("image_urls", {}).keys()) == {"card", "detail", "thumb"},
            )
            check(
                "images[] co image_urls",
                all("image_urls" in img for img in data.get("images", [])),
            )

            # --- 10. Cleanup ---
            print("\n10. Xoa anh")
            for image_id in (image1["id"], image2["id"]):
                res = await client.delete(
                    f"/api/upload/product-image/{image_id}", headers=headers
                )
                check(f"Xoa anh {image_id} -> 200", res.status_code == 200, res.text[:120])

            res = await client.get(
                f"/api/upload/product-image/product/{product_id}", headers=headers
            )
            check("Gallery da sach", len(res.json()) == 0, str(len(res.json())))

        print("\n" + "=" * 50)
        print("SMOKE TEST PASS - tat ca luong chinh hoat dong")
        print("=" * 50)
    finally:
        await delete_temp_product(product_id)
        app.dependency_overrides.clear()
        print(f"\nDa xoa product tam (id={product_id})")


if __name__ == "__main__":
    asyncio.run(main())
