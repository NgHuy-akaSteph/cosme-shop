"""Pytest fixtures - DB test rieng + HTTP client.

QUAN TRONG: test dung `TEST_DATABASE_URL`. Neu bien nay khong duoc dat,
fixture se skip toan bo test suite de khong vo tinh xoa du lieu DB dev.

Neu DB test khong the la database rieng (vd Neon free tier chi co 1 DB),
dat them `TEST_DATABASE_SCHEMA` de chay trong schema rieng biet lap
(tranh xoa bang `public` cua DB dev).

Engine tao o scope=function + NullPool de moi test co event loop rieng
(tranh loi "Task got Future attached to a different loop").

LUU Y QUAN TRONG (Neon/pgBouncer):
- `connect_args["server_settings"]` bi proxy BO QUA -> phai `SET search_path` bang SQL.
- `Base.metadata.create_all` bo qua `search_path` (dung `pg_table_is_visible`) ->
  se KHONG tao table trong schema test ma thay vao do dung table trong `public`.
  Vi vay tao table bang metadata copy voi `schema=TEST_DATABASE_SCHEMA`.
- Fixture `_prepare_schema` verify `current_schema()` truocc khi truncate,
  fail som neu connection tro sai schema (tranh xoa du lieu dev).
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import MetaData, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.db.session import get_db

# Import model de da duy nhat Base.metadata
import app.db.session  # noqa: F401,E402

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
TEST_DATABASE_SCHEMA = os.getenv("TEST_DATABASE_SCHEMA", "")


def _strip_pooler(url: str) -> str:
    """Loai bo '-pooler' khoi host Neon.

    Neon pooler (pgBouncer) giu `search_path` o server-side -> moi connection
    sau do se mac dinh tro toi schema cua connection truoc. Dieu nay lam
    `SET search_path` lan truoc pollute DB dev. Direct endpoint moi tao
    session moi cho moi connection.
    """
    return url.replace("-pooler.", ".")


def _build_schema_metadata(schema: str) -> MetaData:
    """Copy Base.metadata sang schema cu the (giữ nguyên tên bang)."""
    metadata = MetaData(schema=schema)
    for table in Base.metadata.sorted_tables:
        table.to_metadata(metadata, schema=schema)
    return metadata


def _qualified_tables(schema: str) -> list[str]:
    """Danh sach bang da qualify theo schema de truncate dung cho."""
    return sorted(
        f'"{schema}"."{table.name}"' for table in Base.metadata.sorted_tables
    )


async def _get_existing_indexes(conn, schema: str) -> dict[str, set[str]]:
    """Danh sach index thuc te cua moi bang trong schema (theo ten index)."""
    result = await conn.execute(
        text(
            """
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE schemaname = :schema
            """
        ),
        {"schema": schema},
    )
    indexes: dict[str, set[str]] = {}
    for table_name, index_name in result:
        indexes.setdefault(table_name, set()).add(index_name)
    return indexes


async def _drop_outdated_tables(conn, metadata: MetaData, schema: str) -> list[str]:
    """
    Drop cac bang co schema khong khop voi model hien tai.

    `metadata.create_all` chi tao bang con THIEU - bang da ton tai voi cot
    cu (vd truoc khi migration bo cot `url` cua `product_images`) se duoc
    giu nguyen va moi len khong khop model.

    So sanh danh sach cot thuc te voi model; bang khong khop -> drop de
    `create_all` tao lai dung schema moi.

    Args:
        conn: AsyncConnection
        metadata: Metadata cua schema test
        schema: Ten schema

    Returns:
        Danh sach ten bang da drop.
    """
    result = await conn.execute(
        text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
            """
        ),
        {"schema": schema},
    )
    existing: dict[str, set[str]] = {}
    for table_name, column_name in result:
        existing.setdefault(table_name, set()).add(column_name)

    existing_indexes = await _get_existing_indexes(conn, schema)

    dropped: list[str] = []
    for table in metadata.sorted_tables:
        actual = existing.get(table.name)
        if actual is None:
            continue  # Chua ton tai -> create_all se tao moi

        expected = {col.name for col in table.columns}
        columns_match = actual == expected

        # Index cung phai khop: `create_all` KHONG tao them index vao bang
        # da ton tai (chi tao bang thieu). Index unique la lop bao ve cuoi
        # cung (vd `uq_orders_transaction_id`) - thieu index -> test bao ve
        # do se PASS nham ma thuc te khong co rang buoc.
        actual_indexes = existing_indexes.get(table.name, set())
        expected_indexes = {
            idx.name for idx in table.indexes if idx.name is not None
        }
        indexes_match = expected_indexes.issubset(actual_indexes)

        if not (columns_match and indexes_match):
            await conn.execute(
                text(f'DROP TABLE IF EXISTS "{schema}"."{table.name}" CASCADE')
            )
            dropped.append(table.name)

    return dropped


@pytest_asyncio.fixture
async def engine():
    if not TEST_DATABASE_URL:
        pytest.skip(
            "TEST_DATABASE_URL chua duoc dat - bo qua test (tranh xoa nham DB dev)."
        )

    test_engine = create_async_engine(
        _strip_pooler(TEST_DATABASE_URL),
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )

    # Neon (pgBouncer) BO QUA `server_settings` -> search_path phai duoc
    # set bang lenh SQL sau khi connection da duoc tao.
    if TEST_DATABASE_SCHEMA:
        @event.listens_for(test_engine.sync_engine, "connect")
        def _set_search_path(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute(f'SET search_path TO "{TEST_DATABASE_SCHEMA}", public')
            finally:
                cursor.close()

    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def _prepare_schema(engine):
    """Tao schema rieng (neu co) + verify search_path da dung."""
    if not TEST_DATABASE_SCHEMA:
        yield
        return

    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{TEST_DATABASE_SCHEMA}"'))

    # AN TOAN: xac nhan connection dang tro toi schema test, khong phai `public`.
    # Neu `SET search_path` bi proxy bo qua -> fail som thay vi xoa du lieu dev.
    async with engine.connect() as conn:
        active = await conn.execute(text("SELECT current_schema()"))
        active_schema = active.scalar_one()

    if active_schema != TEST_DATABASE_SCHEMA:
        raise RuntimeError(
            f"Test DB dang tro toi schema '{active_schema}' thay vi "
            f"'{TEST_DATABASE_SCHEMA}' — BO QUA test de tranh xoa du lieu dev. "
            "Kiem tra TEST_DATABASE_SCHEMA va quyen ghi DB."
        )

    yield


@pytest_asyncio.fixture
async def db_session(engine, _prepare_schema):
    """Tao table trong schema test, truncate du lieu giua cac test."""
    if TEST_DATABASE_SCHEMA:
        metadata = _build_schema_metadata(TEST_DATABASE_SCHEMA)
        async with engine.begin() as conn:
            # Drop bang co schema cu (migration da doi model) -> create_all
            # tao lai dung cau truc moi.
            dropped = await _drop_outdated_tables(conn, metadata, TEST_DATABASE_SCHEMA)
            if dropped:
                print(f"[test] Drop bang outdated trong schema test: {dropped}")
            await conn.run_sync(metadata.create_all)
        truncate_target = ", ".join(_qualified_tables(TEST_DATABASE_SCHEMA))
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        truncate_target = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)

    # Dam bao bat dau sach
    async with engine.begin() as conn:
        await conn.execute(
            text(f"TRUNCATE TABLE {truncate_target} RESTART IDENTITY CASCADE")
        )

    session_maker = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        yield session

    # Don sach du lieu cho test ke tiep
    async with engine.begin() as conn:
        await conn.execute(
            text(f"TRUNCATE TABLE {truncate_target} RESTART IDENTITY CASCADE")
        )


@pytest_asyncio.fixture
async def client(db_session):
    """HTTP client tro toi app voi dependency DB ghi de bang session test."""
    from app.main import app as fastapi_app

    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    fastapi_app.dependency_overrides.clear()
