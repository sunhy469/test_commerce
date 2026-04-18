"""API 路由 - 所有智能体接口（含数据持久化）"""

from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from app.agents.product_monitor import ProductMonitorAgent
from app.agents.supply_chain import SupplyChainAgent
from app.agents.content_gen import ContentGenAgent
from app.agents.auto_purchase import AutoPurchaseAgent
from app.services.payment import PaymentService
from app.models.schemas import (
    SearchRequest, AnalyzeRequest, RankingRequest,
    ContentDetailRequest, ContentImageRequest,
    StoreBinding, CommerceOrderRequest, OrderStageUpdateRequest, CommercePaymentRequest,
)
from app.db import store
from app.db.database import get_conn
import base64
import json

# === 路由 ===
monitor_router = APIRouter(prefix="/api/monitor", tags=["选品监控"])
supply_router = APIRouter(prefix="/api/supply", tags=["供应链匹配"])
content_router = APIRouter(prefix="/api/content", tags=["内容生成"])
purchase_router = APIRouter(prefix="/api/purchase", tags=["自动采购"])
payment_router = APIRouter(prefix="/api/payment", tags=["支付"])
history_router = APIRouter(prefix="/api/history", tags=["历史记录"])
user_router = APIRouter(prefix="/api/user", tags=["用户中心"])

# === 智能体实例 ===
monitor_agent = ProductMonitorAgent()
supply_agent = SupplyChainAgent()
content_agent = ContentGenAgent()
purchase_agent = AutoPurchaseAgent()
payment_service = PaymentService()


# ==================== 选品监控 + 排行榜 ====================
@monitor_router.get("/trending")
async def get_trending(country: str = "", category: str = ""):
    products = await monitor_agent.search(keyword="", limit=20, country=country, category=category)
    product_dicts = [p.model_dump() for p in products]
    # 按国家过滤
    if country:
        product_dicts = [p for p in product_dicts if p.get("country", "US") == country] or product_dicts
    if category:
        product_dicts = [p for p in product_dicts if category.lower() in p.get("category", "").lower()] or product_dicts
    store.save_products(product_dicts)
    store.log_activity("monitor", "查看热销趋势", f"获取{len(product_dicts)}个商品, 国家: {country or '全部'}")
    return {"products": product_dicts, "total": len(product_dicts)}


@monitor_router.post("/search")
async def search_products(req: SearchRequest):
    products = await monitor_agent.search(keyword=req.keyword, limit=req.limit, country=req.country, category=req.category)
    product_dicts = [p.model_dump() for p in products]
    if req.country:
        product_dicts = [p for p in product_dicts if p.get("country", "US") == req.country] or product_dicts
    store.save_products(product_dicts)
    store.log_activity("monitor", "搜索商品", f"关键词: {req.keyword}, 国家: {req.country or '全部'}")
    return {"products": product_dicts, "total": len(product_dicts)}


@monitor_router.post("/ranking")
async def get_ranking(req: RankingRequest):
    """获取排行榜数据：仅从数据库读取（定时任务入库后查询）"""
    sea_countries = {"ID", "TH", "VN", "MY", "PH", "SG"}
    country = req.country.strip().upper() if req.country else ""

    with get_conn() as conn:
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if country:
            if country not in sea_countries:
                return {"products": [], "total": 0, "rank_type": req.rank_type, "time_range": req.time_range, "country": country}
            query += " AND country=?"
            params.append(country)
        else:
            query += " AND country IN ({})".format(",".join(["?"] * len(sea_countries)))
            params.extend(sorted(sea_countries))

        if req.category:
            query += " AND category LIKE ?"
            params.append(f"%{req.category}%")

        if req.rank_type == "growth":
            query += " ORDER BY growth_rate DESC"
        elif req.time_range == "daily":
            query += " ORDER BY daily_sales DESC"
        elif req.time_range == "weekly":
            query += " ORDER BY weekly_sales DESC"
        else:
            query += " ORDER BY sales_count DESC"

        query += " LIMIT ?"
        params.append(req.limit)
        rows = conn.execute(query, params).fetchall()
        products = [dict(r) for r in rows]

    return {"products": products, "total": len(products), "rank_type": req.rank_type, "time_range": req.time_range, "country": country}


@monitor_router.post("/analyze")
async def analyze_products(req: AnalyzeRequest):
    result = await monitor_agent.run(keyword=req.keyword, category=req.category, limit=req.limit)
    if result.get("products"):
        store.save_products(result["products"])
    if result.get("analysis"):
        store.save_analysis(req.keyword, req.category, result["analysis"], result.get("total", 0))
    return result


# ==================== 供应链匹配 ====================
class SupplyRequest(BaseModel):
    keyword: str = ""
    product: dict = None


@supply_router.post("/match")
async def match_suppliers(req: SupplyRequest):
    result = await supply_agent.run(product=req.product, keyword=req.keyword)
    store.save_supplier_match(
        keyword=req.keyword,
        product_title=(req.product or {}).get("title", req.keyword),
        suppliers=result.get("suppliers", []),
        analysis=result.get("analysis", {}),
    )
    return result


@supply_router.post("/image-search")
async def image_search_suppliers(image_url: str = Form(""), image_file: UploadFile = File(None)):
    """以图搜货 - 支持URL或上传图片"""
    from app.scrapers.alibaba_scraper import AlibabaScraper
    scraper = AlibabaScraper()

    if image_file:
        content = await image_file.read()
        img_base64 = base64.b64encode(content).decode()
        # 对于上传的图片，先保存再搜索
        import os
        save_path = f"data/images/search_{image_file.filename}"
        os.makedirs("data/images", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(content)
        image_url = save_path

    results = await scraper.search_by_image(image_url or "", limit=10)
    store.log_activity("supply", "图搜找货", f"图片: {image_url[:50] if image_url else '上传文件'}")
    return {"results": results, "total": len(results), "source": "image_search"}


# ==================== 内容生成（拆分为3个子模块） ====================
@content_router.post("/generate")
async def generate_content_all(req: ContentDetailRequest):
    """兼容旧接口 - 生成全部内容"""
    result = await content_agent.run(product=req.product, content_type="all")
    store.save_content(
        product_title=req.product.get("title", ""),
        product_price=req.product.get("price", 0),
        content_type="all",
        page=result.get("page"),
    )
    return result


COUNTRY_LANG_MAP = {
    "US": ("en", "American English, casual North American style"),
    "GB": ("en", "British English"),
    "ID": ("id", "Bahasa Indonesia"),
    "TH": ("th", "ภาษาไทย (Thai)"),
    "VN": ("vi", "Tiếng Việt (Vietnamese)"),
    "MY": ("ms", "Bahasa Melayu (Malay)"),
    "PH": ("en", "Philippine English, casual Filipino style"),
    "JP": ("ja", "日本語 (Japanese)"),
    "KR": ("ko", "한국어 (Korean)"),
    "BR": ("pt", "Português brasileiro"),
    "MX": ("es", "Español mexicano"),
    "SA": ("ar", "العربية (Arabic)"),
    "global": ("en", "International English"),
}


@content_router.post("/detail-page")
async def generate_detail_page(req: ContentDetailRequest):
    """生成商品详情页（支持多语言）"""
    lang_code, lang_desc = COUNTRY_LANG_MAP.get(req.country, ("en", "English"))
    product = req.product
    product["_target_language"] = lang_desc
    product["_target_country"] = req.country
    result = await content_agent.run(product=product, content_type="page")
    store.save_content(
        product_title=product.get("title", ""),
        product_price=product.get("price", 0),
        content_type="detail_page",
        page=result.get("page"),
    )
    store.log_activity("content", "生成详情页", f"商品: {product.get('title','')}, 国家: {req.country}")
    return result


@content_router.post("/image")
async def generate_image(req: ContentImageRequest):
    """生成商品电商详情图任务（字节 Seed 2.0）"""
    product = req.product
    product["_image_prompt"] = req.prompt
    product["_image_style"] = req.style
    result = await content_agent.run(product=product, content_type="image")
    image_job = result.get("image_job", {})
    provider = image_job.get("provider", "byte-seed")
    model_name = image_job.get("model", "Seed-2.0")
    job_id = f"IMG-{product.get('title', 'product')[:8]}-{provider}".replace(" ", "")

    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO content_jobs
            (job_id, job_type, provider, model_name, product_title, prompt, aspect_ratio, status, preview_url, result_payload, updated_at)
            VALUES (?, 'image', ?, ?, ?, ?, ?, 'ready_for_submit', ?, ?, CURRENT_TIMESTAMP)""",
            (
                job_id,
                provider,
                model_name,
                product.get("title", ""),
                image_job.get("prompt", req.prompt),
                product.get("_aspect_ratio", "4:5"),
                "",
                json.dumps(image_job, ensure_ascii=False),
            ),
        )

    store.log_activity("content", "生成商品图片任务", f"商品: {product.get('title','')}, 引擎: {provider}/{model_name}")
    return {
        "type": "image",
        "provider": provider,
        "model": model_name,
        "job_id": job_id,
        "prompt": image_job.get("prompt", req.prompt),
        "enabled": image_job.get("enabled", False),
        "message": "已生成可提交到字节 Seed 2.0 的图片任务草稿",
    }


# ==================== 自动采购 ====================
@purchase_router.post("/orders")
async def create_order(req: CommerceOrderRequest):
    result = await purchase_agent.create_order(req.model_dump())
    store.log_activity("purchase", "创建订单草稿", f"订单: {req.order_id or 'auto'}, 商品: {req.product_title}")
    return result


@purchase_router.get("/orders")
async def list_orders(status: str = "", limit: int = 50):
    orders = await purchase_agent.get_orders(status=status, limit=limit)
    return {"orders": orders, "total": len(orders)}


@purchase_router.get("/orders/{order_id}")
async def get_order_detail(order_id: str):
    return await purchase_agent.get_order_detail(order_id)


@purchase_router.post("/orders/{order_id}/stage")
async def update_order_stage(order_id: str, req: OrderStageUpdateRequest):
    result = await purchase_agent.update_order_stage(
        order_id,
        status=req.status,
        supplier_id=req.supplier_id,
        supplier_name=req.supplier_name,
        payment_channel=req.payment_channel,
        notes=req.notes,
    )
    store.log_activity("purchase", "推进订单阶段", f"订单: {order_id}, 阶段: {req.status}")
    return result


@purchase_router.get("/payment-channels")
async def list_payment_channels():
    channels = await payment_service.get_payment_channels()
    return {"channels": channels, "total": len(channels)}


@purchase_router.post("/orders/{order_id}/payments")
async def create_order_payment(order_id: str, req: CommercePaymentRequest):
    result = await payment_service.create_payment(
        order_id=order_id,
        channel=req.payment_channel,
        amount=req.amount,
        currency=req.currency,
        subject=req.subject,
        return_url=req.return_url,
    )
    await purchase_agent.update_order_stage(order_id, status="payment_pending", payment_channel=req.payment_channel, notes="已创建支付单，等待用户完成付款。")
    store.log_activity("payment", "创建订单支付", f"订单: {order_id}, 通道: {req.payment_channel}, 金额: {req.amount}{req.currency}")
    return result


@purchase_router.post("/orders/{order_id}/mark-paid")
async def mark_order_paid(order_id: str):
    await payment_service.mark_payment_status(order_id, status="paid")
    result = await purchase_agent.update_order_stage(order_id, status="paid", notes="支付已确认，可进入履约。")
    store.log_activity("payment", "标记支付成功", f"订单: {order_id}")
    return result


class SkuMappingRequest(BaseModel):
    tiktok_product_id: str
    tiktok_sku: str = ""
    alibaba_product_id: str
    alibaba_sku: str = ""
    supplier_name: str = ""
    price_cny: float = 0
    moq: int = 1


@purchase_router.post("/sku-mappings")
async def create_sku_mapping(req: SkuMappingRequest):
    result = await purchase_agent.create_sku_mapping(req.model_dump())
    store.log_activity("purchase", "创建SKU映射", f"TikTok:{req.tiktok_product_id} -> 1688:{req.alibaba_product_id}")
    return result


@purchase_router.get("/sku-mappings")
async def list_sku_mappings():
    mappings = await purchase_agent.get_sku_mappings()
    return {"mappings": mappings, "total": len(mappings)}


@purchase_router.post("/sync-inventory")
async def sync_inventory():
    result = await purchase_agent.sync_inventory()
    store.log_activity("purchase", "库存同步", f"同步{result['synced_count']}个商品")
    return result


@purchase_router.get("/sync-history")
async def sync_history(limit: int = 20):
    records = await purchase_agent.get_sync_history(limit=limit)
    return {"records": records, "total": len(records)}


class PurchaseRequest(BaseModel):
    order: dict = {}


@purchase_router.post("/plan")
async def create_purchase_plan(req: PurchaseRequest):
    result = await purchase_agent.run(order=req.order)
    store.log_activity("purchase", "生成采购方案", "")
    return result


@purchase_router.get("/status")
async def purchase_status():
    return {
        "status": "partial_ready",
        "message": "订单管理和SKU映射已就绪，1688自动下单需企业认证",
        "features": {
            "order_management": "ready",
            "sku_mapping": "ready",
            "inventory_sync": "ready_mock",
            "auto_purchase_1688": "pending_auth",
            "payment_alipay": "pending_setup",
            "payment_stripe": "pending_setup",
        },
    }


# ==================== 历史记录 ====================
@history_router.get("/activities")
async def get_activities(limit: int = 50, module: str = ""):
    return {"activities": store.get_activities(limit=limit, module=module)}


@history_router.get("/analyses")
async def get_analyses(limit: int = 20):
    return {"records": store.get_analyses(limit=limit)}


@history_router.get("/supplier-matches")
async def get_supplier_matches(limit: int = 20):
    return {"records": store.get_supplier_matches(limit=limit)}


@history_router.get("/content-records")
async def get_content_records(limit: int = 20):
    return {"records": store.get_content_records(limit=limit)}


@history_router.get("/products")
async def get_saved_products(keyword: str = "", category: str = "", limit: int = 50):
    return {"products": store.get_products(keyword=keyword, category=category, limit=limit)}


@history_router.get("/stats")
async def get_db_stats():
    return store.get_stats()


# ==================== 收藏 ====================
class FavoriteRequest(BaseModel):
    product_id: str = ""
    title: str
    price: float = 0
    category: str = ""
    note: str = ""


@history_router.post("/favorites")
async def add_favorite(req: FavoriteRequest):
    store.add_favorite(req.product_id, req.title, req.price, req.category, req.note)
    return {"status": "ok", "message": f"已收藏: {req.title}"}


@history_router.delete("/favorites/{fav_id}")
async def remove_favorite(fav_id: int):
    store.remove_favorite(fav_id)
    return {"status": "ok"}


@history_router.get("/favorites")
async def get_favorites(limit: int = 50):
    return {"favorites": store.get_favorites(limit=limit)}


# ==================== 支付 ====================
class AlipayRequest(BaseModel):
    order_id: str
    amount_cny: float
    subject: str = "1688采购付款"


class StripeRequest(BaseModel):
    order_id: str
    amount_usd: float
    product_name: str = ""


@payment_router.post("/alipay")
async def create_alipay_payment(req: AlipayRequest):
    result = await payment_service.create_alipay_order(req.order_id, req.amount_cny, req.subject)
    store.log_activity("payment", "创建支付宝付款", f"订单: {req.order_id}, ¥{req.amount_cny}")
    return result


@payment_router.post("/stripe")
async def create_stripe_payment(req: StripeRequest):
    result = await payment_service.create_stripe_checkout(req.order_id, req.amount_usd, req.product_name)
    store.log_activity("payment", "创建Stripe收款", f"订单: {req.order_id}, ${req.amount_usd}")
    return result


@payment_router.get("/channels")
async def get_payment_channels():
    channels = await payment_service.get_payment_channels()
    return {"channels": channels, "total": len(channels)}


@payment_router.get("/records")
async def get_payment_records(order_id: str = "", limit: int = 20):
    records = await payment_service.get_payment_records(order_id=order_id, limit=limit)
    return {"records": records, "total": len(records)}


# ==================== 用户中心 ====================
@user_router.post("/store-bindings")
async def bind_store(req: StoreBinding):
    """绑定店铺"""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO store_bindings (platform, store_name, store_id, store_url, access_token, country) VALUES (?,?,?,?,?,?)",
            (req.platform, req.store_name, req.store_id, req.store_url, req.access_token, req.country)
        )
    store.log_activity("user", "绑定店铺", f"{req.platform}: {req.store_name}")
    return {"status": "ok", "message": f"店铺 {req.store_name} 绑定成功"}


@user_router.get("/store-bindings")
async def get_store_bindings():
    """获取已绑定的店铺"""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM store_bindings WHERE is_active=1 ORDER BY created_at DESC").fetchall()
        return {"stores": [dict(r) for r in rows]}


@user_router.delete("/store-bindings/{binding_id}")
async def remove_store_binding(binding_id: int):
    """删除店铺绑定"""
    with get_conn() as conn:
        conn.execute("UPDATE store_bindings SET is_active=0 WHERE id=?", (binding_id,))
    return {"status": "ok"}
