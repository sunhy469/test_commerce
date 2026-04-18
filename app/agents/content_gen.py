"""内容生成智能体 - AI页面仿制 + 图片处理 + HTML落地页生成"""

import json
from app.agents.base import BaseAgent
from app.services.image_processor import ImageProcessor
from app.services.page_generator import PageGenerator
from app.services.seed_client import SeedClient

SYSTEM_PROMPT_PAGE = """你是一个专业的 TikTok Shop 商品页面设计师和文案专家。
根据商品信息，生成一个完整的商品页面内容方案。

请用 JSON 格式输出，包含以下字段：
- page_title: 商品标题（英文，包含SEO关键词，吸引点击）
- description: 商品描述（英文，口语化，适合北美/东南亚市场）
- bullet_points: 5个卖点要点（英文）
- seo_tags: 5个SEO标签
- price_suggestion: 建议定价策略
- review_templates: 3条模拟热门评论（英文，自然真实风格）
- pain_points: 该商品解决的用户痛点（英文）
- landing_page_sections: 页面板块结构（标题+内容概要）

只输出 JSON，不要其他内容。"""


class ContentGenAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.image_processor = ImageProcessor()
        self.page_generator = PageGenerator()
        self.seed_client = SeedClient()

    async def run(self, product: dict, content_type: str = "all") -> dict:
        """生成内容"""
        result = {}

        if content_type in ("page", "all"):
            page_data = await self._generate_page(product)
            result["page"] = page_data

            # 生成可部署的 HTML 落地页
            html_result = self.page_generator.generate(page_data, product)
            result["html_page"] = html_result

        if content_type in ("image", "all"):
            result["image_job"] = await self.seed_client.build_image_job(
                product,
                prompt=product.get("_image_prompt", ""),
                style=product.get("_image_style", "minimal-clean"),
            )

        # 处理商品图片（如果有图片URL）
        image_url = product.get("image_url", "")
        if image_url and image_url != "" and not image_url.startswith("https://example.com"):
            img_result = await self.image_processor.process_product_image(
                image_url=image_url,
                source="tiktok",
                remove_bg=False,
                filter_type="aesthetic",
                remove_chinese=True,
            )
            result["processed_image"] = img_result

        return result

    async def _generate_page(self, product: dict) -> dict:
        """生成商品页面内容"""
        user_prompt = f"""请为以下商品生成 TikTok Shop 商品页面内容：

商品名称: {product.get('title', 'N/A')}
价格: ${product.get('price', 0)}
类目: {product.get('category', 'N/A')}
销量: {product.get('sales_count', 0)}

要求：
1. 转换为目标市场（北美/东南亚）的口语化表达
2. 自动生成5个吸引人的SEO标签
3. 提供商品Pain Point（痛点）解决方案
4. 生成3条自然风格的热门评论模板"""

        result_text = await self.think(SYSTEM_PROMPT_PAGE, user_prompt)
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {"page_title": product.get("title", ""), "raw_content": result_text}

    async def process_image(
        self,
        image_url: str,
        source: str = "1688",
        remove_bg: bool = False,
        filter_type: str = "clean",
        remove_chinese: bool = True,
    ) -> dict:
        """单独处理图片（供API调用）"""
        return await self.image_processor.process_product_image(
            image_url=image_url,
            source=source,
            remove_bg=remove_bg,
            filter_type=filter_type,
            remove_chinese=remove_chinese,
        )
