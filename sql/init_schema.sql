-- 外贸多智能体系统数据库建表脚本
-- Source: app/db/database.py (init_db)
-- Dialect: SQLite

PRAGMA foreign_keys=ON;

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
    sales_trend_flag INTEGER DEFAULT 0,
    total_gmv REAL DEFAULT 0,
    weekly_gmv REAL DEFAULT 0,
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

-- 内容任务
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

-- 支付通道
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

-- 初始化默认支付通道（可重复执行）
INSERT OR IGNORE INTO payment_channels (channel_code, channel_name, channel_group, currency, note) VALUES
('alipay_cn', '支付宝（中国）', 'domestic', 'CNY', '用于国内采购付款'),
('stripe_card', 'Stripe / 国际信用卡', 'international', 'USD', '用于海外客户付款'),
('paypal', 'PayPal', 'international', 'USD', '国际备选支付通道'),
('alipay_global', 'Alipay+ / 国际钱包', 'international', 'USD', '云平台部署后接入');

-- 可选索引（提升查询性能）
CREATE INDEX IF NOT EXISTS idx_products_updated_at ON products(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_tiktok_order_id ON orders(tiktok_order_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at DESC);

-- 东南亚国家分表（保留 1/7/15/30 天核心指标 + image_url）
CREATE TABLE IF NOT EXISTS products_id (
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
);

CREATE TABLE IF NOT EXISTS products_my AS SELECT * FROM products_id WHERE 0;
CREATE TABLE IF NOT EXISTS products_ph AS SELECT * FROM products_id WHERE 0;
CREATE TABLE IF NOT EXISTS products_sg AS SELECT * FROM products_id WHERE 0;
CREATE TABLE IF NOT EXISTS products_th AS SELECT * FROM products_id WHERE 0;
CREATE TABLE IF NOT EXISTS products_vn AS SELECT * FROM products_id WHERE 0;
