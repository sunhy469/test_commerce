"""爬虫测试和直接调用 API"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.scrapers.tiktok_scraper import TikTokScraper
from app.scrapers.alibaba_scraper import AlibabaScraper

scraper_router = APIRouter(prefix="/api/scraper", tags=["爬虫采集"])

tiktok = TikTokScraper()
alibaba = AlibabaScraper()


# ==================== TikTok 爬虫 ====================
@scraper_router.get("/tiktok/trending-tags")
async def scrape_tiktok_tags():
    """采集 TikTok 热门标签数据"""
    results = await tiktok.scrape_trending_hashtags()
    return {"hashtags": results, "total": len(results)}


@scraper_router.get("/tiktok/search")
async def scrape_tiktok_search(keyword: str, limit: int = 20, region: str = "US"):
    """TikTok 商品搜索采集"""
    from app.services.echotik_client import EchoTikClient
    echotik = EchoTikClient()

    real_products = await echotik.search_trending_products(keyword=keyword, country=region, limit=limit)
    if real_products:
        return {
            "products": [p.model_dump() for p in real_products],
            "total": len(real_products),
            "source": "echotik_basic_auth",
        }

    products = await tiktok.search_shop_products(keyword, limit)
    return {
        "products": [p.model_dump() for p in products],
        "total": len(products),
        "source": "tiktok_scraper",
    }


class VideoRequest(BaseModel):
    url: str


@scraper_router.post("/tiktok/video")
async def scrape_tiktok_video(req: VideoRequest):
    """采集单个 TikTok 视频的商品信息"""
    result = await tiktok.scrape_video_products(req.url)
    return result


# ==================== 1688 爬虫 ====================
@scraper_router.get("/alibaba/search")
async def scrape_alibaba_search(keyword: str, limit: int = 20):
    """1688 商品搜索"""
    # 优先 API，然后网页
    results = await alibaba.search_products_api(keyword)
    source = "1688_api"
    if not results:
        results = await alibaba.search_products_web(keyword, limit)
        source = "1688_web"
    return {"products": results, "total": len(results), "source": source}


class ImageSearchRequest(BaseModel):
    image_url: str
    limit: int = 10


@scraper_router.post("/alibaba/image-search")
async def scrape_alibaba_image(req: ImageSearchRequest):
    """1688 以图搜货"""
    results = await alibaba.search_by_image(req.image_url, req.limit)
    return {"results": results, "total": len(results), "source": "1688_image_search"}


# ==================== 状态检查 ====================
@scraper_router.get("/status")
async def scraper_status():
    """检查各爬虫/API 的可用状态"""
    return {
        "tiktok_scraper": "ready_with_cookie",
        "echotik_api": "needs_api_key",
        "alibaba_api": "pending_enterprise_auth",
        "alibaba_web": "ready_with_risk",
        "alibaba_image_search": "ready",
        "note": "若要跑通真实 TikTok 数据，请填写 TIKTOK_SESSION_COOKIE，必要时配置 SCRAPER_PROXY；1688 开放平台仍需企业认证。",
    }
