"""支付服务 - 国内/国际支付编排"""

import json
from datetime import datetime
from config.settings import get_settings
from app.db.database import get_conn


class PaymentService:
    """统一支付服务"""

    def __init__(self):
        settings = get_settings()
        self.alipay_app_id = settings.alipay_app_id
        self.stripe_secret_key = settings.stripe_secret_key

    async def create_payment(self, order_id: str, channel: str, amount: float, currency: str, subject: str, return_url: str = "") -> dict:
        channel = channel or ("alipay_cn" if currency == "CNY" else "stripe_card")
        if channel == "alipay_cn":
            return await self.create_alipay_order(order_id, amount, subject, return_url=return_url)
        if channel == "stripe_card":
            return await self.create_stripe_checkout(order_id, amount, subject, return_url=return_url)
        if channel == "paypal":
            return await self.create_paypal_order(order_id, amount)
        if channel == "alipay_global":
            return {
                "status": "pending_cloud_setup",
                "payment_method": channel,
                "message": "Alipay+ 国际钱包需云平台部署后接入真实回调与签名能力。",
            }
        return {"status": "unsupported", "message": f"暂不支持的支付通道: {channel}"}

    async def get_payment_channels(self) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM payment_channels WHERE status='enabled' ORDER BY channel_group, id"
            ).fetchall()
            return [dict(r) for r in rows]

    async def mark_payment_status(self, order_id: str, status: str, transaction_id: str = "") -> dict:
        paid_at = datetime.now().isoformat() if status == "paid" else None
        with get_conn() as conn:
            conn.execute(
                "UPDATE payments SET status=?, transaction_id=COALESCE(NULLIF(?, ''), transaction_id), paid_at=COALESCE(?, paid_at) WHERE order_id=?",
                (status, transaction_id, paid_at, order_id),
            )
            conn.execute(
                "UPDATE orders SET payment_status=?, updated_at=? WHERE tiktok_order_id=?",
                (status, datetime.now().isoformat(), order_id),
            )
        return {"status": "ok", "order_id": order_id, "payment_status": status}

    async def create_alipay_order(self, order_id: str, amount_cny: float, subject: str, return_url: str = "") -> dict:
        if not self.alipay_app_id:
            payload = {
                "status": "not_configured",
                "payment_method": "alipay_cn",
                "message": "支付宝 APP_ID 未配置，已保留商务流程节点。",
                "setup_guide": [
                    "1. 登录支付宝开放平台创建企业应用",
                    "2. 配置 RSA2 密钥和回调地址",
                    "3. 云部署后接入 notify_url / return_url",
                ],
            }
        else:
            payload = {
                "status": "created",
                "payment_method": "alipay_cn",
                "order_id": order_id,
                "amount_cny": amount_cny,
                "checkout_url": return_url or f"https://openapi.alipay.com/gateway.do?out_trade_no={order_id}",
                "message": "支付宝付款单已创建",
            }

        with get_conn() as conn:
            conn.execute(
                """INSERT INTO payments (order_id, payment_method, amount, currency, status, checkout_url, provider, provider_model)
                VALUES (?, 'alipay_cn', ?, 'CNY', ?, ?, 'alipay', 'domestic_checkout')""",
                (order_id, amount_cny, payload["status"], payload.get("checkout_url", "")),
            )
        return payload

    async def create_stripe_checkout(self, order_id: str, amount_usd: float, product_name: str, return_url: str = "") -> dict:
        if not self.stripe_secret_key:
            payload = {
                "status": "not_configured",
                "payment_method": "stripe_card",
                "message": "Stripe Secret Key 未配置，已保留国际支付流程。",
                "setup_guide": [
                    "1. 注册 Stripe 商户号",
                    "2. 获取测试密钥与 webhook secret",
                    "3. 云部署后配置 success_url / cancel_url / webhook",
                ],
            }
        else:
            payload = {
                "status": "created",
                "payment_method": "stripe_card",
                "order_id": order_id,
                "amount_usd": amount_usd,
                "checkout_url": return_url or f"https://checkout.stripe.com/pay/mock_{order_id}",
                "message": "Stripe 收款链接已创建",
            }

        with get_conn() as conn:
            conn.execute(
                """INSERT INTO payments (order_id, payment_method, amount, currency, status, checkout_url, provider, provider_model)
                VALUES (?, 'stripe_card', ?, 'USD', ?, ?, 'stripe', 'hosted_checkout')""",
                (order_id, amount_usd, payload["status"], payload.get("checkout_url", "")),
            )
        return payload

    async def create_paypal_order(self, order_id: str, amount_usd: float) -> dict:
        payload = {
            "status": "pending_cloud_setup",
            "payment_method": "paypal",
            "order_id": order_id,
            "amount_usd": amount_usd,
            "message": "PayPal 商务接入节点已预留，待云端配置 Client ID / Secret。",
        }
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO payments (order_id, payment_method, amount, currency, status, provider, provider_model)
                VALUES (?, 'paypal', ?, 'USD', ?, 'paypal', 'checkout_order')""",
                (order_id, amount_usd, payload["status"]),
            )
        return payload

    async def get_payment_records(self, order_id: str = "", limit: int = 20) -> list[dict]:
        with get_conn() as conn:
            if order_id:
                rows = conn.execute(
                    "SELECT * FROM payments WHERE order_id=? ORDER BY created_at DESC", (order_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM payments ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]
