import os
import uuid
from pathlib import Path
from io import BytesIO

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.core.config import LLM_API_KEY
from app.models.story import Story
from app.db.session import SessionLocal


from app.services.title_service import generate_story_title

# STATIC_DIR = Path("./static")
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
COVERS_DIR = STATIC_DIR / "covers"
COVERS_DIR.mkdir(parents=True, exist_ok=True)


def _pick_template_colors(story_id: int):
    palettes = [
        ("#75C8E8", "#2AA7D6", "#EAF9FF"),
        ("#F8BBD0", "#F48FB1", "#FFF3F7"),
        ("#FFD180", "#FFB74D", "#FFF8E8"),
        ("#A5D6A7", "#66BB6A", "#F1FFF2"),
        ("#9FA8DA", "#5C6BC0", "#F3F5FF"),
    ]
    return palettes[story_id % len(palettes)]


def _load_font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    lines = []
    current = ""
    for ch in text:
        test = current + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines[:3]


def build_fallback_cover(story: Story) -> str:
    bg1, bg2, fg = _pick_template_colors(story.id)
    width, height = 768, 1024

    img = Image.new("RGB", (width, height), bg1)
    draw = ImageDraw.Draw(img)

    # 简单渐变感
    for i in range(height):
        ratio = i / max(height - 1, 1)
        r1 = int(int(bg1[1:3], 16) * (1 - ratio) + int(bg2[1:3], 16) * ratio)
        g1 = int(int(bg1[3:5], 16) * (1 - ratio) + int(bg2[3:5], 16) * ratio)
        b1 = int(int(bg1[5:7], 16) * (1 - ratio) + int(bg2[5:7], 16) * ratio)
        draw.line((0, i, width, i), fill=(r1, g1, b1))

    # 顶部标签
    draw.rounded_rectangle((80, 50, width - 80, 130), radius=18, fill="#FFF7E8", outline="#333333", width=2)

    title_font = _load_font(48)
    label_font = _load_font(28)
    small_font = _load_font(24)

    label = "为绘画角色注入生命力"
    draw.text((110, 76), label, font=label_font, fill="#2b2b2b")

    # 主标题
    lines = _wrap_text(draw, story.title or "未命名故事", title_font, width - 160)
    y = 180
    for line in lines:
        draw.text((90, y), line, font=title_font, fill="#0B5C87")
        y += 64

    # 作者区
    draw.text((90, 360), "KidRead", font=small_font, fill=fg)

    # 右下装饰线
    for offset in range(14):
        draw.arc((180 + offset * 18, 740 - offset * 4, 760 + offset * 10, 1080 - offset * 8), 210, 300, fill=fg, width=2)

    filename = f"fallback_{story.id}_{uuid.uuid4().hex[:8]}.png"
    output_path = COVERS_DIR / filename
    img.save(output_path, format="PNG")

    return f"/static/covers/{filename}"


def build_cover_prompt(story: Story) -> str:
    title = story.title or "儿童故事"
    content = (story.content or "")[:1200]
    return f"""
儿童绘本封面插画，温柔、干净、适合小朋友，构图完整，留出顶部与中部适合后期叠加书名的空白区域。
不要在画面里生成任何文字。
故事标题：{title}
故事内容摘要：{content}
风格：儿童绘本、柔和色彩、细腻但简洁、温暖有想象力。
""".strip()


def generate_ai_cover_for_story(story_id: int):
    db = SessionLocal()
    try:
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            return

        story.cover_status = "generating"
        db.commit()

        prompt = build_cover_prompt(story)
        story.cover_prompt = prompt
        db.commit()

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        payload = {
            "model": "qwen-image-2.0-pro",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ]
            },
            "parameters": {
                "size": "1536*2048",
                "n": 1,
                "watermark": False,
                "prompt_extend": True
            }
        }

        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json"
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            # 同步接口返回 choices/content/image 或 output.results，做兼容处理
            image_url = None

            choices = (((data or {}).get("output") or {}).get("choices") or [])
            if choices:
                content = (((choices[0] or {}).get("message") or {}).get("content") or [])
                for item in content:
                    image_url = item.get("image") or item.get("url")
                    if image_url:
                        break

            if not image_url:
                results = (((data or {}).get("output") or {}).get("results") or [])
                if results:
                    image_url = results[0].get("url")

            if not image_url:
                story.cover_status = "failed"
                db.commit()
                return

            img_resp = client.get(image_url)
            img_resp.raise_for_status()

            filename = f"ai_cover_{story.id}_{uuid.uuid4().hex[:8]}.png"
            save_path = COVERS_DIR / filename
            save_path.write_bytes(img_resp.content)

        story.cover_image_url = f"/static/covers/{filename}"
        story.cover_status = "ready"
        db.commit()

    except Exception:
        if story_id:
            try:
                story = db.query(Story).filter(Story.id == story_id).first()
                if story:
                    story.cover_status = "failed"
                    db.commit()
            except Exception:
                pass
    finally:
        db.close()


def finalize_story_assets(story_id: int):
    db = SessionLocal()
    try:
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            return

        # 1. 优化正式标题
        try:
            if story.title_source != "manual":
                final_title = generate_story_title(
                    content=story.content or "",
                    age=story.age or 6,
                    fallback=story.title or "我的新故事"
                )
                if final_title and final_title != story.title:
                    story.title = final_title
                    story.title_source = "auto"
                    db.commit()
                    db.refresh(story)

                    # 标题变了，重做 fallback cover
                    fallback_cover_url = build_fallback_cover(story)
                    story.fallback_cover_url = fallback_cover_url
                    db.commit()
                    db.refresh(story)
        except Exception:
            pass

        # 2. 生成 AI cover
        generate_ai_cover_for_story(story_id)

    finally:
        db.close()