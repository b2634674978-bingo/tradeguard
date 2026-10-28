"""数据库驱动兼容层：同一套 SQL 同时跑在 SQLite（本地）和 PostgreSQL（云端持久化）。

设计原则
--------
1. **业务 SQL 不感知方言**：`database.py` 继续写带 `?` 占位符的标准 SQL；
   所有差异（占位符、冲突子句、自增、BLOB 类型）集中在本文件翻译。
2. **SQLite 零改动**：本地运行、单元测试、离线演示全部走原生 sqlite3，
   行为与改造前完全一致。
3. **Postgres 走连接池**：云端每次请求都新建 TCP + TLS 连接代价过高
   （Supabase 单次握手 100ms 量级），因此复用连接。
4. **不引入 ORM**：避免 1000 行业务逻辑重写带来的回归风险。

环境变量
--------
DATABASE_URL / TRADEGUARD_DATABASE_URL
    PostgreSQL 连接串；为空则回落到本地 SQLite。
TRADEGUARD_PG_POOL
    Postgres 连接池上限，默认 4。
"""

from __future__ import annotations

import os
import queue
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:  # 本地/离线场景可能没装 psycopg，此时只用 SQLite
    import psycopg
    from psycopg.rows import dict_row

    PSYCOPG_AVAILABLE = True
except ImportError:  # pragma: no cover - 取决于环境
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]
    PSYCOPG_AVAILABLE = False


# --------------------------------------------------------------------------- 方言


def translate_placeholders(sql: str) -> str:
    """把 `?` 占位符换成 `%s`，跳过单引号字面量内部（如 DEFAULT ''）。"""
    if "?" not in sql:
        return sql
    out: list[str] = []
    in_string = False
    for char in sql:
        if char == "'":
            in_string = not in_string
            out.append(char)
        elif char == "?" and not in_string:
            out.append("%s")
        else:
            out.append(char)
    return "".join(out)


# INSERT OR REPLACE 需要冲突目标才能转成 ON CONFLICT DO UPDATE
_CONFLICT_TARGETS: dict[str, tuple[str, ...]] = {
    "meta": ("key",),
}


def translate_statement(sql: str, *, dialect: str = "postgres") -> str:
    """把 SQLite 方言的写入语句翻译成目标方言可执行的形式。

    - `INSERT OR IGNORE` -> `INSERT ... ON CONFLICT DO NOTHING`
    - `INSERT OR REPLACE` -> `INSERT ... ON CONFLICT (<pk>) DO UPDATE SET ...`
      （仅用于 meta 这类以主键为唯一键的小表）
    - PostgreSQL 下 `?` -> `%s`；SQLite 下占位符原样保留
    """
    text = sql.strip()
    lowered = text.lower()
    conflict_suffix = ""

    if lowered.startswith("insert or ignore into"):
        text = "INSERT INTO" + text[len("INSERT OR IGNORE INTO") :]
        conflict_suffix = " ON CONFLICT DO NOTHING"
    elif lowered.startswith("insert or replace into"):
        rest = text[len("INSERT OR REPLACE INTO") :].lstrip()
        table = rest.split("(", 1)[0].strip().split()[0].strip('"').lower()
        target = _CONFLICT_TARGETS.get(table)
        if target is None:
            # 没有声明冲突目标时退化为忽略重复，保证不中断写入
            text = "INSERT INTO" + text[len("INSERT OR REPLACE INTO") :]
            conflict_suffix = " ON CONFLICT DO NOTHING"
        else:
            text = "INSERT INTO" + text[len("INSERT OR REPLACE INTO") :]
            columns = ", ".join(target)
            updates = ", ".join(f"{column} = EXCLUDED.{column}" for column in _non_key_columns(table, target))
            conflict_suffix = f" ON CONFLICT ({columns}) DO UPDATE SET {updates}"

    text = translate_placeholders(text) if dialect == "postgres" else text

    if conflict_suffix:
        text = text.rstrip().rstrip(";").rstrip()
        if " ON CONFLICT" not in text.upper():
            text += conflict_suffix
    return text


def _non_key_columns(table: str, target: tuple[str, ...]) -> tuple[str, ...]:
    # meta 只有 key/value 两列，除主键外的列即为更新目标
    known = {"meta": ("value",)}
    columns = known.get(table, ("value",))
    return tuple(column for column in columns if column not in target) or ("value",)


def split_statements(script: str) -> list[str]:
    """按分号拆分建表脚本（本项目的 DDL 字面量里没有分号，拆分安全）。"""
    statements: list[str] = []
    buffer: list[str] = []
    in_string = False
    for char in script:
        if char == "'":
            in_string = not in_string
        if char == ";" and not in_string:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            continue
        buffer.append(char)
    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


# --------------------------------------------------------------------------- 连接


class SqliteConnection:
    """把 sqlite3 连接包装成兼容层要求的接口。"""

    dialect = "sqlite"

    def __init__(self, raw: sqlite3.Connection):
        self.raw = raw

    def execute(self, sql: str, params: Any = ()) -> Any:
        statement = translate_statement(sql, dialect="sqlite") if _needs_rewrite(sql) else sql
        return self.raw.execute(statement, tuple(params or ()))

    def insert_id(self, sql: str, params: Any = ()) -> int:
        cursor = self.raw.execute(sql, tuple(params or ()))
        return int(cursor.lastrowid)

    def executescript(self, script: str) -> None:
        for statement in split_statements(script):
            self.raw.execute(statement)

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        self.raw.close()


def _needs_rewrite(sql: str) -> bool:
    lowered = sql.lstrip().lower()
    return lowered.startswith("insert or ")


class PgConnection:
    """psycopg 连接的薄包装：负责方言翻译与自增主键回填。"""

    dialect = "postgres"

    def __init__(self, raw: Any):
        self.raw = raw
        # 回滚失败（连接已断）时置位，归还连接池前会被丢弃
        self.broken = [False]

    def execute(self, sql: str, params: Any = ()) -> Any:
        statement = translate_statement(sql)
        values = tuple(params or ())
        if not values:
            return self.raw.execute(statement)
        return self.raw.execute(statement, values)

    def insert_id(self, sql: str, params: Any = ()) -> int:
        statement = translate_statement(sql).rstrip().rstrip(";")
        if "returning" not in statement.lower():
            statement += " RETURNING id"
        values = tuple(params or ())
        cursor = self.raw.execute(statement, values) if values else self.raw.execute(statement)
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("插入后未返回主键")
        if isinstance(row, dict):
            return int(row["id"])
        return int(row[0])

    def executescript(self, script: str) -> None:
        for statement in split_statements(script):
            self.execute(statement)

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        self.raw.close()


# --------------------------------------------------------------------------- 后端


class DatabaseBackend:
    """后端基类：约定 database.py 依赖的最小接口。"""

    name = "base"
    dialect = "sqlite"
    supports_file_backup = True
    pk_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
    blob_type = "BLOB"
    real_type = "REAL"

    @contextmanager
    def connect(self) -> Iterator[Any]:  # pragma: no cover - 抽象
        raise NotImplementedError

    def columns(self, conn: Any, table: str) -> set[str]:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError

    def close(self) -> None:
        return None


class SqliteBackend(DatabaseBackend):
    name = "sqlite"
    dialect = "sqlite"
    supports_file_backup = True

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[SqliteConnection]:
        raw = sqlite3.connect(str(self.path), timeout=20)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA foreign_keys = ON")
        conn = SqliteConnection(raw)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def columns(self, conn: SqliteConnection, table: str) -> set[str]:
        return {row["name"] for row in conn.raw.execute(f"PRAGMA table_info({table})")}

    def describe(self) -> str:
        return f"SQLite · {self.path}"


class PostgresBackend(DatabaseBackend):
    name = "postgres"
    dialect = "postgres"
    supports_file_backup = False
    pk_type = "INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY"
    blob_type = "BYTEA"
    real_type = "DOUBLE PRECISION"

    def __init__(self, url: str):
        if not PSYCOPG_AVAILABLE:  # pragma: no cover - 取决于环境
            raise RuntimeError(
                "检测到 DATABASE_URL，但未安装 psycopg。请执行 pip install -r requirements.txt。"
            )
        self.url = url
        self._dsn, self._connect_kwargs, self.host = normalize_pg_url(url)
        self._pool: queue.LifoQueue[Any] = queue.LifoQueue()
        self._lock = threading.Lock()
        self._created = 0
        self._max_pool = max(1, int(os.environ.get("TRADEGUARD_PG_POOL", "4")))

    # -- 池化 ------------------------------------------------------------
    def _new_connection(self) -> Any:
        return psycopg.connect(
            self._dsn,
            row_factory=dict_row,
            connect_timeout=10,
            **self._connect_kwargs,
        )

    def _acquire(self) -> Any:
        while True:
            try:
                conn = self._pool.get_nowait()
            except queue.Empty:
                break
            if getattr(conn, "closed", True) or getattr(conn, "broken", False):
                with self._lock:
                    self._created -= 1
                continue
            try:
                # 归还的连接可能已被服务端断开，先探活
                conn.execute("SELECT 1")
            except Exception:  # noqa: BLE001 - 探活失败即丢弃
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
                with self._lock:
                    self._created -= 1
                continue
            return conn

        with self._lock:
            if self._created >= self._max_pool:
                # 池已满：阻塞等待有人归还
                return self._pool.get(timeout=30)
            self._created += 1
        try:
            return self._new_connection()
        except Exception:
            with self._lock:
                self._created -= 1
            raise

    def _release(self, conn: Any, *, broken: bool = False) -> None:
        if broken or getattr(conn, "closed", False):
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
            with self._lock:
                self._created -= 1
            return
        try:
            self._pool.put_nowait(conn)
        except queue.Full:  # pragma: no cover - LifoQueue 无界
            conn.close()
            with self._lock:
                self._created -= 1

    @contextmanager
    def connect(self) -> Iterator[PgConnection]:
        raw = self._acquire()
        conn = PgConnection(raw)
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:  # noqa: BLE001 - 连接已断时回滚也会失败
                conn.broken[0] = True
            raise
        finally:
            self._release(raw, broken=conn.broken[0])

    def columns(self, conn: PgConnection, table: str) -> set[str]:
        rows = conn.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = ? AND table_schema = current_schema()
            """,
            (table,),
        ).fetchall()
        names: set[str] = set()
        for row in rows:
            names.add(row["column_name"] if isinstance(row, dict) else row[0])
        return names

    def describe(self) -> str:
        return f"PostgreSQL · {self.host}"

    def close(self) -> None:
        with self._lock:
            while True:
                try:
                    conn = self._pool.get_nowait()
                except queue.Empty:
                    break
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
                self._created -= 1


# --------------------------------------------------------------------------- DSN


def normalize_pg_url(url: str) -> tuple[str, dict[str, Any], str]:
    """归一化 Postgres 连接串，返回 (dsn, connect_kwargs, 主机描述)。

    处理三类常见问题：
    1. 平台（Render/Heroku）下发的是 `postgres://`，psycopg 只认 `postgresql://`；
    2. Supabase 连接串常带 `?pgbouncer=true`、`?connection_limit=1`，
       这些是 PgBouncer 的私有参数，直接透传会让 psycopg 报无效连接选项；
    3. 事务模式池化（6543 端口 / pgbouncer=true）不支持命名预处理语句，
       必须关闭预处理，否则报 `prepared statement already exists`。
    """
    raw = (url or "").strip()
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]

    parts = urlsplit(raw)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    pooler_flags = str(query.pop("pgbouncer", "")).lower() in {"true", "1", "yes"}
    query.pop("connection_limit", None)
    query.pop("pool_timeout", None)

    port = parts.port or 5432
    transaction_pooler = pooler_flags or port == 6543

    dsn = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    kwargs: dict[str, Any] = {}
    if transaction_pooler:
        # 关闭服务端预处理语句（psycopg3 用 None 表示不缓存）
        kwargs["prepare_threshold"] = None

    host = f"{parts.hostname or 'localhost'}:{port}{parts.path or ''}"
    return dsn, kwargs, host


def mask_url(url: str) -> str:
    """把连接串里的密码替换成 ***，并统一 scheme，用于界面展示。"""
    raw = (url or "").strip()
    if not raw:
        return ""
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    parts = urlsplit(raw if "://" in raw else f"postgresql://{raw}")
    netloc = parts.netloc
    if "@" in netloc and ":" in netloc.rsplit("@", 1)[0]:
        credentials, host = netloc.rsplit("@", 1)
        user = credentials.split(":", 1)[0]
        netloc = f"{user}:***@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def make_backend(path: str | Path | None = None, database_url: str | None = None) -> DatabaseBackend:
    """决定用哪个后端：显式路径 > DATABASE_URL > 本地 SQLite。"""
    url = (database_url or os.environ.get("DATABASE_URL") or os.environ.get("TRADEGUARD_DATABASE_URL") or "").strip()
    if url and path is None:
        return PostgresBackend(url)
    from . import config  # 延迟导入，避免循环依赖

    return SqliteBackend(path or config.DB_PATH)
