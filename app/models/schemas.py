from datetime import datetime
from pydantic import BaseModel


class TikTokProduct(BaseModel):
    product_id: str
    title: str
    price: float
    currency: str = "USD"
    sales_count: int = 0
    daily_sales: int = 0
    weekly_sales: int = 0
    likes: int = 0
    comments: int = 0
    shop_name: str = ""
    category: str = ""
    product_url: str = ""
    image_url: str = ""
    country: str = "US"
    growth_rate: float = 0.0
    collected_at: datetime = None

    def model_post_init(self, __context):
        if self.collected_at is None:
            self.collected_at = datetime.now()


class ProductAnalysis(BaseModel):
    product: TikTokProduct
    sku_structure: str = ""
    price_analysis: str = ""
    promotion_strategy: str = ""
    seo_keywords: list[str] = []
    pain_points: str = ""
    recommendation_score: float = 0.0
    summary: str = ""


class SearchRequest(BaseModel):
    keyword: str
    category: str = ""
    country: str = ""
    min_sales: int = 0
    days: int = 7
    limit: int = 20


class AnalyzeRequest(BaseModel):
    keyword: str
    category: str = ""
    country: str = ""
    limit: int = 10


class RankingRequest(BaseModel):
    country: str = "US"
    rank_type: str = "sales"  # sales / growth
    time_range: str = "daily"  # daily / weekly / monthly
    category: str = ""
    limit: int = 20


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    country: str = ""
    scene: str = "auto"
    attachment_name: str = ""


class ContentDetailRequest(BaseModel):
    product: dict
    country: str = "US"
    language: str = "en"


class ContentImageRequest(BaseModel):
    product: dict
    style: str = "modern"
    prompt: str = ""


class ImageSearchRequest(BaseModel):
    image_data: str = ""  # base64
    image_url: str = ""
    limit: int = 10


class StoreBinding(BaseModel):
    platform: str = "tiktok"
    store_name: str = ""
    store_id: str = ""
    store_url: str = ""
    access_token: str = ""
    country: str = "US"


class ContentProviderConfig(BaseModel):
    image_provider: str = "picset-seed"
    image_model: str = "Seed 2.0"
    image_prompt: str = ""
    aspect_ratio: str = "4:5"
    generate_count: int = 1


class CommerceOrderRequest(BaseModel):
    order_id: str = ""
    product_title: str = ""
    product_id: str = ""
    quantity: int = 1
    unit_price: float = 0
    customer_name: str = ""
    customer_email: str = ""
    customer_phone: str = ""
    shipping_address: str = ""
    store_binding_id: int | None = None
    supplier_id: str = ""
    supplier_name: str = ""
    payment_channel: str = ""
    notes: str = ""


class OrderStageUpdateRequest(BaseModel):
    status: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    payment_channel: str = ""
    notes: str = ""


class CommercePaymentRequest(BaseModel):
    order_id: str
    payment_channel: str
    amount: float
    currency: str = "CNY"
    subject: str = "跨境电商订单支付"
    return_url: str = ""
