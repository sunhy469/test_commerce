from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # TikTok
    tiktok_email: str = ""
    tiktok_password: str = ""
    tiktok_session_cookie: str = ""
    tiktok_user_agent: str = ""
    tiktok_referer: str = "https://www.tiktok.com/"
    scraper_proxy: str = ""

    # 1688
    alibaba_account: str = ""
    alibaba_password: str = ""

    # 1688 开放平台 API
    alibaba_app_key: str = ""
    alibaba_app_secret: str = ""

    # TikTok Shop API
    tiktok_api_token: str = ""

    # API Keys / Model Providers
    echotik_username: str = "260413847753057272"
    echotik_password: str = "7cfe6ddae8134f2c9ff48d521d68c411"
    echotik_base_url: str = "https://open.echotik.live/api/v3"
    volcano_api_key: str = ""
    seed_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    seed_image_model: str = "Seed-2.0"
    seed_video_model: str = "Seedance-2.0"

    # 支付 - 支付宝
    alipay_app_id: str = ""
    alipay_private_key: str = ""

    # 支付 - Stripe
    stripe_secret_key: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
