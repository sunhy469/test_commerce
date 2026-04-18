"""系统总览 API"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.db import store
from app.db.database import get_conn
from config.settings import get_settings

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["总览"])


@dashboard_router.get("/stats")
async def get_stats():
    """获取系统概览统计（从数据库读取真实数据）"""
    db_stats = store.get_stats()
    activities = store.get_activities(limit=10)

    # 从数据库动态计算热门类目
    trending_categories = []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM products WHERE category != '' GROUP BY category ORDER BY cnt DESC LIMIT 5"
        ).fetchall()
        for r in rows:
            trending_categories.append({
                "name": r["category"],
                "count": r["cnt"],
                "growth": round(r["cnt"] / max(db_stats["products"], 1) * 100, 1),
            })

    # 从订单数据计算利润概览
    profit_summary = {"avg_profit_margin": 0, "best_category": "N/A", "avg_product_cost_cny": 0, "avg_selling_price_usd": 0}
    with get_conn() as conn:
        row = conn.execute(
            "SELECT AVG(unit_price_usd) as avg_price, AVG(purchase_price_cny) as avg_cost FROM orders WHERE purchase_price_cny IS NOT NULL"
        ).fetchone()
        if row and row["avg_price"]:
            avg_revenue = row["avg_price"] * 7.2
            avg_cost = row["avg_cost"] + 15 + row["avg_cost"] * 0.05
            margin = (avg_revenue - avg_cost) / avg_revenue * 100 if avg_revenue > 0 else 0
            profit_summary = {
                "avg_profit_margin": round(margin, 1),
                "best_category": trending_categories[0]["name"] if trending_categories else "N/A",
                "avg_product_cost_cny": round(row["avg_cost"], 2),
                "avg_selling_price_usd": round(row["avg_price"], 2),
            }

    # 检测系统连接状态
    settings = get_settings()
    claude_status = "disabled"
    echotik_status = "connected" if (settings.echotik_api_key or (settings.echotik_username and settings.echotik_password)) else "not_configured"
    seed_status = "connected" if settings.volcano_api_key else "not_configured"

    return {
        "overview": {
            "monitored_products": db_stats["products"],
            "analyses_count": db_stats["analyses"],
            "matched_suppliers": db_stats["supplier_matches"],
            "generated_pages": db_stats["content_records"],
            "favorites": db_stats["favorites"],
        },
        "trending_categories": trending_categories,
        "profit_summary": profit_summary,
        "system_status": {
            "tiktok_api": "mock",
            "alibaba_api": "pending_auth",
            "claude_api": claude_status,
            "echotik_api": echotik_status,
            "seed_api": seed_status,
        },
        "recent_activities": activities,
    }


@dashboard_router.get("/profit-calc")
async def calc_profit(
    tiktok_price_usd: float = 12.99,
    cost_1688_cny: float = 15.0,
    shipping_cny: float = 15.0,
    exchange_rate: float = 7.2,
    misc_rate: float = 0.05,
):
    """利润计算器"""
    revenue_cny = tiktok_price_usd * exchange_rate
    total_cost = cost_1688_cny + shipping_cny
    misc_fee = total_cost * misc_rate
    total_cost_with_misc = total_cost + misc_fee
    profit_cny = revenue_cny - total_cost_with_misc
    profit_margin = (profit_cny / revenue_cny * 100) if revenue_cny > 0 else 0

    return {
        "revenue_cny": round(revenue_cny, 2),
        "cost_1688_cny": cost_1688_cny,
        "shipping_cny": shipping_cny,
        "misc_fee_cny": round(misc_fee, 2),
        "total_cost_cny": round(total_cost_with_misc, 2),
        "profit_cny": round(profit_cny, 2),
        "profit_margin_pct": round(profit_margin, 1),
        "is_profitable": profit_cny >= 20,
        "verdict": "推荐" if profit_cny >= 20 else ("观望" if profit_cny >= 10 else "不推荐"),
    }


@dashboard_router.get("/export")
async def export_data(module: str = "monitor", format: str = "json"):
    """导出数据（预留接口）"""
    return {
        "status": "ready",
        "module": module,
        "format": format,
        "message": f"数据导出功能就绪，将导出 {module} 模块数据为 {format} 格式",
    }
