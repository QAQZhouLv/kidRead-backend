import os
import json
import base64
import hashlib
import hmac
import asyncio
import tempfile
from datetime import datetime
from email.utils import formatdate
from typing import Callable, Awaitable, Optional
from urllib.parse import urlencode

import websockets
from dotenv import load_dotenv

load_dotenv()

# 从项目根目录 .env 读取
XF_APP_ID = os.getenv("XF_APP_ID", "")
XF_API_KEY = os.getenv("XF_API_KEY", "")
XF_API_SECRET = os.getenv("XF_API_SECRET", "")

# 讯飞语音听写（流式版）接口
XF_HOST = os.getenv("XF_HOST", "iat-api.xfyun.cn")
XF_PATH = os.getenv("XF_PATH", "/v2/iat")
# wss://iat-api.xfyun.cn/v2/iat

# 识别参数
XF_LANGUAGE = os.getenv("XF_LANGUAGE", "zh_cn")
XF_DOMAIN = os.getenv("XF_DOMAIN", "iat")
XF_ACCENT = os.getenv("XF_ACCENT", "mandarin")
XF_VAD_EOS = int(os.getenv("XF_VAD_EOS", "5000"))

# 你当前历史代码里用的是 mp3/lame，这里默认也沿用它
# 如果后面你小程序前端改成 pcm，这里可以改成 raw / speex / lame 等对应值
XF_AUDIO_FORMAT = os.getenv("XF_AUDIO_FORMAT", "audio/L16;rate=16000")
XF_AUDIO_ENCODING = os.getenv("XF_AUDIO_ENCODING", "lame")


def _check_env():
    if not XF_APP_ID or not XF_API_KEY or not XF_API_SECRET:
        raise RuntimeError(
            "讯飞 ASR 配置缺失，请在项目根目录 .env 中设置："
            "XF_APP_ID / XF_API_KEY / XF_API_SECRET"
        )


def build_xfyun_ws_url() -> str:
    """
    构造讯飞 websocket 鉴权 URL
    """
    _check_env()

    date = formatdate(
        timeval=datetime.utcnow().timestamp(),
        localtime=False,
        usegmt=True
    )

    signature_origin = f"host: {XF_HOST}\ndate: {date}\nGET {XF_PATH} HTTP/1.1"
    signature_sha = hmac.new(
        XF_API_SECRET.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")

    authorization_origin = (
        f'api_key="{XF_API_KEY}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature}"'
    )
    authorization = base64.b64encode(
        authorization_origin.encode("utf-8")
    ).decode("utf-8")

    params = {
        "authorization": authorization,
        "date": date,
        "host": XF_HOST,
    }

    return f"wss://{XF_HOST}{XF_PATH}?{urlencode(params)}"


# def _extract_text_from_xfyun_message(data: dict) -> str:
#     """
#     从讯飞返回结构里抽取文字
#     """
#     result = data.get("data", {}).get("result") or {}
#     ws_list = result.get("ws", []) or []

#     sentence = "".join(
#         cw.get("w", "")
#         for item in ws_list
#         for cw in item.get("cw", [])
#     )
#     return sentence

def _extract_words(data: dict) -> str:
    """
    从单条讯飞消息里提取本次 words
    """
    result = data.get("data", {}).get("result") or {}
    ws_list = result.get("ws", []) or []

    sentence = "".join(
        cw.get("w", "")
        for item in ws_list
        for cw in item.get("cw", [])
    )
    return sentence


def _get_result_meta(data: dict):
    """
    提取 pgs / rg 元信息
    pgs:
      - apd: append
      - rpl: replace
    rg:
      - 需要替换的结果片段范围（1-based）
    """
    result = data.get("data", {}).get("result") or {}
    pgs = result.get("pgs")
    rg = result.get("rg") or []
    return pgs, rg


class ASRStreamBridge:
    """
    讯飞流式识别桥接层

    用法目标：
    - start(): 建立与讯飞 websocket 的连接
    - send_audio_frame(): 持续发送音频帧
    - stop(): 通知结束
    - 在识别过程中，通过 on_partial / on_final 回调把文字吐给外层
    """

    def __init__(
        self,
        on_partial: Callable[[str], Awaitable[None]],
        on_final: Callable[[str], Awaitable[None]],
    ):
        self.on_partial = on_partial
        self.on_final = on_final

        self.ws = None
        self._recv_task: Optional[asyncio.Task] = None
        self._closed = False
        self._started = False
        self._done_event = asyncio.Event()

        self._last_partial_text = ""
        self._final_text = ""
        self._result_parts = []

    async def start(self):
        """
        建立与讯飞 websocket 的连接，并启动后台接收循环
        """
        if self._closed:
            raise RuntimeError("ASRStreamBridge 已关闭，不能再次 start")

        ws_url = build_xfyun_ws_url()
        self.ws = await websockets.connect(
            ws_url,
            max_size=10 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=20,
        )

        self._recv_task = asyncio.create_task(self._recv_loop())




    async def _recv_loop(self):
        """
        持续接收讯飞返回结果，并做累计/替换
        """
        try:
            while True:
                msg = await self.ws.recv()
                data = json.loads(msg)

                code = data.get("code", -1)
                if code != 0:
                    message = data.get("message", "unknown error")
                    raise RuntimeError(f"讯飞识别失败：code={code}, message={message}")

                text = _extract_words(data)
                pgs, rg = _get_result_meta(data)
                status = data.get("data", {}).get("status")

                if text:
                    if pgs == "rpl" and isinstance(rg, list) and len(rg) == 2:
                        start = max(rg[0] - 1, 0)
                        end = max(rg[1], start)

                        while len(self._result_parts) < end:
                            self._result_parts.append("")

                        self._result_parts[start:end] = [text]

                    else:
                        # 默认按 append 处理
                        self._result_parts.append(text)

                    merged_text = "".join(self._result_parts).strip()
                    self._last_partial_text = merged_text
                    await self.on_partial(merged_text)

                if status == 2:
                    final_text = "".join(self._result_parts).strip() or self._last_partial_text or self._final_text
                    self._final_text = final_text
                    await self.on_final(final_text)
                    self._done_event.set()
                    break

        except asyncio.CancelledError:
            self._done_event.set()
            raise
        except Exception:
            self._done_event.set()
            raise

    
    async def send_audio_frame(self, audio_bytes: bytes):
        """
        把音频帧发给讯飞。
        第一次发 status=0，并携带 common/business；
        后续发 status=1。
        """
        if self._closed:
            raise RuntimeError("连接已关闭，不能继续发送音频")

        if not self.ws:
            raise RuntimeError("请先调用 start()")

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        if not self._started:
            frame = {
                "common": {
                    "app_id": XF_APP_ID
                },
                "business": {
                    "language": XF_LANGUAGE,
                    "domain": XF_DOMAIN,
                    "accent": XF_ACCENT,
                    "vad_eos": XF_VAD_EOS,
                },
                "data": {
                    "status": 0,
                    "format": XF_AUDIO_FORMAT,
                    "encoding": XF_AUDIO_ENCODING,
                    "audio": audio_b64,
                }
            }
            self._started = True
        else:
            frame = {
                "data": {
                    "status": 1,
                    "format": XF_AUDIO_FORMAT,
                    "encoding": XF_AUDIO_ENCODING,
                    "audio": audio_b64,
                }
            }

        await self.ws.send(json.dumps(frame, ensure_ascii=False))

    async def stop(self):
        """
        通知讯飞音频结束，并关闭连接
        """
        if self._closed:
            return

        self._closed = True

        try:
            if self.ws:
                end_frame = {
                    "data": {
                        "status": 2,
                        "format": XF_AUDIO_FORMAT,
                        "encoding": XF_AUDIO_ENCODING,
                        "audio": ""
                    }
                }
                await self.ws.send(json.dumps(end_frame, ensure_ascii=False))
        except Exception:
            pass

        # 等待最终结果回来，最多等 3 秒
        try:
            await asyncio.wait_for(self._done_event.wait(), timeout=3.0)
        except Exception:
            pass

        try:
            if self.ws:
                await self.ws.close()
        except Exception:
            pass

        # 如果接收任务还活着，清掉
        try:
            if self._recv_task and not self._recv_task.done():
                self._recv_task.cancel()
        except Exception:
            pass


async def _recognize_file_with_xfyun(file_bytes: bytes) -> str:
    """
    把整段文件作为“伪流式”发给讯飞，得到最终结果
    这是对你旧版 /api/asr 逻辑的封装延续
    """
    ws_url = build_xfyun_ws_url()
    final_text_parts = []

    async with websockets.connect(
        ws_url,
        max_size=10 * 1024 * 1024,
        ping_interval=20,
        ping_timeout=20,
    ) as ws:
        chunk_size = 8000
        chunks = [
            file_bytes[i:i + chunk_size]
            for i in range(0, len(file_bytes), chunk_size)
        ]

        for idx, chunk in enumerate(chunks):
            audio_b64 = base64.b64encode(chunk).decode("utf-8")

            if idx == 0:
                frame = {
                    "common": {
                        "app_id": XF_APP_ID
                    },
                    "business": {
                        "language": XF_LANGUAGE,
                        "domain": XF_DOMAIN,
                        "accent": XF_ACCENT,
                        "vad_eos": XF_VAD_EOS,
                    },
                    "data": {
                        "status": 0,
                        "format": XF_AUDIO_FORMAT,
                        "encoding": XF_AUDIO_ENCODING,
                        "audio": audio_b64
                    }
                }
            else:
                frame = {
                    "data": {
                        "status": 1,
                        "format": XF_AUDIO_FORMAT,
                        "encoding": XF_AUDIO_ENCODING,
                        "audio": audio_b64
                    }
                }

            await ws.send(json.dumps(frame, ensure_ascii=False))
            await asyncio.sleep(0.04)

        end_frame = {
            "data": {
                "status": 2,
                "format": XF_AUDIO_FORMAT,
                "encoding": XF_AUDIO_ENCODING,
                "audio": ""
            }
        }
        await ws.send(json.dumps(end_frame, ensure_ascii=False))

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            code = data.get("code", -1)
            if code != 0:
                message = data.get("message", "unknown error")
                raise RuntimeError(f"讯飞识别失败：code={code}, message={message}")

            text = _extract_words(data)
            if text:
                final_text_parts.append(text)

            status = data.get("data", {}).get("status")
            if status == 2:
                break

    return "".join(final_text_parts).strip()


async def transcribe_file_bytes(file_bytes: bytes) -> str:
    """
    非流式上传文件识别，供 /api/asr 使用
    """
    _check_env()

    if not file_bytes:
        return ""

    return await _recognize_file_with_xfyun(file_bytes)