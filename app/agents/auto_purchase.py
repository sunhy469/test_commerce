"""自动采购智能体 - 商务流程编排"""

from datetime import datetime
from app.agents.base import BaseAgent
from app.db.database import get_conn


class AutoPurchaseAgent(BaseAgent):
    """自动采购智能体

    强化后的业务流程：
    1. 创建草稿订单
    2. 选择店铺 / 绑定店铺
    3. 确认供应商
    4. 确认支付通道
    5. 创建支付单
    6. 支付完成后进入履约/采购
    """

    def __init__(self):
        super().__init__()

    async def create_order(self, order_data: dict) -> dict:
        order_id = order_data.get("order_id") or f"TT{datetime.now().strftime('%Y%m%d%H%M%S')}"
        quantity = order_data.get("quantity", 1)
        unit_price = order_data.get("unit_price", 0)
        total_usd = quantity * unit_price
        status = "draft"
        workflow_stage = "draft"
        purchase_status = "awaiting_supplier"

        with get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO orders
                (tiktok_order_id, product_title, product_id, quantity, unit_price_usd, total_usd,
                 customer_name, customer_email, customer_phone, shipping_address, status,
                 workflow_stage, store_binding_id, supplier_id, matched_supplier, matched_1688_id,
                 purchase_price_cny, purchase_status, payment_channel, payment_status, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    order_id,
                    order_data.get("product_title", ""),
                    order_data.get("product_id", ""),
                    quantity,
                    unit_price,
                    total_usd,
                    order_data.get("customer_name", ""),
                    order_data.get("customer_email", ""),
                    order_data.get("customer_phone", ""),
                    order_data.get("shipping_address", ""),
                    status,
                    workflow_stage,
                    order_data.get("store_binding_id"),
                    order_data.get("supplier_id", ""),
                    order_data.get("supplier_name", ""),
                    "",
                    0,
                    purchase_status,
                    order_data.get("payment_channel", ""),
                    "unpaid",
                    order_data.get("notes", ""),
                    datetime.now().isoformat(),
                ),
            )

        sku_match = self._find_sku_mapping(order_data.get("product_id", "")) if order_data.get("product_id") else None
        if sku_match:
            await self.update_order_stage(
                order_id,
                status="supplier_confirmed",
                supplier_id=sku_match.get("alibaba_product_id", ""),
                supplier_name=sku_match.get("supplier_name", ""),
                notes="已自动匹配 SKU 映射，可进入支付确认。",
            )

        return await self.get_order_detail(order_id)

    async def update_order_stage(self, order_id: str, status: str, supplier_id: str = "", supplier_name: str = "", payment_channel: str = "", notes: str = "") -> dict:
        stage_map = {
            "draft": ("draft", "draft", "awaiting_supplier"),
            "store_confirmed": ("pending_confirmation", "store_confirmed", "awaiting_supplier"),
            "supplier_confirmed": ("pending_payment", "supplier_confirmed", "ready_to_order"),
            "payment_pending": ("pending_payment", "payment_pending", "payment_initiated"),
            "paid": ("paid", "paid", "ready_for_fulfillment"),
            "fulfilling": ("fulfilling", "fulfilling", "ordered"),
            "completed": ("completed", "completed", "completed"),
            "cancelled": ("cancelled", "cancelled", "cancelled"),
        }
        status_value, workflow_stage, purchase_status = stage_map.get(status, (status, status, status))
        with get_conn() as conn:
            current = conn.execute("SELECT * FROM orders WHERE tiktok_order_id=?", (order_id,)).fetchone()
            if not current:
                return {"status": "not_found", "message": f"订单不存在: {order_id}"}
            conn.execute(
                """UPDATE orders SET status=?, workflow_stage=?, purchase_status=?, supplier_id=COALESCE(NULLIF(?, ''), supplier_id),
                matched_supplier=COALESCE(NULLIF(?, ''), matched_supplier), payment_channel=COALESCE(NULLIF(?, ''), payment_channel),
                notes=CASE WHEN ? != '' THEN ? ELSE notes END, updated_at=? WHERE tiktok_order_id=?""",
                (
                    status_value,
                    workflow_stage,
                    purchase_status,
                    supplier_id,
                    supplier_name,
                    payment_channel,
                    notes,
                    notes,
                    datetime.now().isoformat(),
                    order_id,
                ),
            )
            if status == "paid":
                conn.execute(
                    "UPDATE orders SET payment_status='paid', updated_at=? WHERE tiktok_order_id=?",
                    (datetime.now().isoformat(), order_id),
                )
        return await self.get_order_detail(order_id)

    async def get_order_detail(self, order_id: str) -> dict:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM orders WHERE tiktok_order_id=?", (order_id,)).fetchone()
            if not row:
                return {"status": "not_found", "message": f"订单不存在: {order_id}"}
            order = dict(row)

        order["stage_tips"] = self._build_stage_tips(order)
        order["available_actions"] = self._build_available_actions(order)
        order["profit_estimate_cny"] = self._estimate_profit(order)
        return {"status": "ok", "order": order}

    def _build_stage_tips(self, order: dict) -> list[dict]:
        return [
            {"key": "draft", "label": "填写订单信息", "done": order.get("workflow_stage") not in ("draft",)},
            {"key": "store_confirmed", "label": "确认店铺绑定", "done": order.get("workflow_stage") in ("store_confirmed", "supplier_confirmed", "payment_pending", "paid", "fulfilling", "completed")},
            {"key": "supplier_confirmed", "label": "确认供应商", "done": order.get("workflow_stage") in ("supplier_confirmed", "payment_pending", "paid", "fulfilling", "completed")},
            {"key": "payment_pending", "label": "选择支付方式并发起支付", "done": order.get("workflow_stage") in ("payment_pending", "paid", "fulfilling", "completed")},
            {"key": "paid", "label": "支付完成", "done": order.get("workflow_stage") in ("paid", "fulfilling", "completed")},
            {"key": "fulfilling", "label": "采购/履约", "done": order.get("workflow_stage") in ("fulfilling", "completed")},
        ]

    def _build_available_actions(self, order: dict) -> list[str]:
        stage = order.get("workflow_stage", "draft")
        mapping = {
            "draft": ["confirm_store", "cancel_order"],
            "store_confirmed": ["confirm_supplier", "cancel_order"],
            "supplier_confirmed": ["choose_payment", "cancel_order"],
            "payment_pending": ["pay_now", "mark_paid", "cancel_order"],
            "paid": ["start_fulfillment"],
            "fulfilling": ["complete_order"],
        }
        return mapping.get(stage, [])

    def _estimate_profit(self, order: dict) -> float:
        revenue_cny = (order.get("total_usd") or 0) * 7.2
        cost_cny = (order.get("purchase_price_cny") or 0) + 15
        if revenue_cny <= 0:
            return 0
        return round(revenue_cny - cost_cny - cost_cny * 0.05, 2)

    def _find_sku_mapping(self, tiktok_product_id: str) -> dict | None:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM sku_mappings WHERE tiktok_product_id=? AND is_active=1",
                (tiktok_product_id,),
            ).fetchone()
            return dict(row) if row else None

    async def create_sku_mapping(self, mapping: dict) -> dict:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO sku_mappings
                (tiktok_product_id, tiktok_sku, alibaba_product_id, alibaba_sku,
                 supplier_name, price_cny, moq)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    mapping.get("tiktok_product_id", ""),
                    mapping.get("tiktok_sku", ""),
                    mapping.get("alibaba_product_id", ""),
                    mapping.get("alibaba_sku", ""),
                    mapping.get("supplier_name", ""),
                    mapping.get("price_cny", 0),
                    mapping.get("moq", 1),
                ),
            )
        return {"status": "ok", "message": "SKU映射已创建"}

    async def get_sku_mappings(self) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sku_mappings WHERE is_active=1 ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    async def sync_inventory(self) -> dict:
        mappings = await self.get_sku_mappings()
        results = []
        for m in mappings:
            current_stock = 500
            current_price = m.get("price_cny", 15)
            action = "no_change"
            if current_stock == 0:
                action = "delist_tiktok"
            elif current_stock < 10:
                action = "low_stock_alert"
            elif abs(current_price - m.get("price_cny", 0)) > 2:
                action = "price_changed_alert"

            with get_conn() as conn:
                conn.execute(
                    """INSERT INTO inventory_sync
                    (tiktok_product_id, alibaba_product_id, stock_1688, price_1688_cny,
                     previous_stock, previous_price, action_taken)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        m.get("tiktok_product_id", ""),
                        m.get("alibaba_product_id", ""),
                        current_stock,
                        current_price,
                        m.get("last_stock", 0),
                        m.get("price_cny", 0),
                        action,
                    ),
                )
            results.append({
                "tiktok_product_id": m.get("tiktok_product_id"),
                "stock": current_stock,
                "price_cny": current_price,
                "action": action,
            })

        return {
            "synced_count": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "delisted": sum(1 for r in results if r["action"] == "delist_tiktok"),
            "alerts": sum(1 for r in results if "alert" in r["action"]),
        }

    async def get_orders(self, status: str = "", limit: int = 50) -> list[dict]:
        with get_conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE status=? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    async def get_sync_history(self, limit: int = 20) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM inventory_sync ORDER BY synced_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    async def run(self, order: dict = None, **kwargs) -> dict:
        if order:
            return await self.create_order(order)
        return {
            "status": "ready",
            "features": {
                "order_create": "POST /api/purchase/orders",
                "order_stage_update": "POST /api/purchase/orders/{order_id}/stage",
                "order_detail": "GET /api/purchase/orders/{order_id}",
                "sku_mapping": "POST /api/purchase/sku-mappings",
                "inventory_sync": "POST /api/purchase/sync-inventory",
                "order_list": "GET /api/purchase/orders",
            },
        }
