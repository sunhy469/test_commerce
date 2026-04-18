"""本地规则引擎：替代 Claude 的文本分析与结构化输出"""

import json


class LocalAI:
    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        text = user_prompt or ""
        lower = text.lower()

        if "json指令" in system_prompt or "调度中心" in system_prompt:
            return json.dumps({
                "action": "general_chat",
                "params": {},
                "reply": text,
            }, ensure_ascii=False)

        if "供应链" in system_prompt or "供应商筛选" in system_prompt or "采购建议" in text:
            return json.dumps({
                "suppliers": [
                    {"name": "义乌优选工厂", "price_range": "¥8-15", "moq": 50, "delivery_days": 3, "score": 92},
                    {"name": "广州跨境货盘", "price_range": "¥10-18", "moq": 100, "delivery_days": 2, "score": 88}
                ],
                "cost_analysis": "建议按货值、物流与平台佣金联合核算，优先选择支持小批量试单的供应商。",
                "profit_estimate": "建议保留至少 25%-40% 毛利空间后再上架。",
                "risk_assessment": "重点检查发货时效、退货率、侵权风险与图片版权。",
                "recommendation": "先小单测试，再放量采购。"
            }, ensure_ascii=False)

        if "商品页面" in system_prompt or "页面设计师" in system_prompt or "page" in lower:
            title = "Viral Product for New Store Launch"
            return json.dumps({
                "page_title": title,
                "description": "A clean and conversion-focused product page tailored for cross-border ecommerce stores.",
                "bullet_points": [
                    "High-conversion product layout",
                    "Clear selling points for new store launch",
                    "Suitable for mobile-first ecommerce shoppers",
                    "Easy to localize for different markets",
                    "Designed for image-led product selling"
                ],
                "seo_tags": ["viral product", "ecommerce", "new store", "product image", "cross border"],
                "price_suggestion": "建议使用首单优惠与多件折扣组合提高转化。",
                "review_templates": [
                    "Looks exactly like the product page I wanted for my shop.",
                    "Clean layout and easy to convert.",
                    "Perfect for testing on a new ecommerce platform."
                ],
                "pain_points": "Low trust, weak visual hierarchy, and unclear benefits are the biggest blockers for conversion.",
                "landing_page_sections": [
                    {"title": "Core Benefits", "content": "Explain why this product deserves attention."},
                    {"title": "Usage Scenes", "content": "Show where and how customers use the product."},
                    {"title": "Trust Section", "content": "Add reviews, FAQs and shipping reassurance."}
                ]
            }, ensure_ascii=False)

        if "选品分析师" in system_prompt or "选品建议" in text:
            return json.dumps({
                "sku_structure": "建议以单品为主，搭配 2 件装或颜色变体测试。",
                "price_analysis": "建议优先测试中低客单价区间，利于新平台冷启动。",
                "promotion_strategy": "首单折扣 + 多件优惠更适合新店铺起量。",
                "seo_keywords": ["viral", "trending", "must have", "shop", "new launch"],
                "pain_points": "消费者更在意发货时效、图片质感与真实评价。",
                "recommendation_score": 8.1,
                "summary": "适合用于新平台上新测试，优先验证点击率与转化率。"
            }, ensure_ascii=False)

        return json.dumps({"text": text}, ensure_ascii=False)
