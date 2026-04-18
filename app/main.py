"""外贸多智能体系统 - FastAPI 入口"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import monitor_router, supply_router, content_router, purchase_router, payment_router, history_router, user_router
from app.api.dashboard import dashboard_router
from app.api.scraper import scraper_router
from app.api.chat import chat_router


# 定时任务：每6小时同步库存
async def schedule_inventory_sync():
    """后台库存同步定时任务"""
    import asyncio
    from app.agents.auto_purchase import AutoPurchaseAgent
    agent = AutoPurchaseAgent()
    while True:
        await asyncio.sleep(6 * 3600)  # 每6小时
        try:
            result = await agent.sync_inventory()
            print(f"[定时任务] 库存同步完成: 同步{result['synced_count']}个商品, 下架{result['delisted']}个")
        except Exception as e:
            print(f"[定时任务] 库存同步失败: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理"""
    import asyncio
    # 启动定时任务
    task = asyncio.create_task(schedule_inventory_sync())
    print("[系统] 库存同步定时任务已启动（每6小时执行）")
    yield
    # 关闭定时任务
    task.cancel()


app = FastAPI(
    title="外贸多智能体系统",
    description="基于 TikTok + 1688 的外贸自动化选品、供应链匹配、内容生成与采购系统",
    version="0.1.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(monitor_router)
app.include_router(supply_router)
app.include_router(content_router)
app.include_router(purchase_router)
app.include_router(payment_router)
app.include_router(history_router)
app.include_router(dashboard_router)
app.include_router(scraper_router)
app.include_router(chat_router)
app.include_router(user_router)

# 静态文件
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# 生成的落地页和处理后的图片
os.makedirs("data/pages", exist_ok=True)
os.makedirs("data/images", exist_ok=True)
app.mount("/pages", StaticFiles(directory="data/pages"), name="pages")
app.mount("/images", StaticFiles(directory="data/images"), name="images")


@app.get("/")
async def index():
    return FileResponse("frontend/templates/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
