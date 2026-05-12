from __future__ import annotations

import os
import sys

import requests

BASE_URL = os.getenv("HTTP_PUBLIC_BASE_URL")
#HTTP_PUBLIC_BASE_URL


def req(method: str, path: str, *, token: str | None = None, json=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.request(method, f"{BASE_URL}{path}", headers=headers, json=json, timeout=60)
    print(method, path, resp.status_code)
    if resp.status_code >= 400:
        print(resp.text)
        sys.exit(1)
    return resp.json()


def main() -> None:
    login = req("POST", "/api/auth/login", json={"dev_openid": "smoke", "nickname": "测试用户", "age": 8, "theme_preference": "meadow"})
    token = login["token"]
    req("GET", "/api/app/bootstrap", token=token)
    req("POST", "/api/sessions", token=token, json={"scene": "create", "story_id": 0, "session_id": "smoke_create", "title": "冒烟测试"})
    chat = req("POST", "/api/chat/unified", token=token, json={
        "scene": "create", "story_id": 0, "session_id": "smoke_create", "age": 8,
        "input_mode": "text", "text": "写一个关于星空列车的短故事", "history": [],
    })
    content = "\n".join([chat.get("lead_text", ""), chat.get("story_text", ""), chat.get("guide_text", "")]).strip()
    story = req("POST", "/api/stories", token=token, json={"title": "星空列车", "age": 8, "content": content})
    story_id = story["id"]
    req("GET", f"/api/debug/story/{story_id}/chunks", token=token)
    print("Smoke test completed. story_id=", story_id)


if __name__ == "__main__":
    main()
