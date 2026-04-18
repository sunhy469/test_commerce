"""EchoTik API 客户端 - 获取 TikTok 热销商品数据"""

import base64
import json
from urllib.parse import quote

import httpx

from app.db.store import get_products
from app.models.schemas import TikTokProduct
from config.settings import get_settings

class EchoTikClient:
    SEA_REGION_CODES = ("ID", "MY", "PH", "SG", "TH", "VN")
    REGION_STORAGE_FIELDS = (
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

    def __init__(self):
        settings = get_settings()

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
        return {"Content-Type": "application/json", "Accept": "application/json"}

    def _from_db_products(self, keyword: str = "", category: str = "", country: str = "", limit: int = 20) -> list[TikTokProduct]:
        rows = get_products(keyword=keyword, category=category, limit=max(limit, 1))
        products: list[TikTokProduct] = []
        for row in rows:
            if country and (row.get("country") or "") != country:
                continue
            products.append(TikTokProduct(**row))
            if len(products) >= limit:
                break
        return products

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

    def _build_storage_product(self, row: dict, region: str) -> dict:
        image_url = self._parse_sale_props_image(row.get("sale_props")) or self._parse_cover_url(row.get("cover_url"))
        product = {
            "product_id": str(row.get("product_id") or ""),
            "product_name": row.get("product_name") or "",
            "image_url": image_url,
            "region": row.get("region") or region,
        }
        for field in self.REGION_STORAGE_FIELDS:
            val = row.get(field, 0)
            product[field] = self._to_float(val, 0) if field.endswith("_amt") else self._to_int(val, 0)
        return product

    def _parse_sale_props_image(self, sale_props_raw) -> str:
        """从 sale_props 字段中提取第一张图片链接。"""
        if not sale_props_raw:
            return ""

        def _first_http_url(value) -> str:
            if isinstance(value, str):
                value = value.strip()
                return value if value.startswith("http") else ""
            if isinstance(value, dict):
                for key in ("url", "image", "image_url", "img", "cover"):
                    found = _first_http_url(value.get(key))
                    if found:
                        return found
                for key in ("sale_prop_values", "images", "img_list", "urls", "image_list"):
                    found = _first_http_url(value.get(key))
                    if found:
                        return found
                return ""
            if isinstance(value, list):
                for item in value:
                    found = _first_http_url(item)
                    if found:
                        return found
            return ""

        try:
            sale_props = sale_props_raw
            if isinstance(sale_props_raw, str):
                sale_props = sale_props_raw.strip()
                # 接口偶尔会返回二次 JSON 编码的字符串，最多解码两次。
                for _ in range(2):
                    if not isinstance(sale_props, str):
                        break
                    try:
                        sale_props = json.loads(sale_props)
                    except Exception:
                        break

            return _first_http_url(sale_props)
        except Exception:
            return ""

    def _build_product_from_product_list(self, row: dict, region: str) -> TikTokProduct:
        title = row.get("product_name") or row.get("desc_detail") or "TikTok Product"
        price = self._to_float(row.get("spu_avg_price"), 0)
        if price <= 0:
            min_price = self._to_float(row.get("min_price"), 0)
            max_price = self._to_float(row.get("max_price"), 0)
            price = round((min_price + max_price) / 2, 2) if min_price and max_price else (min_price or max_price or 0)

        image_url = (
                self._parse_sale_props_image(row.get("sale_props"))
                or self._parse_cover_url(row.get("cover_url"))
                or f"https://picsum.photos/seed/{quote(str(row.get('product_id') or title))}/400/400"
        )
        weekly_sales = self._to_int(row.get("total_sale_7d_cnt"), 0)
        daily_sales = self._to_int(row.get("total_sale_1d_cnt"), 0)
        if daily_sales <= 0 and weekly_sales > 0:
            daily_sales = max(weekly_sales // 7, 1)

        total_sales = self._to_int(row.get("total_sale_cnt"), 0)
        growth_rate = 0.0
        sale_30d = self._to_int(row.get("total_sale_30d_cnt"), 0)
        if sale_30d > 0:
            growth_rate = round((weekly_sales / sale_30d) * 100, 2)

        return TikTokProduct(
            product_id=str(row.get("product_id") or title),
            title=title,
            price=price,
            currency="USD",
            sales_count=total_sales,
            daily_sales=daily_sales,
            weekly_sales=weekly_sales,
            likes=self._to_int(row.get("total_views_cnt"), 0),
            comments=self._to_int(row.get("review_count"), 0),
            shop_name=str(row.get("seller_id") or ""),
            category=str(row.get("category_id") or ""),
            product_url=f"https://www.tiktok.com/shop/pdp/{quote(str(row.get('product_id') or ''))}",
            image_url=image_url,
            country=row.get("region") or region,
            growth_rate=growth_rate,
        )

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
        """搜索 TikTok 热销商品（使用 /echotik/product/list）。"""
        del days
        region = country or "US"

        if self.use_mock:
            return self._from_db_products(keyword=keyword, category=category, country=country, limit=limit)

        ranked_products: list[TikTokProduct] = []
        params = {
            "region": region,
            "page_num": 10,
            "page_size": 5,
            "sales_trend_flag": 1,
            "sort_type": 1,
            "product_sort_field": 4,  # total_sale_7d_cnt
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self.base_url}/echotik/product/list",
                    headers=self._get_headers(),
                    params=params,
                )
                resp.raise_for_status()
                payload = resp.json()
                if payload.get("code") != 0:
                    return self._from_db_products(keyword=keyword, category=category, country=country, limit=limit)
                rows = payload.get("data") or []
                for row in rows:
                    product = self._build_product_from_product_list(row, region=region)
                    ranked_products.append(product)
        except Exception:
            return self._from_db_products(keyword=keyword, category=category, country=country, limit=limit)

        if keyword:
            lower = keyword.lower()
            ranked_products = [p for p in ranked_products if lower in p.title.lower()]
        if category:
            ranked_products = [p for p in ranked_products if category.lower() in p.category.lower()] or ranked_products

        return ranked_products[:limit] if ranked_products else self._from_db_products(keyword=keyword, category=category, country=country, limit=limit)

    async def get_product_detail(self, product_id: str) -> TikTokProduct | None:
        if not product_id:
            return None
        for p in self._from_db_products(limit=200):
            if p.product_id == product_id:
                return p
        return None

    async def fetch_region_products_for_storage(self, region: str, page_num: int = 1, page_size: int = 50) -> list[dict]:
        """拉取指定国家商品并提取数据库存储所需字段。"""
        target_region = (region or "US").upper()
        if self.use_mock:
            return []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/echotik/product/list",
                headers=self._get_headers(),
                params={
                    "region": target_region,
                    "page_num": 10,
                    "page_size": 5,
                    "sales_trend_flag": 1,
                    "sort_type": 1,
                    "product_sort_field": 4,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("code") != 0:
                return []
            rows = payload.get("data") or []
            return [self._build_storage_product(row, target_region) for row in rows if row.get("product_id")]
