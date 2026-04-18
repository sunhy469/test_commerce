"""往数据库插入演示数据，让前端页面有实际内容展示"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import get_conn
import json
from datetime import datetime, timedelta

def seed():
    with get_conn() as conn:
        # 清理旧数据（可选）
        for t in ['products','product_analyses','supplier_matches','content_records',
                   'activity_log','favorites','orders','sku_mappings','inventory_sync','payments',
                   'chat_history','store_bindings']:
            conn.execute(f"DELETE FROM {t}")

    # ========== 1. 商品数据 ==========
    products = [
        {"product_id":"TT10001","title":"Glow Skin Serum - Vitamin C Brightening","price":14.99,"currency":"USD","sales_count":12500,"daily_sales":420,"weekly_sales":2800,"video_views":890000,"likes":45000,"comments":3200,"shop_name":"GlowBeautyUS","category":"Beauty & Personal Care","product_url":"","image_url":"https://picsum.photos/seed/serum01/200/200","country":"US","growth_rate":0.35},
        {"product_id":"TT10002","title":"Portable Blender USB Rechargeable 380ml","price":19.99,"currency":"USD","sales_count":8700,"daily_sales":290,"weekly_sales":1950,"video_views":620000,"likes":31000,"comments":2100,"shop_name":"KitchenGadgetPro","category":"Home & Garden","product_url":"","image_url":"https://picsum.photos/seed/blender02/200/200","country":"US","growth_rate":0.18},
        {"product_id":"TT10003","title":"LED Strip Lights RGB 5M Smart WiFi","price":9.99,"currency":"USD","sales_count":15200,"daily_sales":580,"weekly_sales":3900,"video_views":1200000,"likes":67000,"comments":4500,"shop_name":"SmartHomeLED","category":"Electronics","product_url":"","image_url":"https://picsum.photos/seed/led03/200/200","country":"GB","growth_rate":0.42},
        {"product_id":"TT10004","title":"Cloud Slides Pillow Slippers Unisex","price":12.99,"currency":"USD","sales_count":22000,"daily_sales":850,"weekly_sales":5600,"video_views":1800000,"likes":95000,"comments":6800,"shop_name":"ComfyWearShop","category":"Fashion","product_url":"","image_url":"https://picsum.photos/seed/slides04/200/200","country":"US","growth_rate":0.55},
        {"product_id":"TT10005","title":"Matcha Whisk Set Bamboo Traditional","price":8.99,"currency":"USD","sales_count":5600,"daily_sales":180,"weekly_sales":1100,"video_views":340000,"likes":18000,"comments":1200,"shop_name":"TeaCultureCo","category":"Food & Beverages","product_url":"","image_url":"https://picsum.photos/seed/matcha05/200/200","country":"JP","growth_rate":0.12},
        {"product_id":"TT10006","title":"Wireless Earbuds Pro ANC Bluetooth 5.3","price":24.99,"currency":"USD","sales_count":9800,"daily_sales":350,"weekly_sales":2300,"video_views":750000,"likes":42000,"comments":3100,"shop_name":"AudioTechDirect","category":"Electronics","product_url":"","image_url":"https://picsum.photos/seed/earbuds06/200/200","country":"ID","growth_rate":0.28},
        {"product_id":"TT10007","title":"Aesthetic Room Decor Moon Lamp 3D Print","price":16.99,"currency":"USD","sales_count":7300,"daily_sales":240,"weekly_sales":1600,"video_views":520000,"likes":28000,"comments":1900,"shop_name":"DreamDecorShop","category":"Home & Garden","product_url":"","image_url":"https://picsum.photos/seed/lamp07/200/200","country":"TH","growth_rate":0.22},
        {"product_id":"TT10008","title":"Hair Oil Rosemary Growth Serum 60ml","price":11.99,"currency":"USD","sales_count":18000,"daily_sales":720,"weekly_sales":4800,"video_views":1400000,"likes":78000,"comments":5200,"shop_name":"NaturalHairLab","category":"Beauty & Personal Care","product_url":"","image_url":"https://picsum.photos/seed/hairoil08/200/200","country":"US","growth_rate":0.48},
    ]
    from app.db.store import save_products
    save_products(products)

    # ========== 2. 选品分析记录 ==========
    analyses = [
        {"keyword":"beauty serum","category":"Beauty & Personal Care","analysis":{
            "sku_structure":"多规格组合：30ml基础款、60ml进阶款、套装（精华+面霜），价格带$9.99-$24.99",
            "price_analysis":"主力价格带$12-$18，高于$20需要品牌背书。建议定价$14.99，Buy 2 Get 10% Off",
            "promotion_strategy":"Buy 2 Get 1 Free效果最佳，配合限时折扣+免运费门槛$25",
            "seo_keywords":["vitamin c serum","brightening serum","glow skin","anti aging serum","face serum"],
            "pain_points":"用户主要抱怨：包装漏液(23%)、效果慢(18%)、味道刺鼻(12%)。需加强密封包装和使用说明",
            "recommendation_score":8.5,
            "summary":"美妆精华赛道竞争激烈但需求旺盛，Vitamin C精华是长青品类。建议选择工厂直供、注重包装质量，定价$14.99有较好利润空间。"
        },"product_count":15},
        {"keyword":"led strip lights","category":"Electronics","analysis":{
            "sku_structure":"按长度分：5M/10M/20M，按功能分：基础RGB/智能WiFi/音乐同步",
            "price_analysis":"5M基础款$6-$10，WiFi智能款$9-$15。建议主推WiFi款$9.99",
            "promotion_strategy":"套装优惠（灯带+遥控器+延长线），满$15免运费",
            "seo_keywords":["led strip lights","room decor lights","rgb lights","smart led","tiktok lights"],
            "pain_points":"常见差评：粘性不够(30%)、APP连接困难(22%)、色差(15%)。选供应商注意胶带质量",
            "recommendation_score":7.8,
            "summary":"LED灯带是TikTok常青爆品，Room Tour和Aesthetic视频持续带货。WiFi智能款利润更高，建议主推。"
        },"product_count":12},
    ]
    with get_conn() as conn:
        for a in analyses:
            conn.execute(
                "INSERT INTO product_analyses (keyword, category, analysis_json, product_count, recommendation_score) VALUES (?,?,?,?,?)",
                (a["keyword"], a["category"], json.dumps(a["analysis"], ensure_ascii=False), a["product_count"], a["analysis"]["recommendation_score"])
            )

    # ========== 3. 供应商匹配记录 ==========
    supplier_records = [
        {"keyword":"vitamin c serum","product_title":"Glow Skin Serum - Vitamin C Brightening","suppliers":[
            {"name":"义乌美妆工厂直营店","price_cny":12.5,"moq":100,"delivery_days":3,"rating":4.8,"location":"浙江义乌","total_score":88},
            {"name":"广州白云化妆品批发","price_cny":10.0,"moq":200,"delivery_days":2,"rating":4.6,"location":"广东广州","total_score":82},
            {"name":"上海国际美妆供应链","price_cny":15.0,"moq":50,"delivery_days":4,"rating":4.9,"location":"上海","total_score":79},
        ],"analysis":{"cost_analysis":"1688成本¥10-15 + 物流¥15 + 杂费¥1.5 = 总成本¥26.5-31.5","profit_estimate":"TikTok售价$14.99 x 7.2 = ¥107.9，利润¥76.4-81.4，利润率70%+","risk_assessment":"美妆类需注意FDA合规，建议选有出口资质的供应商","recommendation":"推荐义乌美妆工厂直营店，价格适中、品质稳定、有出口经验"}},
        {"keyword":"cloud slides","product_title":"Cloud Slides Pillow Slippers Unisex","suppliers":[
            {"name":"福建晋江鞋业工厂","price_cny":8.0,"moq":50,"delivery_days":2,"rating":4.7,"location":"福建晋江","total_score":91},
            {"name":"温州鞋都批发中心","price_cny":9.5,"moq":30,"delivery_days":3,"rating":4.5,"location":"浙江温州","total_score":85},
        ],"analysis":{"cost_analysis":"1688成本¥8-9.5 + 物流¥15 + 杂费¥1.2 = 总成本¥24.2-25.7","profit_estimate":"TikTok售价$12.99 x 7.2 = ¥93.5，利润¥67.8-69.3，利润率72%+","risk_assessment":"鞋类注意尺码标准转换(CN->US/EU)，需提供对照表","recommendation":"推荐福建晋江鞋业工厂，产业带优势明显，价格最低"}},
    ]
    with get_conn() as conn:
        for s in supplier_records:
            conn.execute(
                "INSERT INTO supplier_matches (keyword, product_title, suppliers_json, analysis_json, supplier_count, best_supplier, best_price) VALUES (?,?,?,?,?,?,?)",
                (s["keyword"], s["product_title"], json.dumps(s["suppliers"], ensure_ascii=False), json.dumps(s["analysis"], ensure_ascii=False),
                 len(s["suppliers"]), s["suppliers"][0]["name"], s["suppliers"][0]["price_cny"])
            )

    # ========== 4. 内容生成记录 ==========
    content_records = [
        {"product_title":"Cloud Slides Pillow Slippers Unisex","product_price":12.99,"content_type":"all",
         "page":{"page_title":"Walk on Clouds - Ultra Soft Pillow Slides for All-Day Comfort","description":"Experience next-level comfort with our Cloud Slides. Made with thick EVA foam that cushions every step. Perfect for home, beach, or quick errands. Your feet will thank you!","bullet_points":["Ultra-thick 4.5cm EVA sole - like walking on marshmallows","Non-slip textured bottom for indoor & outdoor use","Quick-dry open-toe design - perfect for pool & shower","Unisex sizing with 8 color options to match any vibe","Lightweight at only 200g - pack them anywhere"],"seo_tags":["cloud slides","pillow slippers","comfort slides","EVA sandals","summer slides"],"price_suggestion":"$12.99 base, Buy 2 for $22.99 (save 12%). Free shipping over $25","review_templates":["OMG these are SO comfy! I bought one pair and came back for 3 more colors. My whole family wears them now 😍","Best slides I've ever owned. I wear them to the grocery store, around the house, everywhere. Worth every penny!","Was skeptical but these actually feel like walking on clouds. The arch support is surprisingly good for the price."],"landing_page_sections":[{"title":"Hero Banner","content":"Walk on Clouds - lifestyle photo with model"},{"title":"Problem/Solution","content":"Tired of flat, uncomfortable slides? Our 4.5cm EVA foam changes everything"},{"title":"Features Grid","content":"4 key features with icons"},{"title":"Social Proof","content":"TikTok viral badge + customer reviews"},{"title":"Size Guide","content":"US/EU/CN conversion chart"},{"title":"Bundle Offer","content":"Buy 2 Save 12% CTA"}]},
         "video":{"video_concept":"Satisfying 'cloud walk' ASMR + before/after tired feet","hook":"POV: You just found the slides that 2M people are obsessed with 🤯","script":[{"scene":"Hook","duration":"0-3s","content":"Close-up of squishing the slide foam with hand","caption":"These slides have 2M+ views for a reason..."},{"scene":"Problem","duration":"3-7s","content":"Person rubbing tired feet after long day","caption":"Your feet after standing all day 😩"},{"scene":"Solution","duration":"7-15s","content":"Sliding feet into cloud slides, satisfied reaction","caption":"But then you try THESE 😮‍💨☁️"},{"scene":"Features","duration":"15-22s","content":"Quick cuts: non-slip bottom, water test, color options","caption":"Non-slip ✓ Waterproof ✓ 8 colors ✓"},{"scene":"CTA","duration":"22-27s","content":"Walking confidently, link in bio gesture","caption":"Link in bio - Buy 2 Save 12% 🛒"}],"hashtags":["cloudslides","comfyshoes","TikTokMadeMeBuyIt","pillow slides","summervibes","satisfying","shoesoftheday","amazonfinds","comfortfirst","musthave"],"music_suggestion":"Trending lo-fi beat or satisfying ASMR sounds"}},
    ]
    with get_conn() as conn:
        for c in content_records:
            conn.execute(
                "INSERT INTO content_records (product_title, product_price, content_type, page_json, video_json) VALUES (?,?,?,?,?)",
                (c["product_title"], c["product_price"], c["content_type"],
                 json.dumps(c.get("page"), ensure_ascii=False) if c.get("page") else None,
                 json.dumps(c.get("video"), ensure_ascii=False) if c.get("video") else None)
            )

    # ========== 5. SKU 映射 ==========
    sku_mappings = [
        {"tiktok_product_id":"TT10001","tiktok_sku":"GLOW-VC-30ML","alibaba_product_id":"ALI-688001","alibaba_sku":"VC-30ML-A","supplier_name":"义乌美妆工厂直营店","price_cny":12.5,"moq":100},
        {"tiktok_product_id":"TT10003","tiktok_sku":"LED-5M-WIFI","alibaba_product_id":"ALI-688003","alibaba_sku":"RGB-5M-WIFI","supplier_name":"深圳跨境电子供应链","price_cny":8.0,"moq":50},
        {"tiktok_product_id":"TT10004","tiktok_sku":"CLOUD-SLIDE-UNI","alibaba_product_id":"ALI-688004","alibaba_sku":"EVA-SLIDE-001","supplier_name":"福建晋江鞋业工厂","price_cny":8.0,"moq":50},
        {"tiktok_product_id":"TT10008","tiktok_sku":"HAIR-OIL-60ML","alibaba_product_id":"ALI-688008","alibaba_sku":"ROSEMARY-60ML","supplier_name":"广州白云化妆品批发","price_cny":6.5,"moq":200},
    ]
    with get_conn() as conn:
        for m in sku_mappings:
            conn.execute(
                "INSERT INTO sku_mappings (tiktok_product_id, tiktok_sku, alibaba_product_id, alibaba_sku, supplier_name, price_cny, moq) VALUES (?,?,?,?,?,?,?)",
                (m["tiktok_product_id"], m["tiktok_sku"], m["alibaba_product_id"], m["alibaba_sku"], m["supplier_name"], m["price_cny"], m["moq"])
            )

    # ========== 6. 订单数据 ==========
    orders = [
        {"tiktok_order_id":"TT20260415001","product_title":"Cloud Slides Pillow Slippers Unisex","product_id":"TT10004","quantity":2,"unit_price_usd":12.99,"total_usd":25.98,"customer_name":"Sarah Johnson","shipping_address":"1234 Oak Street, Los Angeles, CA 90001","status":"matched","matched_supplier":"福建晋江鞋业工厂","matched_1688_id":"ALI-688004","purchase_price_cny":16.0,"purchase_status":"ready_to_order"},
        {"tiktok_order_id":"TT20260415002","product_title":"Glow Skin Serum - Vitamin C Brightening","product_id":"TT10001","quantity":1,"unit_price_usd":14.99,"total_usd":14.99,"customer_name":"Emily Chen","shipping_address":"5678 Maple Ave, New York, NY 10001","status":"matched","matched_supplier":"义乌美妆工厂直营店","matched_1688_id":"ALI-688001","purchase_price_cny":12.5,"purchase_status":"ready_to_order"},
        {"tiktok_order_id":"TT20260415003","product_title":"LED Strip Lights RGB 5M Smart WiFi","product_id":"TT10003","quantity":3,"unit_price_usd":9.99,"total_usd":29.97,"customer_name":"Mike Brown","shipping_address":"910 Pine Rd, Chicago, IL 60601","status":"matched","matched_supplier":"深圳跨境电子供应链","matched_1688_id":"ALI-688003","purchase_price_cny":24.0,"purchase_status":"ordered"},
        {"tiktok_order_id":"TT20260415004","product_title":"Wireless Earbuds Pro ANC Bluetooth 5.3","product_id":"TT10006","quantity":1,"unit_price_usd":24.99,"total_usd":24.99,"customer_name":"Lisa Wang","shipping_address":"2468 Elm St, Houston, TX 77001","status":"pending","matched_supplier":None,"matched_1688_id":None,"purchase_price_cny":None,"purchase_status":"not_ordered"},
    ]
    with get_conn() as conn:
        for o in orders:
            conn.execute(
                """INSERT INTO orders (tiktok_order_id, product_title, product_id, quantity, unit_price_usd, total_usd,
                customer_name, shipping_address, status, matched_supplier, matched_1688_id, purchase_price_cny, purchase_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (o["tiktok_order_id"],o["product_title"],o["product_id"],o["quantity"],o["unit_price_usd"],o["total_usd"],
                 o["customer_name"],o["shipping_address"],o["status"],o["matched_supplier"],o["matched_1688_id"],o["purchase_price_cny"],o["purchase_status"])
            )

    # ========== 7. 库存同步记录 ==========
    sync_records = [
        {"tiktok_product_id":"TT10001","alibaba_product_id":"ALI-688001","stock_1688":350,"price_1688_cny":12.5,"previous_stock":400,"previous_price":12.5,"action_taken":"no_change"},
        {"tiktok_product_id":"TT10003","alibaba_product_id":"ALI-688003","stock_1688":8,"price_1688_cny":8.5,"previous_stock":50,"previous_price":8.0,"action_taken":"low_stock_alert"},
        {"tiktok_product_id":"TT10004","alibaba_product_id":"ALI-688004","stock_1688":1200,"price_1688_cny":8.0,"previous_stock":1200,"previous_price":8.0,"action_taken":"no_change"},
        {"tiktok_product_id":"TT10008","alibaba_product_id":"ALI-688008","stock_1688":0,"price_1688_cny":7.0,"previous_stock":100,"previous_price":6.5,"action_taken":"delist_tiktok"},
    ]
    with get_conn() as conn:
        for s in sync_records:
            conn.execute(
                "INSERT INTO inventory_sync (tiktok_product_id, alibaba_product_id, stock_1688, price_1688_cny, previous_stock, previous_price, action_taken) VALUES (?,?,?,?,?,?,?)",
                (s["tiktok_product_id"],s["alibaba_product_id"],s["stock_1688"],s["price_1688_cny"],s["previous_stock"],s["previous_price"],s["action_taken"])
            )

    # ========== 8. 支付记录 ==========
    payments = [
        {"order_id":"TT20260415001","payment_method":"alipay","amount":16.0,"currency":"CNY","status":"paid","transaction_id":"ALI2026041500001"},
        {"order_id":"TT20260415003","payment_method":"alipay","amount":24.0,"currency":"CNY","status":"paid","transaction_id":"ALI2026041500003"},
        {"order_id":"TT20260415001","payment_method":"stripe","amount":25.98,"currency":"USD","status":"completed","transaction_id":"pi_3Qx00001"},
    ]
    with get_conn() as conn:
        for p in payments:
            conn.execute(
                "INSERT INTO payments (order_id, payment_method, amount, currency, status, transaction_id) VALUES (?,?,?,?,?,?)",
                (p["order_id"],p["payment_method"],p["amount"],p["currency"],p["status"],p["transaction_id"])
            )

    # ========== 9. 收藏 ==========
    favorites = [
        {"product_id":"TT10004","title":"Cloud Slides Pillow Slippers Unisex","price":12.99,"category":"Fashion","note":"爆款，利润率72%"},
        {"product_id":"TT10008","title":"Hair Oil Rosemary Growth Serum 60ml","price":11.99,"category":"Beauty & Personal Care","note":"TikTok增长最快"},
        {"product_id":"TT10003","title":"LED Strip Lights RGB 5M Smart WiFi","price":9.99,"category":"Electronics","note":"长青品类，持续出单"},
    ]
    with get_conn() as conn:
        for f in favorites:
            conn.execute("INSERT INTO favorites (product_id, title, price, category, note) VALUES (?,?,?,?,?)",
                         (f["product_id"],f["title"],f["price"],f["category"],f["note"]))

    # ========== 10. 操作日志 ==========
    activities = [
        {"module":"monitor","action":"查看热销趋势","detail":"获取8个商品"},
        {"module":"monitor","action":"AI选品分析","detail":"关键词: beauty serum, 分析15个商品"},
        {"module":"monitor","action":"AI选品分析","detail":"关键词: led strip lights, 分析12个商品"},
        {"module":"supply","action":"供应商匹配","detail":"关键词: vitamin c serum, 匹配3个供应商"},
        {"module":"supply","action":"供应商匹配","detail":"关键词: cloud slides, 匹配2个供应商"},
        {"module":"content","action":"AI内容生成","detail":"商品: Cloud Slides, 类型: all"},
        {"module":"purchase","action":"创建订单","detail":"订单: TT20260415001, 状态: matched"},
        {"module":"purchase","action":"创建订单","detail":"订单: TT20260415002, 状态: matched"},
        {"module":"purchase","action":"创建订单","detail":"订单: TT20260415003, 状态: matched"},
        {"module":"purchase","action":"创建SKU映射","detail":"TikTok:TT10001 -> 1688:ALI-688001"},
        {"module":"purchase","action":"库存同步","detail":"同步4个商品"},
        {"module":"payment","action":"创建支付宝付款","detail":"订单: TT20260415001, ¥16.0"},
        {"module":"favorite","action":"收藏商品","detail":"Cloud Slides Pillow Slippers Unisex"},
        {"module":"system","action":"系统启动","detail":"库存同步定时任务已启动"},
    ]
    with get_conn() as conn:
        for a in activities:
            conn.execute("INSERT INTO activity_log (module, action, detail) VALUES (?,?,?)",
                         (a["module"],a["action"],a["detail"]))

    # ========== 11. 对话历史 ==========
    chats = [
        {"session_id":"demo001","role":"user","content":"帮我找美国热销的手机壳","action_type":None,"action_result":None},
        {"session_id":"demo001","role":"assistant","content":"已为您找到20个热销手机壳商品","action_type":"search_products","action_result":None},
        {"session_id":"demo001","role":"user","content":"匹配一下供应商","action_type":None,"action_result":None},
        {"session_id":"demo001","role":"assistant","content":"已匹配3个1688供应商，推荐义乌美妆工厂直营店","action_type":"match_suppliers","action_result":None},
    ]
    with get_conn() as conn:
        for c in chats:
            conn.execute("INSERT INTO chat_history (session_id, role, content, action_type, action_result) VALUES (?,?,?,?,?)",
                         (c["session_id"],c["role"],c["content"],c["action_type"],c["action_result"]))

    # ========== 12. 店铺绑定 ==========
    stores = [
        {"platform":"tiktok","store_name":"GlowBeautyUS","store_id":"TS10001","store_url":"https://shop.tiktok.com/glowbeautyus","access_token":"","country":"US"},
        {"platform":"shopee","store_name":"ComfyWear东南亚店","store_id":"SH20001","store_url":"https://shopee.co.id/comfywear","access_token":"","country":"ID"},
    ]
    with get_conn() as conn:
        for s in stores:
            conn.execute("INSERT INTO store_bindings (platform, store_name, store_id, store_url, access_token, country) VALUES (?,?,?,?,?,?)",
                         (s["platform"],s["store_name"],s["store_id"],s["store_url"],s["access_token"],s["country"]))

    print("Demo data seeded successfully!")
    print(f"  - 8 products")
    print(f"  - 2 analyses")
    print(f"  - 2 supplier matches")
    print(f"  - 1 content record")
    print(f"  - 4 SKU mappings")
    print(f"  - 4 orders")
    print(f"  - 4 inventory sync records")
    print(f"  - 3 payment records")
    print(f"  - 3 favorites")
    print(f"  - 14 activity logs")


if __name__ == "__main__":
    seed()
