# TradeAgent Studio

一个基于 **FastAPI + SQLite + 原生前端** 的跨境电商智能工作台，覆盖：
- 热销商品监控与区域排行榜
- 供应链匹配（关键词/以图搜货）
- 商品详情页与图片任务生成
- 订单与支付流程管理
- 会话聊天与本地会话管理

---

## 目录结构

```text
app/                  # 后端 FastAPI 代码
  api/                # 各业务路由（chat/monitor/supply/content/purchase...）
  db/                 # SQLite 连接与数据读写
  agents/             # 业务智能体实现
frontend/
  templates/          # 前端页面模板（index.html）
  static/js/          # 前端逻辑（app.js）
sql/init_schema.sql   # 数据库初始化脚本
```

---

## 环境要求

- Python 3.10+
- pip

---

## 快速启动

```bash
# 1) 安装依赖
pip install -r requirements.txt

# 2) 启动服务（默认 8000）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问：
- 页面：`http://127.0.0.1:8000/`
- 健康检查：`http://127.0.0.1:8000/health`

---

## 关键功能说明

### 1) 排行榜数据源

`POST /api/monitor/ranking`

- 对东南亚国家（`ID/TH/VN/MY/PH/SG`）会优先读取分表（如 `products_id`）。
- 若分表不可用/无数据，会回退到主表 `products`。

### 2) 聊天会话删除

`DELETE /api/chat/history/{session_id}`

- 删除指定 `session_id` 的后端聊天记录。
- 前端删除会话时会同步调用该接口（若本地会话已绑定后端 session）。

### 3) 启动同步策略

当前版本已关闭启动时 EchoTik 自动同步任务，避免本地/测试环境启动即产生大量外部请求。

---

## 常用开发命令

```bash
# 语法检查（后端）
python -m compileall app

# 运行测试（如果你已配置测试数据）
pytest
```

---

## 注意事项

1. 本项目默认使用 SQLite，数据库文件位于 `data/` 目录。
2. 若你在调试聊天历史删除，请同时检查：
   - 浏览器本地存储 `ta_chat_sessions`
   - 后端 `chat_history` 表中的 session 数据
3. 前端控制台页面当前采用“数字指标卡”展示，不绘制趋势折线图。

---

## License

仅用于学习与内部演示。
