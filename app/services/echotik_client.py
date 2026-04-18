"""EchoTik API 客户端 - 获取 TikTok 热销商品数据"""

import base64
import json
from urllib.parse import quote

import httpx

from app.models.schemas import TikTokProduct
from config.settings import get_settings

# Mock 数据 - 多国家、多品类、含图片和销量数据
MOCK_PRODUCTS = [
    TikTokProduct(product_id="us_001", title="Sunset Glow Blush Palette - Summer Vibes Collection", price=12.99,
        sales_count=15800, daily_sales=520, weekly_sales=3640, likes=189000, comments=4200,
        shop_name="GlowBeautyOfficial", category="Beauty & Personal Care", country="US", growth_rate=23.5,
        image_url="https://picsum.photos/seed/blush/400/400", product_url="https://www.tiktok.com/"),
    TikTokProduct(product_id="us_002", title="Portable Mini Fan USB Rechargeable Neck Fan", price=8.99,
        sales_count=32000, daily_sales=1100, weekly_sales=7700, likes=410000, comments=8900,
        shop_name="CoolTechStore", category="Electronics", country="US", growth_rate=45.2,
        image_url="https://picsum.photos/seed/fan/400/400", product_url="https://www.tiktok.com/"),
    TikTokProduct(product_id="us_003", title="Cloud Slide Sandals Thick Sole Anti-slip", price=15.99,
        sales_count=28500, daily_sales=950, weekly_sales=6650, likes=356000, comments=7100,
        shop_name="ComfyWalkShop", category="Shoes & Fashion", country="US", growth_rate=38.7,
        image_url="https://picsum.photos/seed/slides/400/400", product_url="https://www.tiktok.com/"),
    TikTokProduct(product_id="us_004", title="LED Sunset Projection Lamp Rainbow Night Light", price=11.49,
        sales_count=19200, daily_sales=640, weekly_sales=4480, likes=298000, comments=5600,
        shop_name="HomeVibesDecor", category="Home & Garden", country="US", growth_rate=18.3,
        image_url="https://picsum.photos/seed/lamp/400/400", product_url="https://www.tiktok.com/"),
    TikTokProduct(product_id="us_005", title="Matcha Whisk Set Bamboo Tea Ceremony Kit", price=19.99,
        sales_count=8900, daily_sales=290, weekly_sales=2030, likes=120000, comments=3200,
        shop_name="ZenTeaHouse", category="Food & Beverages", country="US", growth_rate=12.1,
        image_url="https://picsum.photos/seed/matcha/400/400", product_url="https://www.tiktok.com/"),
    TikTokProduct(product_id="id_002", title="Phone Case Casing HP Aesthetic Lucu", price=2.99,
        sales_count=68000, daily_sales=2300, weekly_sales=16100, likes=380000, comments=9200,
        shop_name="CaseMurah", category="Electronics", country="ID", growth_rate=78.5,
        image_url="https://picsum.photos/seed/phonecase/400/400", product_url="https://www.tiktok.com/"),
    TikTokProduct(product_id="th_001", title="เซรั่มบำรุงผิวหน้า Vitamin C Serum", price=5.99,
        sales_count=38000, daily_sales=1280, weekly_sales=8960, likes=450000, comments=10200,
        shop_name="ThaiBeautyBKK", category="Beauty & Personal Care", country="TH", growth_rate=55.8,
        image_url="https://picsum.photos/seed/thaiserum/400/400", product_url="https://www.tiktok.com/"),
]


class EchoTikClient:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.echotik_api_key
        self.username = settings.echotik_username
        self.password = settings.echotik_password
        self.base_url = settings.echotik_base_url.rstrip("/")
        self.use_mock = not (self.username and self.password)

    def _get_headers(self) -> dict:
        if self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("utf-8")
            return {
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        if self.api_key:
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        return {"Content-Type": "application/json", "Accept": "application/json"}

    def _mock_products(self, keyword: str = "", category: str = "", country: str = "", limit: int = 20) -> list[TikTokProduct]:
        results = list(MOCK_PRODUCTS)
        if keyword:
            lower = keyword.lower()
            results = [p for p in results if lower in p.title.lower() or lower in p.category.lower()]
        if category:
            results = [p for p in results if category.lower() in p.category.lower()]
        if country:
            results = [p for p in results if p.country == country]
        return (results or MOCK_PRODUCTS)[:limit]

    def _extract_value(self, data: dict, key: str, default=None):
        node = (data or {}).get(key, default)
        if isinstance(node, dict) and "value" in node:
            return node.get("value")
        return node if node is not None else default

    def _to_float(self, value, default: float = 0.0) -> float:
        try:
            if isinstance(value, dict):
                value = value.get("value")
            if value in (None, "", False):
                return default
            return float(str(value).replace(",", ""))
        except Exception:
            return default

    def _to_int(self, value, default: int = 0) -> int:
        try:
            if isinstance(value, dict):
                value = value.get("value")
            if value in (None, "", False):
                return default
            return int(float(str(value).replace(",", "")))
        except Exception:
            return default

    def _parse_cover_url(self, raw_cover: str) -> str:
        try:
            if not raw_cover:
                return ""
            items = json.loads(raw_cover)
            if isinstance(items, list) and items:
                items = sorted(items, key=lambda x: x.get("index", 9999))
                return items[0].get("url", "")
        except Exception:
            return ""
        return ""

    def _build_product_from_influencer_and_goods(self, influencer: dict, goods: dict, region: str) -> TikTokProduct:
        product_name = goods.get("product_name") or influencer.get("nick_name") or influencer.get("unique_id") or "TikTok Product"
        cover_url = self._parse_cover_url(goods.get("cover_url", "")) or influencer.get("avatar", "")
        total_sale_cnt = self._to_int(goods.get("total_sale_cnt"), 0)
        total_video_sale_cnt = self._to_int(goods.get("total_video_sale_cnt"), 0)
        total_digg_cnt = self._to_int(influencer.get("total_digg_cnt"), 0)
        total_comments_cnt = self._to_int(influencer.get("total_comments_cnt"), 0)
        total_followers_7d_cnt = self._to_int(influencer.get("total_followers_7d_cnt"), 0)
        return TikTokProduct(
            product_id=str(goods.get("product_id") or influencer.get("user_id") or influencer.get("unique_id") or product_name),
            title=product_name,
            price=self._to_float(goods.get("spu_avg_price"), 0),
            currency="USD",
            sales_count=total_sale_cnt,
            daily_sales=max(total_video_sale_cnt // 7, 0),
            weekly_sales=total_video_sale_cnt,
            likes=total_digg_cnt,
            comments=total_comments_cnt,
            shop_name=influencer.get("nick_name") or influencer.get("unique_id") or "",
            category=influencer.get("category") or goods.get("category_id") or "TikTok Shop",
            product_url=f"https://www.tiktok.com/@{quote(str(influencer.get('unique_id') or ''))}",
            image_url=cover_url or f"https://picsum.photos/seed/{quote(str(product_name))}/400/400",
            country=region,
            growth_rate=float(total_followers_7d_cnt),
        )

    async def get_influencer_list(self, region: str = "US", page_num: int = 1, page_size: int = 10, sort_field: int = 6) -> list[dict]:
        if self.use_mock:
            return []

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/echotik/influencer/list",
                headers=self._get_headers(),
                params={
                    "region": region,
                    "page_num": page_num,
                    "page_size": min(page_size, 10),
                    "influencer_sort_field_v2": sort_field,
                    "sort_type": 1,
                    "sales_flag": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                return []
            return data.get("data") or []

    async def get_influencer_products(self, user_id: str, page_num: int = 1, page_size: int = 3) -> list[dict]:
        if self.use_mock or not user_id:
            return []

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/echotik/influencer/product/list",
                headers=self._get_headers(),
                params={
                    "user_id": user_id,
                    "page_num": page_num,
                    "page_size": min(page_size, 10),
                    "influencer_product_sort_field": 1,
                    "sort_type": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                return []
            return data.get("data") or []

    def _build_product_from_sale_detail(self, creator_oecuid: str, region: str, data: dict) -> TikTokProduct:
        industry_groups = self._extract_value(data, "industry_groups", []) or []
        category = industry_groups[0].get("name", "TikTok Shop") if industry_groups else "TikTok Shop"
        revenue = self._extract_value(data, "med_gmv_revenue", {}) or {}
        revenue_value = self._to_float(revenue if not isinstance(revenue, dict) else revenue.get("value"), 0)
        units_sold = self._to_int(self._extract_value(data, "units_sold", 0), 0)
        promoted_product_num = max(self._to_int(self._extract_value(data, "promoted_product_num", 1), 1), 1)
        avg_price = round(revenue_value / promoted_product_num, 2) if revenue_value > 0 else 0
        title = f"EchoTik Real-time Creator {creator_oecuid[-6:]}"
        return TikTokProduct(
            product_id=f"echotik_{creator_oecuid}_{region}",
            title=title,
            price=avg_price,
            currency="USD",
            sales_count=units_sold,
            daily_sales=max(units_sold // 7, 0),
            weekly_sales=units_sold,
            likes=self._to_int(self._extract_value(data, "video_med_like_cnt", 0), 0),
            comments=self._to_int(self._extract_value(data, "video_med_comment_cnt", 0), 0),
            shop_name=f"creator_{creator_oecuid[-6:]}",
            category=category,
            product_url=f"https://www.tiktok.com/@creator/video/{creator_oecuid[-12:]}",
            image_url=f"https://picsum.photos/seed/echotik-{quote(creator_oecuid)}/400/400",
            country=region,
            growth_rate=self._to_float(self._extract_value(data, "gpm", {}).get("value") if isinstance(self._extract_value(data, "gpm", {}), dict) else self._extract_value(data, "gpm", 0), 0),
        )

    async def get_creator_sale_detail(self, creator_oecuid: str, region: str = "US") -> dict:
        if self.use_mock:
            return {"code": 0, "message": "mock", "data": {}}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/realtime/tts/sale_detail",
                headers=self._get_headers(),
                params={"creator_oecuid": creator_oecuid, "region": region},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_creator_intro_detail(self, creator_oecuid: str, region: str = "US") -> dict:
        if self.use_mock:
            return {"code": 0, "message": "mock", "data": {}}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/realtime/tts/intro_detail",
                headers=self._get_headers(),
                params={"creator_oecuid": creator_oecuid, "region": region},
            )
            resp.raise_for_status()
            return resp.json()

    async def search_creator_oecuid(self, unique_id: str, region: str = "US") -> str:
        if self.use_mock or not unique_id:
            return ""

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/realtime/tts/search_by_unique_id",
                headers=self._get_headers(),
                params={"unique_id": unique_id, "region": region},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                return ""
            return str(data.get("data") or "")

    async def get_creator_product_by_unique_id(self, unique_id: str, region: str = "US") -> TikTokProduct | None:
        creator_oecuid = await self.search_creator_oecuid(unique_id=unique_id, region=region)
        if not creator_oecuid:
            return None

        detail = await self.get_creator_sale_detail(creator_oecuid=creator_oecuid, region=region)
        intro = await self.get_creator_intro_detail(creator_oecuid=creator_oecuid, region=region)
        if detail.get("code") != 0 or not detail.get("data"):
            return None

        product = self._build_product_from_sale_detail(creator_oecuid=creator_oecuid, region=region, data=detail.get("data") or {})
        intro_data = intro.get("data") or {}
        handle = self._extract_value(intro_data, "handle", unique_id) or unique_id
        nickname = self._extract_value(intro_data, "nickname", handle) or handle
        avatar = self._extract_value(intro_data, "avatar", {}) or {}
        avatar_urls = avatar.get("url_list") if isinstance(avatar, dict) else []
        categories = self._extract_value(intro_data, "category", []) or []

        product.shop_name = handle
        product.title = f"{nickname} - TikTok Shop Creator Sales"
        product.product_url = f"https://www.tiktok.com/@{quote(handle)}"
        if avatar_urls:
            product.image_url = avatar_urls[0]
        if categories:
            product.category = ", ".join([c.get("name", "") for c in categories if c.get("name")]) or product.category
        product.comments = self._to_int(self._extract_value(detail.get("data") or {}, "video_med_comment_cnt", product.comments), product.comments)
        product.likes = self._to_int(self._extract_value(detail.get("data") or {}, "video_med_like_cnt", product.likes), product.likes)
        return product

    async def search_trending_products(
        self, keyword: str = "", category: str = "", country: str = "", days: int = 7, limit: int = 20
    ) -> list[TikTokProduct]:
        """搜索 TikTok 热销商品。关键词优先走实时 creator 查询；无关键词则走 EchoTik 离线达人列表+商品列表。"""
        del days
        region = country or "US"

        if self.use_mock:
            return self._mock_products(keyword=keyword, category=category, country=country, limit=limit)

        if keyword:
            real_product = await self.get_creator_product_by_unique_id(unique_id=keyword, region=region)
            if real_product:
                products = [real_product]
                if category:
                    products = [p for p in products if category.lower() in p.category.lower()] or products
                return products[:limit]
            return self._mock_products(keyword=keyword, category=category, country=country, limit=limit)

        influencers = await self.get_influencer_list(region=region, page_num=1, page_size=min(limit, 10), sort_field=6)
        ranked_products: list[TikTokProduct] = []
        for influencer in influencers:
            goods = await self.get_influencer_products(user_id=str(influencer.get("user_id") or ""), page_num=1, page_size=1)
            if goods:
                ranked_products.append(self._build_product_from_influencer_and_goods(influencer, goods[0], region))
            else:
                ranked_products.append(
                    TikTokProduct(
                        product_id=str(influencer.get("user_id") or influencer.get("unique_id") or ""),
                        title=influencer.get("nick_name") or influencer.get("unique_id") or "TikTok Creator",
                        price=self._to_float(influencer.get("avg_30d_price"), 0),
                        sales_count=self._to_int(influencer.get("total_sale_cnt"), 0),
                        daily_sales=max(self._to_int(influencer.get("total_video_sale_30d_cnt"), 0) // 30, 0),
                        weekly_sales=max(self._to_int(influencer.get("total_video_sale_30d_cnt"), 0) // 4, 0),
                        likes=self._to_int(influencer.get("total_digg_cnt"), 0),
                        comments=self._to_int(influencer.get("total_comments_cnt"), 0),
                        shop_name=influencer.get("nick_name") or influencer.get("unique_id") or "",
                        category=influencer.get("category") or "TikTok Shop",
                        product_url=f"https://www.tiktok.com/@{quote(str(influencer.get('unique_id') or ''))}",
                        image_url=influencer.get("avatar") or f"https://picsum.photos/seed/{quote(str(influencer.get('unique_id') or 'creator'))}/400/400",
                        country=region,
                        growth_rate=float(self._to_int(influencer.get("total_followers_7d_cnt"), 0)),
                    )
                )
            if len(ranked_products) >= limit:
                break

        if category:
            ranked_products = [p for p in ranked_products if category.lower() in p.category.lower()] or ranked_products
        return ranked_products[:limit] if ranked_products else self._mock_products(keyword=keyword, category=category, country=country, limit=limit)

    async def get_product_detail(self, product_id: str) -> TikTokProduct | None:
        for p in MOCK_PRODUCTS:
            if p.product_id == product_id:
                return p
        return None
