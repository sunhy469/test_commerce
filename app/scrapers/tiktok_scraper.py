"""TikTok 数据采集爬虫

数据源优先级：
1. EchoTik 第三方 API（推荐，稳定）
2. TikTok 网页端采集（备用，需代理/会话）
"""

import httpx
import re
import json
import random
from datetime import datetime
from app.models.schemas import TikTokProduct
from config.settings import get_settings

# 常用 User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class TikTokScraper:
    """TikTok 商品数据采集器"""

    def __init__(self, proxy: str = None):
        settings = get_settings()
        self.proxy = proxy or settings.scraper_proxy or None
        self.session_cookie = settings.tiktok_session_cookie
        self.referer = settings.tiktok_referer or "https://www.tiktok.com/"
        self.user_agent = settings.tiktok_user_agent or random.choice(USER_AGENTS)
        self.session_headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": self.referer,
            "Sec-CH-UA": '"Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        if self.session_cookie:
            self.session_headers["Cookie"] = self.session_cookie

    def _get_client(self) -> httpx.AsyncClient:
        kwargs = {
            "headers": self.session_headers,
            "timeout": 30,
            "follow_redirects": True,
        }
        if self.proxy:
            kwargs["proxy"] = self.proxy
        return httpx.AsyncClient(**kwargs)

    async def search_shop_products(self, keyword: str, limit: int = 20) -> list[TikTokProduct]:
        """通过 TikTok 网页搜索结果页采集商品/视频数据（需要有效 cookie 更稳定）"""
        products = []
        try:
            async with self._get_client() as client:
                url = f"https://www.tiktok.com/search?q={keyword}"
                resp = await client.get(url)
                if resp.status_code != 200:
                    print(f"[TikTokScraper] 搜索请求失败: HTTP {resp.status_code}")
                    return []

                html = resp.text
                if "captcha" in html.lower() or "verify" in html.lower() or "robot" in html.lower():
                    print("[TikTokScraper] 页面返回风控/验证内容")
                    return []
                if "__UNIVERSAL_DATA_FOR_REHYDRATION__" not in html:
                    print(f"[TikTokScraper] 页面长度={len(html)}，未发现数据脚本")
                    print(html[:500])
                    return []

                match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.DOTALL)
                if not match:
                    print("[TikTokScraper] 未找到页面数据脚本，可能被风控")
                    return []

                page_data = json.loads(match.group(1))
                flat_text = json.dumps(page_data, ensure_ascii=False)
                candidates = re.findall(r'"desc":"(.*?)".*?"uniqueId":"(.*?)".*?"id":"(\\d+)"', flat_text)

                for idx, (desc, author, video_id) in enumerate(candidates[:limit]):
                    title = bytes(desc, 'utf-8').decode('unicode_escape', errors='ignore') if '\\u' in desc else desc
                    products.append(TikTokProduct(
                        product_id=f"tt_{video_id}",
                        title=(title or keyword)[:200],
                        price=0,
                        sales_count=0,
                        daily_sales=0,
                        weekly_sales=0,
                        likes=0,
                        comments=0,
                        shop_name=author,
                        category="TikTok Search",
                        product_url=f"https://www.tiktok.com/@{author}/video/{video_id}",
                        image_url=f"https://picsum.photos/seed/{video_id}/400/400",
                        country="US",
                    ))

        except Exception as e:
            print(f"[TikTokScraper] 搜索采集异常: {e}")

        return products[:limit]

    async def scrape_trending_hashtags(self, hashtags: list[str] = None) -> list[dict]:
        """采集热门标签下的视频和商品信息

        默认标签：#TikTokMadeMeBuyIt #SummerVibes 等
        """
        if hashtags is None:
            hashtags = [
                "TikTokMadeMeBuyIt",
                "tiktokviral",
                "musthave",
                "summervibes",
                "amazonfinds",
            ]

        results = []
        for tag in hashtags:
            try:
                async with self._get_client() as client:
                    url = f"https://www.tiktok.com/api/challenge/detail/"
                    params = {"challengeName": tag}
                    resp = await client.get(url, params=params)

                    if resp.status_code == 200:
                        data = resp.json()
                        challenge_info = data.get("challengeInfo", {})
                        stats = challenge_info.get("stats", {})
                        results.append({
                            "hashtag": f"#{tag}",
                            "view_count": stats.get("viewCount", 0),
                            "video_count": stats.get("videoCount", 0),
                            "description": challenge_info.get("challenge", {}).get("desc", ""),
                        })
                    else:
                        print(f"[TikTokScraper] 标签 #{tag} 请求失败: HTTP {resp.status_code}")

            except Exception as e:
                print(f"[TikTokScraper] 标签 #{tag} 采集异常: {e}")

        return results

    async def scrape_video_products(self, video_url: str) -> dict:
        """从单个 TikTok 视频页面提取关联商品信息"""
        try:
            async with self._get_client() as client:
                resp = await client.get(video_url)
                if resp.status_code != 200:
                    return {"error": f"HTTP {resp.status_code}"}

                html = resp.text

                # 从页面 script 标签提取 JSON 数据
                pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>'
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    page_data = json.loads(json_str)
                    video_detail = (
                        page_data.get("__DEFAULT_SCOPE__", {})
                        .get("webapp.video-detail", {})
                        .get("itemInfo", {})
                        .get("itemStruct", {})
                    )

                    return {
                        "video_id": video_detail.get("id", ""),
                        "description": video_detail.get("desc", ""),
                        "views": video_detail.get("stats", {}).get("playCount", 0),
                        "likes": video_detail.get("stats", {}).get("diggCount", 0),
                        "comments": video_detail.get("stats", {}).get("commentCount", 0),
                        "shares": video_detail.get("stats", {}).get("shareCount", 0),
                        "author": video_detail.get("author", {}).get("uniqueId", ""),
                        "hashtags": [
                            t.get("hashtagName", "")
                            for t in video_detail.get("textExtra", [])
                            if t.get("hashtagName")
                        ],
                    }

                return {"error": "无法解析页面数据"}

        except Exception as e:
            return {"error": str(e)}

    def _parse_search_result(self, item: dict) -> TikTokProduct | None:
        """解析搜索结果为商品对象"""
        try:
            # TikTok 搜索结果结构因类型而异
            if item.get("type") == 1:  # 视频类型
                video = item.get("item", {})
                return TikTokProduct(
                    product_id=video.get("id", f"tt_{datetime.now().timestamp()}"),
                    title=video.get("desc", "")[:200],
                    price=0,
                    sales_count=0,
                    daily_sales=0,
                    weekly_sales=0,
                    likes=video.get("stats", {}).get("diggCount", 0),
                    comments=video.get("stats", {}).get("commentCount", 0),
                    shop_name=video.get("author", {}).get("uniqueId", ""),
                    category="",
                    product_url=f"https://www.tiktok.com/@{video.get('author', {}).get('uniqueId', '')}/video/{video.get('id', '')}",
                )
        except Exception as e:
            print(f"[TikTokScraper] 解析异常: {e}")
        return None
