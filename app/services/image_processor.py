"""图片处理服务 - 去水印、AI抠图、加滤镜、OCR中文识别与抹除"""

import io
import os
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import httpx

# rembg 用于AI抠图（去背景），首次使用会下载模型（~170MB）
# 如果 rembg 安装失败可以先跳过
try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("[ImageProcessor] rembg 未安装，AI抠图功能不可用。运行: pip install rembg")

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "images")
os.makedirs(SAVE_DIR, exist_ok=True)


class ImageProcessor:
    """图片处理器 - 处理1688和TikTok商品图片"""

    # ==================== 下载图片 ====================
    async def download_image(self, url: str) -> Image.Image | None:
        """下载网络图片"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return Image.open(io.BytesIO(resp.content))
        except Exception as e:
            print(f"[ImageProcessor] 下载失败: {e}")
        return None

    # ==================== TikTok 水印去除 ====================
    def remove_tiktok_watermark(self, img: Image.Image) -> Image.Image:
        """去除 TikTok 水印

        TikTok 水印通常在：
        1. 右下角的 TikTok logo（半透明）
        2. 底部用户名水印
        策略：裁剪底部 + 右下角区域修复
        """
        width, height = img.size

        # 裁剪掉底部 8%（通常包含用户名水印）
        crop_bottom = int(height * 0.08)
        img = img.crop((0, 0, width, height - crop_bottom))

        # 右下角 TikTok logo 区域用周围像素填充（简单修复）
        width, height = img.size
        logo_region = (int(width * 0.82), int(height * 0.85), width, height)
        region = img.crop(logo_region)
        # 用高斯模糊覆盖 logo
        blurred = region.filter(ImageFilter.GaussianBlur(radius=15))
        img.paste(blurred, logo_region)

        return img

    # ==================== 1688 水印去除 ====================
    def remove_1688_watermark(self, img: Image.Image) -> Image.Image:
        """去除 1688 商品图水印

        1688 水印通常是半透明文字（店铺名），覆盖在图片中央
        策略：中间区域亮度增强 + 去噪
        """
        # 增强对比度和亮度，使水印变淡
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)

        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.05)

        return img

    # ==================== AI 抠图（去背景） ====================
    def remove_background(self, img: Image.Image) -> Image.Image:
        """AI 抠图 - 去除商品图片背景，用于制作干净的产品图"""
        if not HAS_REMBG:
            print("[ImageProcessor] rembg 未安装，跳过抠图")
            return img

        # PIL Image -> bytes -> rembg -> PIL Image
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        result_bytes = rembg_remove(img_bytes.getvalue())
        return Image.open(io.BytesIO(result_bytes))

    # ==================== 滤镜效果 ====================
    def apply_filter(self, img: Image.Image, filter_type: str = "aesthetic") -> Image.Image:
        """应用滤镜效果，使商品图更适合 TikTok 风格

        filter_type:
        - aesthetic: 轻柔暖色调（适合美妆/家居）
        - vibrant: 高饱和鲜艳（适合电子/潮流）
        - clean: 干净白底（适合商品展示）
        - warm: 暖色系（适合食品）
        """
        if filter_type == "aesthetic":
            img = ImageEnhance.Color(img).enhance(0.9)
            img = ImageEnhance.Brightness(img).enhance(1.08)
            img = ImageEnhance.Contrast(img).enhance(1.05)
        elif filter_type == "vibrant":
            img = ImageEnhance.Color(img).enhance(1.3)
            img = ImageEnhance.Contrast(img).enhance(1.15)
            img = ImageEnhance.Sharpness(img).enhance(1.2)
        elif filter_type == "clean":
            img = ImageEnhance.Brightness(img).enhance(1.15)
            img = ImageEnhance.Contrast(img).enhance(1.1)
            img = ImageEnhance.Sharpness(img).enhance(1.3)
        elif filter_type == "warm":
            img = ImageEnhance.Color(img).enhance(1.1)
            img = ImageEnhance.Brightness(img).enhance(1.05)
            # 简单暖色调：轻微增加红黄通道
            if img.mode == "RGB":
                r, g, b = img.split()
                r = r.point(lambda x: min(255, int(x * 1.05)))
                img = Image.merge("RGB", (r, g, b))

        return img

    # ==================== OCR 中文识别与抹除 ====================
    def detect_and_remove_chinese_text(self, img: Image.Image) -> Image.Image:
        """检测并抹除图片中的中文文字

        简单实现：扫描密集的深色像素区域（文字区域），用周围颜色填充。
        生产环境建议用 PaddleOCR 或百度OCR API 精确识别。
        """
        # 简单策略：将图片转灰度，找到高对比区域，用模糊覆盖
        gray = img.convert("L")
        width, height = img.size

        # 扫描文字可能出现的区域（通常在图片边缘）
        regions_to_check = [
            (0, int(height * 0.9), width, height),          # 底部
            (0, 0, width, int(height * 0.08)),               # 顶部
            (0, 0, int(width * 0.15), height),               # 左边
            (int(width * 0.85), 0, width, height),           # 右边
        ]

        for region in regions_to_check:
            crop = gray.crop(region)
            # 计算该区域的深色像素比例
            pixels = list(crop.getdata())
            if not pixels:
                continue
            dark_ratio = sum(1 for p in pixels if p < 80) / len(pixels)

            # 如果深色像素较多，可能是文字，用模糊覆盖
            if dark_ratio > 0.05:
                region_img = img.crop(region)
                blurred = region_img.filter(ImageFilter.GaussianBlur(radius=10))
                img.paste(blurred, region)

        return img

    # ==================== 完整处理流程 ====================
    async def process_product_image(
        self,
        image_url: str,
        source: str = "tiktok",
        remove_bg: bool = False,
        filter_type: str = "aesthetic",
        remove_chinese: bool = False,
        save: bool = True,
    ) -> dict:
        """完整的商品图片处理流程

        1. 下载图片
        2. 去水印（TikTok/1688）
        3. 可选：AI抠图
        4. 可选：抹除中文
        5. 应用滤镜
        6. 保存
        """
        # Step 1: 下载
        img = await self.download_image(image_url)
        if img is None:
            return {"error": "图片下载失败", "url": image_url}

        original_size = img.size
        steps = ["downloaded"]

        # Step 2: 去水印
        if source == "tiktok":
            img = self.remove_tiktok_watermark(img)
            steps.append("tiktok_watermark_removed")
        elif source == "1688":
            img = self.remove_1688_watermark(img)
            steps.append("1688_watermark_removed")

        # Step 3: AI 抠图
        if remove_bg:
            img = self.remove_background(img)
            steps.append("background_removed")

        # Step 4: 抹除中文
        if remove_chinese:
            img = self.detect_and_remove_chinese_text(img)
            steps.append("chinese_text_removed")

        # Step 5: 滤镜
        if filter_type:
            img = self.apply_filter(img, filter_type)
            steps.append(f"filter_{filter_type}")

        # Step 6: 保存
        result = {
            "original_size": original_size,
            "processed_size": img.size,
            "steps": steps,
            "rembg_available": HAS_REMBG,
        }

        if save:
            import hashlib
            filename = hashlib.md5(image_url.encode()).hexdigest() + ".png"
            filepath = os.path.join(SAVE_DIR, filename)
            img.save(filepath, "PNG")
            result["saved_path"] = filepath
            result["filename"] = filename

        return result
