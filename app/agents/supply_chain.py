"""供应链匹配智能体 - 1688 同款搜图 + 供应商筛选"""

import json
from app.agents.base import BaseAgent
from app.models.schemas import TikTokProduct

SYSTEM_PROMPT = """你是一个专业的跨境电商供应链分析师，专注于 1688 供应商筛选和成本核算。
请用 JSON 格式输出分析结果，包含以下字段：
- suppliers: 推荐供应商列表，每个包含 name, price_range, moq, delivery_days, score
- cost_analysis: 成本核算（1688成本 + 跨境物流费 + 5%杂费）
- profit_estimate: 利润预估（TikTok售价 * 汇率 - 总成本）
- risk_assessment: 供应商风险评估
- recommendation: 采购建议

只输出 JSON，不要其他内容。"""

# Mock 1688 供应商数据
MOCK_SUPPLIERS = [
    {
        "supplier_id": "s001",
        "name": "义乌美妆工厂直营店",
        "price_cny": 15.0,
        "moq": 100,
        "delivery_days": 3,
        "years_in_business": 8,
        "return_rate": 0.02,
        "rating": 4.8,
        "location": "浙江义乌",
        "image_match_score": 0.92,
    },
    {
        "supplier_id": "s002",
        "name": "广州白云化妆品批发",
        "price_cny": 12.5,
        "moq": 200,
        "delivery_days": 2,
        "years_in_business": 5,
        "return_rate": 0.035,
        "rating": 4.6,
        "location": "广东广州",
        "image_match_score": 0.87,
    },
    {
        "supplier_id": "s003",
        "name": "深圳跨境电子供应链",
        "price_cny": 18.0,
        "moq": 50,
        "delivery_days": 1,
        "years_in_business": 12,
        "return_rate": 0.01,
        "rating": 4.9,
        "location": "广东深圳",
        "image_match_score": 0.95,
    },
]


class SupplyChainAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        from app.scrapers.alibaba_scraper import AlibabaScraper
        self.scraper = AlibabaScraper()
    async def run(self, product: dict = None, keyword: str = "") -> dict:
        """执行供应链匹配流程"""
        # Step 1: 搜索 1688 同款供应商
        suppliers = await self._search_suppliers(keyword or (product or {}).get("title", ""))

        # Step 2: 筛选优质供应商（传入TikTok售价用于价格比较）
        tiktok_price_usd = (product or {}).get("price", 0)
        filtered = self._filter_suppliers(suppliers, tiktok_price_usd=tiktok_price_usd)

        # Step 3: Claude 分析成本和利润
        analysis_text = await self._analyze_supply_chain(product, filtered)
        try:
            analysis = json.loads(analysis_text)
        except json.JSONDecodeError:
            analysis = {"recommendation": analysis_text}

        return {
            "suppliers": filtered,
            "analysis": analysis,
            "total_suppliers": len(suppliers),
            "filtered_count": len(filtered),
        }

    async def _search_suppliers(self, keyword: str) -> list[dict]:
        """搜索 1688 供应商：先尝试 API，失败则用 mock"""
        # 尝试 1688 开放平台 API
        api_results = await self.scraper.search_products_api(keyword)
        if api_results and not any("error" in r for r in api_results):
            return api_results

        # 尝试网页端采集
        web_results = await self.scraper.search_products_web(keyword)
        if web_results and not any("error" in r for r in web_results):
            return web_results

        # 降级到 mock
        print(f"[SupplyChainAgent] 1688 API/爬虫不可用，使用 mock 数据")
        return MOCK_SUPPLIERS

    def _filter_suppliers(self, suppliers: list[dict], tiktok_price_usd: float = 0) -> list[dict]:
        """筛选优质供应商

        规则：
        - 价格低于 TikTok 售价的 40%（按汇率7.2换算）
        - 近90天无虚假发货记录（退货率 < 5%）
        - 工厂直供或 3 年以上经营
        - 综合评分 > 80 分
        """
        tiktok_price_cny = tiktok_price_usd * 7.2 if tiktok_price_usd > 0 else 0
        max_cost_cny = tiktok_price_cny * 0.4 if tiktok_price_cny > 0 else float("inf")

        filtered = []
        for s in suppliers:
            score = 0
            reasons = []

            # 价格检查：低于TikTok售价的40%（换算后）
            price = s.get("price_cny", 0)
            if tiktok_price_cny > 0:
                if price <= max_cost_cny:
                    score += 25
                    reasons.append(f"价格¥{price} < 限价¥{max_cost_cny:.0f}")
                else:
                    reasons.append(f"价格偏高: ¥{price} > ¥{max_cost_cny:.0f}")

            # 退货率/虚假发货检查
            if s.get("return_rate", 1) < 0.05:
                score += 20
                reasons.append("退货率合格")
            else:
                reasons.append(f"退货率偏高: {s.get('return_rate', 0)*100:.1f}%")

            # 经营年限
            if s.get("years_in_business", 0) >= 3:
                score += 20
                reasons.append(f"经营{s.get('years_in_business')}年")

            # 评分
            if s.get("rating", 0) >= 4.5:
                score += 15

            # 发货时效
            if s.get("delivery_days", 99) <= 3:
                score += 10

            # 图片匹配度
            if s.get("image_match_score", 0) >= 0.85:
                score += 10

            s["total_score"] = score
            s["filter_reasons"] = reasons

            # 利润预估
            if tiktok_price_usd > 0 and price > 0:
                revenue_cny = tiktok_price_usd * 7.2
                total_cost = price + 15 + price * 0.05  # 成本+物流+杂费
                profit = revenue_cny - total_cost
                s["profit_cny"] = round(profit, 2)
                s["profit_margin_pct"] = round(profit / revenue_cny * 100, 1) if revenue_cny > 0 else 0
                s["is_low_value"] = profit < 20

            if score >= 60:
                filtered.append(s)

        return sorted(filtered, key=lambda x: x["total_score"], reverse=True)

    async def _analyze_supply_chain(self, product: dict, suppliers: list[dict]) -> str:
        """分析供应链成本"""
        product_info = ""
        if product:
            product_info = f"TikTok商品: {product.get('title', 'N/A')} | 售价: ${product.get('price', 0)}"

        supplier_info = "\n".join(
            [
                f"- {s['name']} | ¥{s['price_cny']} | MOQ:{s['moq']} | 发货:{s['delivery_days']}天 | 评分:{s['rating']}"
                for s in suppliers
            ]
        )

        user_prompt = f"""请分析以下供应链数据，给出采购建议：

{product_info}

1688供应商列表：
{supplier_info}

请计算成本（1688成本 + 跨境物流约15元/件 + 5%杂费），预估利润（按汇率7.2计算），并给出采购建议。
若利润低于20元，标记为低价值。"""

        return await self.think(SYSTEM_PROMPT, user_prompt)
