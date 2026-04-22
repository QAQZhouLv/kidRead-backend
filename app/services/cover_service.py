import json
import uuid
from pathlib import Path

import httpx

from app.core.config import LLM_API_KEY
from app.db.session import SessionLocal
from app.models.story import Story
from app.services.archive_story_service import generate_story_spec_and_state
from app.services.rule_service import normalize_age_group
from app.services.title_service import generate_story_title

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
COVERS_DIR = STATIC_DIR / "covers"
COVERS_DIR.mkdir(parents=True, exist_ok=True)


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


def _sync_story_context(story: Story):
    spec, state, summary = generate_story_spec_and_state(story.age or 6, story.content or "")
    story.story_spec = json.dumps(spec, ensure_ascii=False)
    story.story_state = json.dumps(state, ensure_ascii=False)
    story.story_summary = json.dumps(summary, ensure_ascii=False)
    story.target_age = normalize_age_group(story.age or 6)
    story.difficulty_level = str((spec or {}).get("difficulty_level") or story.difficulty_level or "L2")
    story.safety_status = story.safety_status or "passed"


def generate_ai_cover_for_story(story_id: int):
    db = SessionLocal()
    try:
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            return

        story.cover_status = "generating"
        story.cover_prompt = build_cover_prompt(story)
        db.commit()

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        payload = {
            "model": "qwen-image-2.0-pro",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": story.cover_prompt}]
                    }
                ]
            },
            "parameters": {
                "size": "1536*2048",
                "n": 1,
                "watermark": False,
                "prompt_extend": True,
            },
        }
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

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

        try:
            _sync_story_context(story)
            db.commit()
            db.refresh(story)
        except Exception:
            db.rollback()

        try:
            if story.title_source != "manual":
                final_title = generate_story_title(
                    content=story.content or "",
                    age=story.age or 6,
                    fallback=story.title or "我的新故事",
                )
                if final_title and final_title != story.title:
                    story.title = final_title
                    story.title_source = "auto"
                    db.commit()
                    db.refresh(story)
        except Exception:
            db.rollback()

        generate_ai_cover_for_story(story_id)

    finally:
        db.close()
