"""
Migrate anh seed (URL Unsplash) len Cloudinary that.

Anh seed duoc tao voi `public_id` gia (`seed_xxx`) va tro toi URL ngoai
(Unsplash). Sau khi migrate:
- `public_id` tro toi asset that tren Cloudinary
- `secure_url` tro toi URL Cloudinary
- co `width`/`height`/`format` that

Anh dung chung mot URL goc van duoc upload rieng cho moi product vi
`public_id` co UNIQUE constraint.

Usage:
    cd backend && .venv/bin/python -m app.scripts.migrate_seed_images_to_cloudinary
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from sqlalchemy import select

from app.core.cloudinary import upload_image, build_product_folder
from app.db.session import AsyncSessionLocal
from app.model.product_image import ProductImage

# Tien to nhan dien anh seed cu (public_id gia)
SEED_PUBLIC_ID_PREFIX = "seed_"


async def _download_image(url: str, client: httpx.AsyncClient) -> bytes | None:
    """Tai anh tu URL. Tra None neu that bai."""
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.content
    except Exception as exc:
        print(f"  [!] Download failed: {url} - {exc}")
        return None


async def migrate() -> None:
    """Migrate tat ca anh seed chua duoc migrate len Cloudinary."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ProductImage).where(
                ProductImage.public_id.like(f"{SEED_PUBLIC_ID_PREFIX}%")
            )
        )
        images = list(result.scalars().all())

        if not images:
            print("Khong co anh seed nao can migrate.")
            return

        print(f"Tim thay {len(images)} anh seed can migrate.\n")

        # Tai anh goc 1 lan moi URL (tiet kiem bandwidth)
        content_cache: dict[str, bytes | None] = {}

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for index, image in enumerate(images, start=1):
                print(f"[{index}/{len(images)}] product_id={image.product_id}")

                if image.secure_url not in content_cache:
                    content_cache[image.secure_url] = await _download_image(
                        image.secure_url, client
                    )

                content = content_cache[image.secure_url]
                if not content:
                    print("  [-] Bo qua (khong tai duoc anh)")
                    continue

                try:
                    uploaded = upload_image(
                        content,
                        folder=build_product_folder(image.product_id),
                        filename=f"migrate_{image.id}.jpg",
                    )
                except Exception as exc:
                    print(f"  [!] Upload failed: {exc}")
                    continue

                old_public_id = image.public_id
                image.public_id = uploaded["public_id"]
                image.secure_url = uploaded["secure_url"]
                image.width = uploaded.get("width")
                image.height = uploaded.get("height")
                image.format = uploaded.get("format")

                print(f"  [OK] {old_public_id} -> {image.public_id}")

        await db.commit()
        print("\nMigration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
