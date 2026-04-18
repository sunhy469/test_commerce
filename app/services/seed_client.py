"""字节 Seed 模型客户端（当前先作为配置入口与任务描述输出）"""

from config.settings import get_settings


class SeedClient:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.volcano_api_key
        self.base_url = settings.seed_base_url.rstrip("/")
        self.image_model = settings.seed_image_model
        self.video_model = settings.seed_video_model

    async def build_image_job(self, product: dict, prompt: str = "", style: str = "minimal-clean") -> dict:
        return {
            "provider": "byte-seed",
            "model": self.image_model,
            "base_url": self.base_url,
            "enabled": bool(self.api_key),
            "product_title": product.get("title", ""),
            "style": style,
            "prompt": prompt or f"电商商品图，主体突出，适合新平台售卖：{product.get('title', '')}",
        }

    async def build_video_job(self, product: dict, prompt: str = "") -> dict:
        return {
            "provider": "byte-seed",
            "model": self.video_model,
            "base_url": self.base_url,
            "enabled": bool(self.api_key),
            "product_title": product.get("title", ""),
            "prompt": prompt,
        }
