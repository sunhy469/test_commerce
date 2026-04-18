"""SQLite 数据库初始化和连接管理"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "trade_agents.db")
SEA_REGION_CODES = ("ID", "MY", "PH", "SG", "TH", "VN")
SEA_TABLE_COLUMNS_SQL = """
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT UNIQUE,
    product_name TEXT,
    image_url TEXT,
    region TEXT,
    total_sale_1d_cnt INTEGER DEFAULT 0,
    total_sale_7d_cnt INTEGER DEFAULT 0,
    total_sale_15d_cnt INTEGER DEFAULT 0,
    total_sale_30d_cnt INTEGER DEFAULT 0,
    total_sale_gmv_1d_amt REAL DEFAULT 0,
    total_sale_gmv_7d_amt REAL DEFAULT 0,
    total_sale_gmv_15d_amt REAL DEFAULT 0,
    total_sale_gmv_30d_amt REAL DEFAULT 0,
    total_live_sale_1d_cnt INTEGER DEFAULT 0,
    total_live_sale_7d_cnt INTEGER DEFAULT 0,
    total_live_sale_15d_cnt INTEGER DEFAULT 0,
    total_live_sale_30d_cnt INTEGER DEFAULT 0,
    total_live_sale_gmv_1d_amt REAL DEFAULT 0,
    total_live_sale_gmv_7d_amt REAL DEFAULT 0,
    total_live_sale_gmv_15d_amt REAL DEFAULT 0,
    total_live_sale_gmv_30d_amt REAL DEFAULT 0,
    total_video_sale_1d_cnt INTEGER DEFAULT 0,
    total_video_sale_7d_cnt INTEGER DEFAULT 0,
    total_video_sale_15d_cnt INTEGER DEFAULT 0,
    total_video_sale_30d_cnt INTEGER DEFAULT 0,
    total_video_sale_gmv_1d_amt REAL DEFAULT 0,
    total_video_sale_gmv_7d_amt REAL DEFAULT 0,
    total_video_sale_gmv_15d_amt REAL DEFAULT 0,
    total_video_sale_gmv_30d_amt REAL DEFAULT 0,
    total_views_1d_cnt INTEGER DEFAULT 0,
    total_views_7d_cnt INTEGER DEFAULT 0,
    total_views_15d_cnt INTEGER DEFAULT 0,
    total_views_30d_cnt INTEGER DEFAULT 0,
    total_live_1d_cnt INTEGER DEFAULT 0,
    total_live_7d_cnt INTEGER DEFAULT 0,
    total_live_15d_cnt INTEGER DEFAULT 0,
    total_live_30d_cnt INTEGER DEFAULT 0,
    total_video_1d_cnt INTEGER DEFAULT 0,
    total_video_7d_cnt INTEGER DEFAULT 0,
    total_video_15d_cnt INTEGER DEFAULT 0,
    total_video_30d_cnt INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
"""
SEA_TABLE_REQUIRED_COLUMNS = {
    "product_id",
    "product_name",
    "image_url",
    "region",
    "total_sale_1d_cnt",
    "total_sale_7d_cnt",
    "total_sale_15d_cnt",
    "total_sale_30d_cnt",
    "updated_at",
}


def _drop_column_if_exists(conn: sqlite3.Connection, table_name: str, column_name: str):
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    if column_name not in columns:
        return
    remaining_columns = [c for c in columns if c != column_name]
    cols_sql = ", ".join(remaining_columns)
    conn.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_legacy")
    if table_name == "products":
        conn.execute(
            """CREATE TABLE products (
                                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                                         product_id TEXT UNIQUE,
                                         title TEXT NOT NULL,
                                         price REAL,
                                         currency TEXT DEFAULT 'USD',
                                         sales_count INTEGER DEFAULT 0,
                                         daily_sales INTEGER DEFAULT 0,
                                         weekly_sales INTEGER DEFAULT 0,
                                         likes INTEGER DEFAULT 0,
                                         comments INTEGER DEFAULT 0,
                                         shop_name TEXT,
                                         category TEXT,
                                         product_url TEXT,
                                         image_url TEXT,
                                         country TEXT DEFAULT 'US',
                                         growth_rate REAL DEFAULT 0,
                                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )"""
        )
    elif table_name == "content_records":
        conn.execute(
            """CREATE TABLE content_records (
                                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                product_title TEXT,
                                                product_price REAL,
                                                content_type TEXT,
                                                page_json TEXT,
                                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )"""
        )
    else:
        conn.execute(f"ALTER TABLE {table_name}_legacy RENAME TO {table_name}")
        return
    conn.execute(f"INSERT INTO {table_name} ({cols_sql}) SELECT {cols_sql} FROM {table_name}_legacy")
    conn.execute(f"DROP TABLE {table_name}_legacy")


def get_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


def _rebuild_region_table(conn: sqlite3.Connection, table_name: str):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    backup_name = f"{table_name}_legacy"
    if exists:
        conn.execute(f"DROP TABLE IF EXISTS {backup_name}")
        conn.execute(f"ALTER TABLE {table_name} RENAME TO {backup_name}")
    conn.execute(f"CREATE TABLE {table_name} ({SEA_TABLE_COLUMNS_SQL})")
    if exists:
        old_columns = [row[1] for row in conn.execute(f"PRAGMA table_info({backup_name})").fetchall()]
        new_columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
        shared_columns = [c for c in new_columns if c in old_columns and c != "id"]
        if shared_columns:
            cols_sql = ", ".join(shared_columns)
            conn.execute(
                f"INSERT OR REPLACE INTO {table_name} ({cols_sql}) SELECT {cols_sql} FROM {backup_name}"
            )
        conn.execute(f"DROP TABLE IF EXISTS {backup_name}")


def _ensure_region_table(conn: sqlite3.Connection, table_name: str):
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    if not exists:
        conn.execute(f"CREATE TABLE {table_name} ({SEA_TABLE_COLUMNS_SQL})")
        return

    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    unique_index_ok = conn.execute(
        f"SELECT 1 FROM pragma_index_list('{table_name}') WHERE [unique]=1"
    ).fetchone()
    if not SEA_TABLE_REQUIRED_COLUMNS.issubset(set(columns)) or not unique_index_ok:
        _rebuild_region_table(conn, table_name)


@contextmanager
def get_conn():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """创建所有表"""
    with get_conn() as conn:
        conn.executescript("""
                           -- 监控的商品（TikTok热销）
                           CREATE TABLE IF NOT EXISTS products (
                                                                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                   product_id TEXT UNIQUE,
                                                                   title TEXT NOT NULL,
                                                                   price REAL,
                                                                   currency TEXT DEFAULT 'USD',
                                                                   sales_count INTEGER DEFAULT 0,
                                                                   daily_sales INTEGER DEFAULT 0,
                                                                   weekly_sales INTEGER DEFAULT 0,
                                                                   likes INTEGER DEFAULT 0,
                                                                   comments INTEGER DEFAULT 0,
                                                                   shop_name TEXT,
                                                                   category TEXT,
                                                                   product_url TEXT,
                                                                   image_url TEXT,
                                                                   country TEXT DEFAULT 'US',
                                                                   growth_rate REAL DEFAULT 0,
                                                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- AI 选品分析记录
                           CREATE TABLE IF NOT EXISTS product_analyses (
                                                                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                           keyword TEXT,
                                                                           category TEXT,
                                                                           analysis_json TEXT,
                                                                           product_count INTEGER DEFAULT 0,
                                                                           recommendation_score REAL,
                                                                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- 供应商匹配记录
                           CREATE TABLE IF NOT EXISTS supplier_matches (
                                                                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                           keyword TEXT,
                                                                           product_title TEXT,
                                                                           suppliers_json TEXT,
                                                                           analysis_json TEXT,
                                                                           supplier_count INTEGER DEFAULT 0,
                                                                           best_supplier TEXT,
                                                                           best_price REAL,
                                                                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- 内容生成记录
                           CREATE TABLE IF NOT EXISTS content_records (
                                                                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                          product_title TEXT,
                                                                          product_price REAL,
                                                                          content_type TEXT,
                                                                          page_json TEXT,
                                                                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- 操作日志
                           CREATE TABLE IF NOT EXISTS activity_log (
                                                                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                       module TEXT NOT NULL,
                                                                       action TEXT NOT NULL,
                                                                       detail TEXT,
                                                                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- 收藏的商品（用户标记）
                           CREATE TABLE IF NOT EXISTS favorites (
                                                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                    product_id TEXT,
                                                                    title TEXT,
                                                                    price REAL,
                                                                    category TEXT,
                                                                    note TEXT,
                                                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- TikTok 订单
                           CREATE TABLE IF NOT EXISTS orders (
                                                                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                 tiktok_order_id TEXT UNIQUE,
                                                                 product_title TEXT,
                                                                 product_id TEXT,
                                                                 quantity INTEGER DEFAULT 1,
                                                                 unit_price_usd REAL,
                                                                 total_usd REAL,
                                                                 customer_name TEXT,
                                                                 customer_email TEXT,
                                                                 customer_phone TEXT,
                                                                 shipping_address TEXT,
                                                                 status TEXT DEFAULT 'draft',
                                                                 workflow_stage TEXT DEFAULT 'draft',
                                                                 store_binding_id INTEGER,
                                                                 supplier_id TEXT,
                                                                 matched_supplier TEXT,
                                                                 matched_1688_id TEXT,
                                                                 purchase_price_cny REAL,
                                                                 purchase_status TEXT DEFAULT 'awaiting_supplier',
                                                                 payment_channel TEXT DEFAULT '',
                                                                 payment_status TEXT DEFAULT 'unpaid',
                                                                 notes TEXT,
                                                                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- SKU 映射（TikTok SKU <-> 1688 SKU）
                           CREATE TABLE IF NOT EXISTS sku_mappings (
                                                                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                       tiktok_product_id TEXT,
                                                                       tiktok_sku TEXT,
                                                                       alibaba_product_id TEXT,
                                                                       alibaba_sku TEXT,
                                                                       supplier_name TEXT,
                                                                       price_cny REAL,
                                                                       moq INTEGER DEFAULT 1,
                                                                       is_active INTEGER DEFAULT 1,
                                                                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                                                       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- 库存同步记录
                           CREATE TABLE IF NOT EXISTS inventory_sync (
                                                                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                         tiktok_product_id TEXT,
                                                                         alibaba_product_id TEXT,
                                                                         stock_1688 INTEGER,
                                                                         price_1688_cny REAL,
                                                                         previous_stock INTEGER,
                                                                         previous_price REAL,
                                                                         action_taken TEXT,
                                                                         synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- 支付记录
                           CREATE TABLE IF NOT EXISTS payments (
                                                                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                   order_id TEXT,
                                                                   payment_method TEXT,
                                                                   amount REAL,
                                                                   currency TEXT DEFAULT 'CNY',
                                                                   status TEXT DEFAULT 'pending',
                                                                   transaction_id TEXT,
                                                                   checkout_url TEXT,
                                                                   provider TEXT,
                                                                   provider_model TEXT,
                                                                   paid_at TIMESTAMP,
                                                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- 店铺绑定
                           CREATE TABLE IF NOT EXISTS store_bindings (
                                                                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                         platform TEXT DEFAULT 'tiktok',
                                                                         store_name TEXT,
                                                                         store_id TEXT,
                                                                         store_url TEXT,
                                                                         access_token TEXT,
                                                                         country TEXT DEFAULT 'US',
                                                                         is_active INTEGER DEFAULT 1,
                                                                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

                           -- 对话历史
                           CREATE TABLE IF NOT EXISTS chat_history (
                                                                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                       session_id TEXT,
                                                                       role TEXT,
                                                                       content TEXT,
                                                                       action_type TEXT,
                                                                       action_result TEXT,
                                                                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           );

        CREATE TABLE IF NOT EXISTS content_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            job_type TEXT,
            provider TEXT,
            model_name TEXT,
            product_title TEXT,
            prompt TEXT,
            aspect_ratio TEXT,
            status TEXT DEFAULT 'draft',
            preview_url TEXT,
            result_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS payment_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_code TEXT UNIQUE,
            channel_name TEXT,
            channel_group TEXT,
            currency TEXT,
            status TEXT DEFAULT 'enabled',
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        expected_tables = {f"products_{region.lower()}" for region in SEA_REGION_CODES}
        for table_name in expected_tables:
            _ensure_region_table(conn, table_name)
        existing_product_tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'products_%'"
        ).fetchall()
        for row in existing_product_tables:
            table_name = row[0]
            if table_name not in expected_tables and table_name != "products":
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")

        _drop_column_if_exists(conn, "products", "video_views")
        _drop_column_if_exists(conn, "content_records", "video_json")

        columns = [row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()]
        if "customer_email" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN customer_email TEXT")
        if "customer_phone" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN customer_phone TEXT")
        if "workflow_stage" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN workflow_stage TEXT DEFAULT 'draft'")
        if "store_binding_id" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN store_binding_id INTEGER")
        if "supplier_id" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN supplier_id TEXT")
        if "payment_channel" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_channel TEXT DEFAULT ''")
        if "payment_status" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'unpaid'")
        if "notes" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN notes TEXT")

        payment_columns = [row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()]
        if "checkout_url" not in payment_columns:
            conn.execute("ALTER TABLE payments ADD COLUMN checkout_url TEXT")
        if "provider" not in payment_columns:
            conn.execute("ALTER TABLE payments ADD COLUMN provider TEXT")
        if "provider_model" not in payment_columns:
            conn.execute("ALTER TABLE payments ADD COLUMN provider_model TEXT")

        existing_channels = conn.execute("SELECT COUNT(*) FROM payment_channels").fetchone()[0]
        if existing_channels == 0:
            conn.executemany(
                "INSERT INTO payment_channels (channel_code, channel_name, channel_group, currency, note) VALUES (?, ?, ?, ?, ?)",
                [
                    ("alipay_cn", "支付宝（中国）", "domestic", "CNY", "用于国内采购付款"),
                    ("stripe_card", "Stripe / 国际信用卡", "international", "USD", "用于海外客户付款"),
                    ("paypal", "PayPal", "international", "USD", "国际备选支付通道"),
                    ("alipay_global", "Alipay+ / 国际钱包", "international", "USD", "云平台部署后接入"),
                ],
            )


# 启动时自动初始化
init_db()