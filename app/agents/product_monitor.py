"""选品监控智能体 - TikTok 热销商品监控与分析"""

import json
from app.agents.base import BaseAgent
from app.services.echotik_client import EchoTikClient
from app.models.schemas import TikTokProduct, ProductAnalysis

SYSTEM_PROMPT = """你是一个专业的跨境电商选品分析师，专注于 TikTok Shop 爆品分析。
你需要分析商品数据并输出结构化的选品建议。

请用 JSON 格式输出分析结果，包含以下字段：
- sku_structure: SKU 结构分析（变体、组合方式）
- price_analysis: 价格带分析和定价建议
- promotion_strategy: 促销策略分析（如 Buy 2 Get 1 Free 等）
- seo_keywords: 5个推荐的 SEO 关键词（英文）
- pain_points: 该品类的用户痛点和差评分析
- recommendation_score: 推荐评分（1-10）
- summary: 综合分析摘要（中文，100字以内）

只输出 JSON，不要其他内容。"""


class ProductMonitorAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.echotik = EchoTikClient()
        from app.scrapers.tiktok_scraper import TikTokScraper
        self.scraper = TikTokScraper()

    async def run(
        self, keyword: str = "", category: str = "", limit: int = 10
    ) -> dict:
        """执行选品监控流程"""
        # Step 1: 获取热销商品数据
        products = await self.echotik.search_trending_products(
            keyword=keyword, category=category, limit=limit
        )

        if not products:
            return {"products": [], "analysis": None, "message": "未找到相关商品"}

        # Step 2: 用 Claude 分析爆品特征
        analysis_text = await self._analyze_products(products)

        # Step 3: 解析分析结果
        try:
            analysis_data = json.loads(analysis_text)
        except json.JSONDecodeError:
            analysis_data = {"summary": analysis_text, "recommendation_score": 0}

        # Step 4: 构建完整的分析结果
        product_analyses = []
        for product in products:
            pa = ProductAnalysis(
                product=product,
                sku_structure=analysis_data.get("sku_structure", ""),
                price_analysis=analysis_data.get("price_analysis", ""),
                promotion_strategy=analysis_data.get("promotion_strategy", ""),
                seo_keywords=analysis_data.get("seo_keywords", []),
                pain_points=analysis_data.get("pain_points", ""),
                recommendation_score=analysis_data.get("recommendation_score", 0),
                summary=analysis_data.get("summary", ""),
            )
            product_analyses.append(pa)

        return {
            "products": [p.model_dump() for p in products],
            "analysis": analysis_data,
            "product_analyses": [pa.model_dump() for pa in product_analyses],
            "total": len(products),
        }

    async def _analyze_products(self, products: list[TikTokProduct]) -> str:
        """分析商品列表的爆品特征"""
        products_info = "\n".join(
            [
                f"- {p.title} | ${p.price} | 销量:{p.sales_count} | 日销量:{p.daily_sales} | 近7天销量:{p.weekly_sales} | 类目:{p.category}"
                for p in products
            ]
        )

        user_prompt = f"""请分析以下 TikTok 热销商品数据，提供选品建议：

{products_info}

请从 SKU 结构、定价策略、促销方式、SEO 关键词、用户痛点等维度进行分析。"""

        return await self.think(SYSTEM_PROMPT, user_prompt)

    async def search(self, keyword: str, limit: int = 20, country: str = "", category: str = "") -> list[TikTokProduct]:
        """仅搜索，不分析"""
        products = await self.echotik.search_trending_products(
            keyword=keyword, country=country, category=category, limit=limit
        )
        if products and not all((p.product_id or '').startswith(('us_', 'gb_', 'id_', 'th_')) for p in products):
            return products
        scraped = await self.scraper.search_shop_products(keyword=keyword, limit=limit)
        return scraped or products
