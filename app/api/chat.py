"""AI 对话框 API - 多智能体调度中心"""

import json
import re
import uuid
from fastapi import APIRouter
from app.models.schemas import ChatRequest
from app.services.local_ai import LocalAI
from app.agents.product_monitor import ProductMonitorAgent
from app.agents.supply_chain import SupplyChainAgent
from app.agents.content_gen import ContentGenAgent
from app.agents.auto_purchase import AutoPurchaseAgent
from app.db import store
from app.db.database import get_conn

chat_router = APIRouter(prefix="/api/chat", tags=["AI对话"])

claude = LocalAI()
monitor_agent = ProductMonitorAgent()
supply_agent = SupplyChainAgent()
content_agent = ContentGenAgent()
purchase_agent = AutoPurchaseAgent()

COUNTRY_MAP = {
    "美国": "US", "us": "US", "usa": "US", "美区": "US",
    "英国": "GB", "uk": "GB", "gb": "GB", "英区": "GB",
    "印尼": "ID", "印度尼西亚": "ID", "id": "ID",
    "泰国": "TH", "th": "TH",
    "日本": "JP", "jp": "JP",
    "韩国": "KR", "kr": "KR",
    "越南": "VN", "vn": "VN",
    "马来": "MY", "马来西亚": "MY", "my": "MY",
    "菲律宾": "PH", "ph": "PH",
    "巴西": "BR", "br": "BR",
    "全球": "global", "全部": "",
}

INTENT_SYSTEM = """你是外贸多智能体系统的调度中心。用户会用自然语言描述需求，你需要判断用户意图并返回JSON指令。

可用的动作：
1. search_products - 搜索热销商品（参数: keyword, country, category）
2. analyze_products - 分析选品（参数: keyword, country, category）
3. match_suppliers - 匹配供应商（参数: keyword）
4. generate_detail_page - 生成商品详情页（参数: product_title, price, category, country, style_prompt）
5. generate_image - 生成商品图片（参数: product_title, category, country, style, prompt）
6. create_order - 创建采购订单（参数: product_title, quantity, unit_price）
7. workflow - 多步骤自动化任务（参数: keyword, product_title, country, category, need_ranking, need_supply, need_detail, need_image）
8. general_chat - 普通对话/问答

请返回JSON格式：
{"action": "动作名", "params": {参数}, "reply": "给用户的简短回复"}

只输出JSON，不要其他内容。"""


@chat_router.post("")
async def chat(req: ChatRequest):
    """处理用户对话消息，识别意图并调度Agent"""
    session_id = req.session_id or str(uuid.uuid4())[:8]
    _save_chat(session_id, "user", req.message)

    intent = await _resolve_intent(req.message, req.country, req.scene, req.attachment_name)
    action = intent.get("action", "general_chat")
    params = intent.get("params", {})
    reply = intent.get("reply", "")

    if action == "workflow":
        result_data = await _run_workflow(params)
        reply = reply or _workflow_reply(result_data)
    else:
        result_data, reply = await _run_single_action(action, params, reply)

    _save_chat(session_id, "assistant", reply, action, json.dumps(result_data, ensure_ascii=False, default=str) if result_data else None)
    store.log_activity("chat", f"AI对话: {action}", req.message[:80])

    return {
        "session_id": session_id,
        "reply": reply,
        "action": action,
        "data": result_data,
    }


async def _resolve_intent(message: str, country: str = "", scene: str = "auto", attachment_name: str = "") -> dict:
    heuristic = _heuristic_intent(message, country, scene, attachment_name)
    try:
        intent_text = await claude.analyze(INTENT_SYSTEM, message)
        parsed = json.loads(intent_text)
        if parsed.get("action"):
            parsed.setdefault("params", {})
            for key, value in heuristic.get("params", {}).items():
                parsed["params"].setdefault(key, value)
            if heuristic.get("action") != "general_chat" and parsed.get("action") == "general_chat":
                return heuristic
            if heuristic.get("action") == "workflow" and parsed.get("action") != "workflow":
                return heuristic
            return parsed
    except Exception:
        pass
    return heuristic


def _heuristic_intent(message: str, forced_country: str = "", forced_scene: str = "auto", attachment_name: str = "") -> dict:
    text = message.strip()
    lower = text.lower()
    country = forced_country or _extract_country(lower)
    category = _extract_category(text)
    keyword = _extract_keyword(text)
    product_title = keyword or text

    need_ranking = forced_scene == "ranking" or any(x in text for x in ["热销", "排行榜", "销量榜", "飙升榜", "top", "月榜", "日榜", "周榜", "近7天"])
    need_supply = forced_scene == "supply" or any(x in text for x in ["1688", "供应链", "供应商", "找货", "同款", "图搜"])
    need_detail = forced_scene == "detail" or any(x in text for x in ["详情页", "详情图", "产品详情图"])
    need_image = forced_scene == "image" or any(x in text for x in ["图片", "主图", "海报", "详情图生成", "图像生成"])

    if attachment_name and not keyword:
        keyword = attachment_name.rsplit('.', 1)[0]
        product_title = keyword

    if forced_scene == "auto":
        need_ranking = True if not any([need_ranking, need_supply, need_detail, need_image]) else need_ranking
        need_supply = need_supply or ("供应" in text or "同款" in text)
        need_detail = need_detail or ("详情" in text)
        need_image = need_image or ("图片" in text or "主图" in text)

    if sum([need_ranking, need_supply, need_detail, need_image]) >= 2 or forced_scene == "auto":
        return {
            "action": "workflow",
            "params": {
                "keyword": keyword,
                "product_title": product_title,
                "country": country,
                "category": category,
                "need_ranking": need_ranking,
                "need_supply": need_supply,
                "need_detail": need_detail,
                "need_image": need_image,
                "style_prompt": text,
            },
            "reply": "已识别为多步骤自动化任务，正在联动多个模块处理。",
        }

    if need_detail:
        return {"action": "generate_detail_page", "params": {"product_title": product_title, "country": country, "category": category, "style_prompt": text}, "reply": "正在为您生成商品详情页。"}
    if need_image:
        return {"action": "generate_image", "params": {"product_title": product_title, "country": country, "category": category, "style": "minimal-clean", "prompt": text}, "reply": "正在为您生成商品图片。"}
    if need_supply:
        return {"action": "match_suppliers", "params": {"keyword": keyword or product_title, "country": country, "category": category}, "reply": "正在帮您匹配供应链。"}
    if need_ranking:
        return {"action": "search_products", "params": {"keyword": keyword, "country": country, "category": category}, "reply": "正在帮您查看热销商品与榜单。"}
    return {"action": "general_chat", "params": {"country": country}, "reply": text}


async def _run_single_action(action: str, params: dict, reply: str):
    result_data = None
    if action == "search_products":
        products = await monitor_agent.search(
            keyword=params.get("keyword", ""),
            limit=20,
            country=params.get("country", ""),
            category=params.get("category", ""),
        )
        product_dicts = [p.model_dump() for p in products]
        if params.get("country"):
            product_dicts = [p for p in product_dicts if p.get("country") == params.get("country")] or product_dicts
        if params.get("category"):
            product_dicts = [p for p in product_dicts if params.get("category", "").lower() in p.get("category", "").lower()] or product_dicts
        store.save_products(product_dicts)
        result_data = {"products": product_dicts, "type": "products", "country": params.get("country", ""), "category": params.get("category", "")}
        reply = reply or f"已为您找到{len(product_dicts)}个热销商品。"
    elif action == "analyze_products":
        result = await monitor_agent.run(keyword=params.get("keyword", ""), category=params.get("category", ""), limit=10)
        if result.get("products"):
            store.save_products(result.get("products", []))
        if result.get("analysis"):
            store.save_analysis(params.get("keyword", ""), params.get("category", ""), result.get("analysis", {}), len(result.get("products", [])))
        result_data = {"analysis": result.get("analysis"), "products": result.get("products", []), "type": "analysis"}
        reply = reply or "选品分析已完成。"
    elif action == "match_suppliers":
        result = await supply_agent.run(keyword=params.get("keyword", ""))
        store.save_supplier_match(
            keyword=params.get("keyword", ""),
            product_title=params.get("keyword", ""),
            suppliers=result.get("suppliers", []),
            analysis=result.get("analysis", {}),
        )
        result_data = {"suppliers": result.get("suppliers", []), "analysis": result.get("analysis"), "type": "suppliers"}
        reply = reply or f"已匹配{len(result.get('suppliers', []))}个供应商。"
    elif action == "generate_detail_page":
        product = {"title": params.get("product_title", ""), "price": params.get("price", 9.99), "category": params.get("category", ""), "description": params.get("style_prompt", ""), "_target_country": params.get("country", "US")}
        result = await content_agent.run(product=product, content_type="page")
        store.save_content(
            product_title=product.get("title", ""),
            product_price=product.get("price", 0),
            content_type="detail_page",
            page=result.get("page"),
        )
        result_data = {"page": result.get("page"), "html_page": result.get("html_page"), "type": "detail_page", "product": product}
        reply = reply or "商品详情页已生成。"
    elif action == "generate_image":
        result_data = {"type": "image", "message": "图片任务已创建，可在内容生成模块中继续细化。", "prompt": params.get("prompt", ""), "style": params.get("style", "minimal-clean"), "product_title": params.get("product_title", ""), "country": params.get("country", ""), "category": params.get("category", "")}
        reply = reply or "已为您准备图片生成任务。"
    elif action == "create_order":
        order_data = {"order_id": "", "product_title": params.get("product_title", ""), "quantity": params.get("quantity", 1), "unit_price": params.get("unit_price", 0)}
        result = await purchase_agent.create_order(order_data)
        result_data = {"order": result, "type": "order"}
        reply = reply or f"订单已创建: {result.get('status')}"
    else:
        result_data = {"type": "text", "content": reply or "您好，请告诉我您的目标商品、国家或生成需求。"}
    return result_data, reply


async def _run_workflow(params: dict) -> dict:
    result = {
        "type": "workflow",
        "steps": [],
        "products": [],
        "suppliers": [],
        "page": None,
        "html_page": None,
        "image": None,
        "selected_product": None,
        "country": params.get("country", ""),
        "category": params.get("category", ""),
    }

    chosen_product = {
        "title": params.get("product_title", params.get("keyword", "推荐商品")),
        "price": 9.99,
        "category": params.get("category", ""),
        "country": params.get("country", "US") or "US",
    }

    if params.get("need_ranking"):
        products = await monitor_agent.search(
            keyword=params.get("keyword", ""),
            limit=10,
            country=params.get("country", ""),
            category=params.get("category", ""),
        )
        result["products"] = [p.model_dump() for p in products]
        if params.get("country"):
            result["products"] = [p for p in result["products"] if p.get("country") == params.get("country")] or result["products"]
        if params.get("category"):
            result["products"] = [p for p in result["products"] if params.get("category", "").lower() in p.get("category", "").lower()] or result["products"]
        if result["products"]:
            chosen_product = result["products"][0]
        store.save_products(result["products"])
        result["steps"].append({"module": "ranking", "status": "done", "summary": f"已获取{len(result['products'])}个热销商品"})

    if params.get("need_supply"):
        supply = await supply_agent.run(product=chosen_product, keyword=chosen_product.get("title") or params.get("keyword", ""))
        result["suppliers"] = supply.get("suppliers", [])
        result["supply_analysis"] = supply.get("analysis")
        store.save_supplier_match(
            keyword=params.get("keyword", chosen_product.get("title", "")),
            product_title=chosen_product.get("title", ""),
            suppliers=result["suppliers"],
            analysis=result.get("supply_analysis") or {},
        )
        result["steps"].append({"module": "supply", "status": "done", "summary": f"已匹配{len(result['suppliers'])}个供应商"})

    if params.get("need_detail"):
        detail_product = dict(chosen_product)
        detail_product["description"] = params.get("style_prompt", "")
        detail_product["_target_country"] = params.get("country", chosen_product.get("country", "US"))
        detail = await content_agent.run(product=detail_product, content_type="page")
        result["page"] = detail.get("page")
        result["html_page"] = detail.get("html_page")
        store.save_content(
            product_title=detail_product.get("title", ""),
            product_price=detail_product.get("price", 0),
            content_type="detail_page",
            page=result.get("page"),
        )
        result["steps"].append({"module": "detail", "status": "done", "summary": "已生成商品详情页"})

    if params.get("need_image"):
        result["image"] = {
            "style": "minimal-clean",
            "prompt": params.get("style_prompt", ""),
            "product_title": chosen_product.get("title", ""),
            "country": params.get("country", chosen_product.get("country", "")),
            "category": chosen_product.get("category", ""),
        }
        result["steps"].append({"module": "image", "status": "ready", "summary": "已准备图像生成提示词"})

    result["selected_product"] = chosen_product
    return result


def _workflow_reply(result: dict) -> str:
    parts = []
    if result.get("products"):
        parts.append(f"已找到{len(result['products'])}个热销商品")
    if result.get("suppliers"):
        parts.append(f"匹配到{len(result['suppliers'])}个供应商")
    if result.get("page"):
        parts.append("详情页已生成")
    if result.get("image"):
        parts.append("图片任务已准备")
    return "，".join(parts) if parts else "自动化任务已完成。"


def _extract_country(text: str) -> str:
    for key, value in COUNTRY_MAP.items():
        if key in text:
            return value
    return ""


def _extract_category(text: str) -> str:
    match = re.search(r"(?:品类|类目)[:：]?([\u4e00-\u9fa5A-Za-z0-9_-]{2,20})", text)
    return match.group(1) if match else ""


def _extract_keyword(text: str) -> str:
    patterns = [
        r"热销的(.+?)(?:，|。|并|再|然后|$)",
        r"找(.+?)(?:的同款|供应链|货源|，|。|并|再|然后|$)",
        r"生成这个产品的(.+?)(?:详情页|图片)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match and match.group(1).strip():
            return match.group(1).strip()
    cleaned = re.sub(r"请帮我|帮我|查看|生成|自动|匹配|热销|商品|详情页|图片|图搜|1688", "", text)
    cleaned = re.sub(r"[，。,.；;：:（）()\s]+", " ", cleaned).strip()
    return cleaned[:40]


@chat_router.get("/history")
async def get_chat_history(session_id: str = "", limit: int = 50):
    """获取对话历史"""
    with get_conn() as conn:
        if session_id:
            rows = conn.execute("SELECT * FROM chat_history WHERE session_id=? ORDER BY created_at ASC LIMIT ?", (session_id, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM chat_history ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return {"messages": [dict(r) for r in rows]}


def _save_chat(session_id: str, role: str, content: str, action_type: str = None, action_result: str = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_history (session_id, role, content, action_type, action_result) VALUES (?,?,?,?,?)",
            (session_id, role, content, action_type, action_result),
        )
