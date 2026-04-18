"""1688 数据采集

数据源：
1. 1688 开放平台 API（需企业认证，审核中）
2. 1688 图片搜索（找同款）
"""

import httpx
import hashlib
import time
import json
import re
import random
from config.settings import get_settings

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class AlibabaScraper:
    """1688 商品数据采集器"""

    def __init__(self):
        settings = get_settings()
        self.account = settings.alibaba_account
        self.password = settings.alibaba_password
        # 1688 开放平台 API 配置（企业认证通过后填入）
        self.app_key = ""
        self.app_secret = ""
        self.access_token = ""
        self.api_base = "https://gw.open.1688.com/openapi"

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": "https://www.1688.com/",
            },
            timeout=30,
            follow_redirects=True,
        )

    # ==================== 1688 开放平台 API ====================

    def _sign_request(self, api_path: str, params: dict) -> str:
        """生成 1688 API 签名"""
        # 1688 开放平台签名规则：md5(secret + path + sorted_params + secret)
        sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
        sign_str = f"{self.app_secret}{api_path}{sorted_params}{self.app_secret}"
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    async def search_products_api(self, keyword: str, page: int = 1, page_size: int = 20) -> list[dict]:
        """通过 1688 开放平台 API 搜索商品（需企业认证）

        API: com.alibaba.product:alibaba.product.search
        文档: https://open.1688.com/api/
        """
        if not self.app_key:
            print("[1688API] 未配置 app_key，请完成企业认证后设置")
            return []

        api_path = "param2/1/com.alibaba.product/alibaba.product.search"
        params = {
            "access_token": self.access_token,
            "keyword": keyword,
            "page": str(page),
            "pageSize": str(page_size),
            "_aop_timestamp": str(int(time.time() * 1000)),
        }
        params["_aop_signature"] = self._sign_request(api_path, params)

        try:
            async with self._get_client() as client:
                url = f"{self.api_base}/{api_path}/{self.app_key}"
                resp = await client.get(url, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    products = []
                    for item in data.get("result", {}).get("products", []):
                        products.append({
                            "supplier_id": item.get("productId", ""),
                            "name": item.get("subject", ""),
                            "price_cny": float(item.get("referencePrice", "0").replace("元", "")),
                            "moq": item.get("quantityBegin", 1),
                            "image_url": item.get("imageUrl", ""),
                            "supplier_name": item.get("supplierLoginId", ""),
                            "location": item.get("province", "") + item.get("city", ""),
                        })
                    return products
                else:
                    print(f"[1688API] 搜索失败: HTTP {resp.status_code}")
                    return []

        except Exception as e:
            print(f"[1688API] 搜索异常: {e}")
            return []

    async def get_product_detail_api(self, product_id: str) -> dict:
        """获取 1688 商品详情（需企业认证）"""
        if not self.app_key:
            return {"error": "未配置 app_key"}

        api_path = "param2/1/com.alibaba.product/alibaba.product.get"
        params = {
            "access_token": self.access_token,
            "productId": product_id,
            "_aop_timestamp": str(int(time.time() * 1000)),
        }
        params["_aop_signature"] = self._sign_request(api_path, params)

        try:
            async with self._get_client() as client:
                url = f"{self.api_base}/{api_path}/{self.app_key}"
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    # ==================== 1688 图片搜索（找同款） ====================

    async def search_by_image(self, image_url: str, limit: int = 10) -> list[dict]:
        """1688 以图搜货 - 上传 TikTok 商品主图找 1688 同款

        流程：
        1. 下载 TikTok 商品图片
        2. 自动去除 TikTok 水印
        3. 上传到 1688 图片搜索接口
        4. 返回匹配结果
        """
        try:
            # Step 1: 下载图片
            async with self._get_client() as client:
                img_resp = await client.get(image_url)
                if img_resp.status_code != 200:
                    return [{"error": f"图片下载失败: HTTP {img_resp.status_code}"}]
                image_data = img_resp.content

            # Step 2: 上传到 1688 图搜接口
            async with self._get_client() as client:
                # 1688 图片搜索接口
                upload_url = "https://search.1688.com/img/uploadImage"
                files = {"file": ("search.jpg", image_data, "image/jpeg")}
                upload_resp = await client.post(upload_url, files=files)

                if upload_resp.status_code != 200:
                    return [{"error": f"图片上传失败: HTTP {upload_resp.status_code}"}]

                upload_data = upload_resp.json()
                image_id = upload_data.get("data", {}).get("imageId", "")

                if not image_id:
                    return [{"error": "图片上传成功但未获取到 imageId"}]

            # Step 3: 用 imageId 搜索同款
            async with self._get_client() as client:
                search_url = "https://search.1688.com/img/imageSearch"
                params = {"imageId": image_id, "pageSize": limit}
                search_resp = await client.get(search_url, params=params)

                if search_resp.status_code == 200:
                    search_data = search_resp.json()
                    results = []
                    for item in search_data.get("data", {}).get("offerList", []):
                        results.append({
                            "supplier_id": item.get("offerId", ""),
                            "name": item.get("subject", ""),
                            "price_cny": item.get("priceInfo", {}).get("price", 0),
                            "image_url": item.get("imageUrl", ""),
                            "supplier_name": item.get("company", {}).get("name", ""),
                            "location": item.get("company", {}).get("province", ""),
                            "match_score": item.get("score", 0),
                        })
                    return results[:limit]
                else:
                    return [{"error": f"搜索失败: HTTP {search_resp.status_code}"}]

        except Exception as e:
            print(f"[1688Scraper] 图片搜索异常: {e}")
            return [{"error": str(e)}]

    # ==================== 网页端采集（备用） ====================

    async def search_products_web(self, keyword: str, limit: int = 20) -> list[dict]:
        """通过 1688 网页端搜索（备用方案，可能触发验证码）"""
        try:
            async with self._get_client() as client:
                url = "https://s.1688.com/selloffer/offer_search.htm"
                params = {
                    "keywords": keyword,
                    "n": "y",
                    "spm": "",
                }
                resp = await client.get(url, params=params)

                if resp.status_code != 200:
                    return [{"error": f"HTTP {resp.status_code}，可能触发了反爬验证"}]

                # 简单提取（实际需要更复杂的解析）
                html = resp.text
                # 尝试从页面内嵌 JSON 提取数据
                data_match = re.search(r'__INITIAL_DATA__\s*=\s*({.*?})\s*;', html, re.DOTALL)

                if data_match:
                    try:
                        page_data = json.loads(data_match.group(1))
                        offers = page_data.get("data", {}).get("offerList", [])
                        return [
                            {
                                "supplier_id": o.get("id", ""),
                                "name": o.get("information", {}).get("subject", ""),
                                "price_cny": o.get("tradePrice", {}).get("price", 0),
                                "supplier_name": o.get("company", {}).get("name", ""),
                                "location": o.get("company", {}).get("province", ""),
                            }
                            for o in offers[:limit]
                        ]
                    except json.JSONDecodeError:
                        pass

                return [{"error": "页面解析失败，可能需要登录或被反爬拦截"}]

        except Exception as e:
            return [{"error": str(e)}]
