"""数据持久化服务 - 所有数据库 CRUD 操作"""

import json
from datetime import datetime
from app.db.database import get_conn


# ==================== 操作日志 ====================
def log_activity(module: str, action: str, detail: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity_log (module, action, detail) VALUES (?, ?, ?)",
            (module, action, detail),
        )


def get_activities(limit: int = 50, module: str = ""):
    with get_conn() as conn:
        if module:
            rows = conn.execute(
                "SELECT * FROM activity_log WHERE module=? ORDER BY created_at DESC LIMIT ?",
                (module, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# ==================== 商品 ====================
def save_products(products: list[dict]):
    with get_conn() as conn:
        for p in products:
            conn.execute(
                """INSERT OR REPLACE INTO products
                (product_id, title, price, currency, sales_count, daily_sales, weekly_sales,
                 likes, comments, shop_name, category, product_url, image_url,
                 country, growth_rate, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    p.get("product_id", ""),
                    p.get("title", ""),
                    p.get("price", 0),
                    p.get("currency", "USD"),
                    p.get("sales_count", 0),
                    p.get("daily_sales", 0),
                    p.get("weekly_sales", 0),
                    p.get("likes", 0),
                    p.get("comments", 0),
                    p.get("shop_name", ""),
                    p.get("category", ""),
                    p.get("product_url", ""),
                    p.get("image_url", ""),
                    p.get("country", "US"),
                    p.get("growth_rate", 0),
                    datetime.now().isoformat(),
                ),
            )
    return len(products)


def get_products(keyword: str = "", category: str = "", limit: int = 50):
    with get_conn() as conn:
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        if keyword:
            query += " AND title LIKE ?"
            params.append(f"%{keyword}%")
        if category:
            query += " AND category LIKE ?"
            params.append(f"%{category}%")
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


SEA_REGION_CODES = ("ID", "MY", "PH", "SG", "TH", "VN")
SEA_METRIC_FIELDS = (
    "total_sale_1d_cnt",
    "total_sale_7d_cnt",
    "total_sale_15d_cnt",
    "total_sale_30d_cnt",
    "total_sale_gmv_1d_amt",
    "total_sale_gmv_7d_amt",
    "total_sale_gmv_15d_amt",
    "total_sale_gmv_30d_amt",
    "total_live_sale_1d_cnt",
    "total_live_sale_7d_cnt",
    "total_live_sale_15d_cnt",
    "total_live_sale_30d_cnt",
    "total_live_sale_gmv_1d_amt",
    "total_live_sale_gmv_7d_amt",
    "total_live_sale_gmv_15d_amt",
    "total_live_sale_gmv_30d_amt",
    "total_video_sale_1d_cnt",
    "total_video_sale_7d_cnt",
    "total_video_sale_15d_cnt",
    "total_video_sale_30d_cnt",
    "total_video_sale_gmv_1d_amt",
    "total_video_sale_gmv_7d_amt",
    "total_video_sale_gmv_15d_amt",
    "total_video_sale_gmv_30d_amt",
    "total_views_1d_cnt",
    "total_views_7d_cnt",
    "total_views_15d_cnt",
    "total_views_30d_cnt",
    "total_live_1d_cnt",
    "total_live_7d_cnt",
    "total_live_15d_cnt",
    "total_live_30d_cnt",
    "total_video_1d_cnt",
    "total_video_7d_cnt",
    "total_video_15d_cnt",
    "total_video_30d_cnt",
)


def _table_name_for_region(region: str) -> str:
    normalized = (region or "").strip().lower()
    if normalized not in {c.lower() for c in SEA_REGION_CODES}:
        raise ValueError(f"unsupported region: {region}")
    return f"products_{normalized}"


def save_products_by_region(region: str, products: list[dict]) -> int:
    table_name = _table_name_for_region(region)
    if not products:
        return 0

    with get_conn() as conn:
        for p in products:
            values = {field: p.get(field, 0) for field in SEA_METRIC_FIELDS}
            conn.execute(
                f"""INSERT INTO {table_name}
                (product_id, product_name, image_url, region, {", ".join(SEA_METRIC_FIELDS)}, updated_at)
                VALUES (?, ?, ?, ?, {", ".join(["?"] * len(SEA_METRIC_FIELDS))}, ?)
                ON CONFLICT(product_id) DO UPDATE SET
                    product_name=excluded.product_name,
                    image_url=excluded.image_url,
                    region=excluded.region,
                    {", ".join([f"{f}=excluded.{f}" for f in SEA_METRIC_FIELDS])},
                    updated_at=excluded.updated_at
                """,
                (
                    p.get("product_id", ""),
                    p.get("product_name", p.get("title", "")),
                    p.get("image_url", ""),
                    p.get("region", region),
                    *[values[f] for f in SEA_METRIC_FIELDS],
                    datetime.now().isoformat(),
                ),
            )
    return len(products)


# ==================== 选品分析 ====================
def save_analysis(keyword: str, category: str, analysis: dict, product_count: int):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO product_analyses (keyword, category, analysis_json, product_count, recommendation_score)
               VALUES (?, ?, ?, ?, ?)""",
            (
                keyword,
                category,
                json.dumps(analysis, ensure_ascii=False),
                product_count,
                analysis.get("recommendation_score", 0),
            ),
        )
    log_activity("monitor", "AI选品分析", f"关键词: {keyword}, 分析{product_count}个商品")


def get_analyses(limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM product_analyses ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["analysis"] = json.loads(d.pop("analysis_json", "{}"))
            results.append(d)
        return results


# ==================== 供应商匹配 ====================
def save_supplier_match(keyword: str, product_title: str, suppliers: list, analysis: dict):
    best = suppliers[0] if suppliers else {}
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO supplier_matches
               (keyword, product_title, suppliers_json, analysis_json, supplier_count, best_supplier, best_price)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                keyword,
                product_title,
                json.dumps(suppliers, ensure_ascii=False),
                json.dumps(analysis, ensure_ascii=False),
                len(suppliers),
                best.get("name", ""),
                best.get("price_cny", 0),
            ),
        )
    log_activity("supply", "供应商匹配", f"关键词: {keyword}, 匹配{len(suppliers)}个供应商")


def get_supplier_matches(limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM supplier_matches ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["suppliers"] = json.loads(d.pop("suppliers_json", "[]"))
            d["analysis"] = json.loads(d.pop("analysis_json", "{}"))
            results.append(d)
        return results


# ==================== 内容生成 ====================
def save_content(product_title: str, product_price: float, content_type: str, page: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO content_records (product_title, product_price, content_type, page_json)
               VALUES (?, ?, ?, ?)""",
            (
                product_title,
                product_price,
                content_type,
                json.dumps(page, ensure_ascii=False) if page else None,
            ),
        )
    log_activity("content", "AI内容生成", f"商品: {product_title}, 类型: {content_type}")


def get_content_records(limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM content_records ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["page"] = json.loads(d.pop("page_json") or "{}")
            results.append(d)
        return results


# ==================== 收藏 ====================
def add_favorite(product_id: str, title: str, price: float, category: str, note: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO favorites (product_id, title, price, category, note) VALUES (?, ?, ?, ?, ?)",
            (product_id, title, price, category, note),
        )
    log_activity("favorite", "收藏商品", f"{title}")


def remove_favorite(fav_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM favorites WHERE id=?", (fav_id,))


def get_favorites(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM favorites ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ==================== 统计 ====================
def get_stats():
    with get_conn() as conn:
        products = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
        analyses = conn.execute("SELECT COUNT(*) as c FROM product_analyses").fetchone()["c"]
        matches = conn.execute("SELECT COUNT(*) as c FROM supplier_matches").fetchone()["c"]
        contents = conn.execute("SELECT COUNT(*) as c FROM content_records").fetchone()["c"]
        favorites = conn.execute("SELECT COUNT(*) as c FROM favorites").fetchone()["c"]
        return {
            "products": products,
            "analyses": analyses,
            "supplier_matches": matches,
            "content_records": contents,
            "favorites": favorites,
        }