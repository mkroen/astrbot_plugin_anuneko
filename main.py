import json
import httpx
from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core import AstrBotConfig

# API 地址
CHAT_API_URL = "https://anuneko.com/api/v1/chat"
STREAM_API_URL = "https://anuneko.com/api/v1/msg/{uuid}/stream"
SELECT_CHOICE_URL = "https://anuneko.com/api/v1/msg/select-choice"
SELECT_MODEL_URL = "https://anuneko.com/api/v1/user/select_model"

# 模型映射
MODELS = {
    "1": ("Orange Cat", "橘猫"),
    "2": ("Exotic Shorthair", "黑猫"),
}


@register("anuneko", "mkroen", "AnuNeko AI 对话插件", "1.0.0")
class AnuNekoPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.sessions = {}  # session_key -> chat_id (群聊用群ID，私聊用用户ID)
        self.session_models = {}  # session_key -> model_name

    def _get_config(self, key: str, default=None):
        return self.config.get(key, default)

    def _build_headers(self):
        token = self._get_config("token", "")

        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://anuneko.com",
            "referer": "https://anuneko.com/",
            "user-agent": "Mozilla/5.0",
            "x-app_id": "com.anuttacon.neko",
            "x-client_type": "4",
            "x-device_id": "7b75a432-6b24-48ad-b9d3-3dc57648e3e3",
            "x-token": token,
        }
        return headers

    def _get_proxy(self):
        proxy = self._get_config("proxy", "")
        return proxy if proxy else None

    def _get_session_key(self, event: AstrMessageEvent) -> str:
        """获取会话标识：群聊用 group_id（整个群共享），私聊用 sender_id"""
        group_id = event.get_group_id()
        if group_id:
            return f"group_{group_id}"
        return f"private_{event.get_sender_id()}"

    async def _create_session(self, session_key: str):
        headers = self._build_headers()
        model = self.session_models.get(session_key, "Orange Cat")

        try:
            async with httpx.AsyncClient(timeout=10, proxy=self._get_proxy()) as client:
                resp = await client.post(CHAT_API_URL, headers=headers, json={"model": model})
                resp_json = resp.json()

            chat_id = resp_json.get("chat_id") or resp_json.get("id")
            if chat_id:
                self.sessions[session_key] = chat_id
                await self._switch_model(session_key, chat_id, model)
                return chat_id
        except Exception as e:
            logger.error(f"创建会话失败: {type(e).__name__}: {e}")
        return None

    async def _switch_model(self, session_key: str, chat_id: str, model_name: str):
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(timeout=10, proxy=self._get_proxy()) as client:
                resp = await client.post(
                    SELECT_MODEL_URL, headers=headers, json={"chat_id": chat_id, "model": model_name}
                )
                if resp.status_code == 200:
                    self.session_models[session_key] = model_name
                    return True
        except Exception as e:
            logger.error(f"切换模型失败: {e}")
        return False

    async def _send_choice(self, msg_id: str):
        headers = self._build_headers()
        try:
            async with httpx.AsyncClient(timeout=5, proxy=self._get_proxy()) as client:
                await client.post(
                    SELECT_CHOICE_URL, headers=headers, json={"msg_id": msg_id, "choice_idx": 0}
                )
        except Exception as e:
            logger.error(f"发送选择失败: {e}")

    async def _stream_reply(self, session_uuid: str, text: str) -> str:
        token = self._get_config("token", "")
        headers = {"x-token": token, "Content-Type": "text/plain"}

        url = STREAM_API_URL.format(uuid=session_uuid)
        data = json.dumps({"contents": [text]}, ensure_ascii=False)

        result = ""
        current_msg_id = None

        try:
            async with httpx.AsyncClient(timeout=None, proxy=self._get_proxy()) as client:
                async with client.stream("POST", url, headers=headers, content=data) as resp:
                    async for line in resp.aiter_lines():
                        if not line:
                            continue

                        if not line.startswith("data: "):
                            # 尝试解析错误响应，忽略空行和非JSON内容
                            if line.strip() and line.strip().startswith("{"):
                                try:
                                    error_json = json.loads(line)
                                    if error_json.get("code") == "chat_choice_shown":
                                        return "⚠️ 检测到对话分支未选择，请重试或新建会话。"
                                except json.JSONDecodeError:
                                    pass
                            continue

                        raw_json = line[6:].strip()
                        if not raw_json:
                            continue

                        try:
                            j = json.loads(raw_json)
                        except json.JSONDecodeError:
                            continue

                        if "msg_id" in j:
                            current_msg_id = j["msg_id"]

                        if "c" in j and isinstance(j["c"], list):
                            for choice in j["c"]:
                                if choice.get("c", 0) == 0 and "v" in choice:
                                    result += choice["v"]
                        elif "v" in j and isinstance(j["v"], str):
                            result += j["v"]

            if current_msg_id:
                await self._send_choice(current_msg_id)
        except Exception as e:
            logger.error(f"流式回复失败: {e}")
            return "请求失败，请稍后再试。"

        return result

    @filter.command("neko切换模式")
    async def switch_mode(self, event: AstrMessageEvent):
        """切换 AI 模型：/neko切换模式 1(橘猫) 或 2(黑猫)"""
        session_key = self._get_session_key(event)
        arg = event.message_str.replace("neko切换模式", "").strip()

        if arg not in MODELS:
            yield event.plain_result("请指定模式：1(橘猫) 或 2(黑猫)\n用法：/neko切换模式 1")
            return

        model_key, model_name = MODELS[arg]

        if session_key not in self.sessions:
            chat_id = await self._create_session(session_key)
            if not chat_id:
                yield event.plain_result("❌ 切换失败：无法创建会话")
                return
        else:
            chat_id = self.sessions[session_key]

        success = await self._switch_model(session_key, chat_id, model_key)

        if success:
            yield event.plain_result(f"✨ 已切换到 {model_name} 模式")
        else:
            yield event.plain_result(f"❌ 切换到 {model_name} 失败")

    @filter.command("neko新会话")
    async def new_session(self, event: AstrMessageEvent):
        """创建新的对话会话：/neko新会话"""
        session_key = self._get_session_key(event)

        new_id = await self._create_session(session_key)

        if new_id:
            model = self.session_models.get(session_key, "Orange Cat")
            model_name = "橘猫" if model == "Orange Cat" else "黑猫"
            yield event.plain_result(f"✨ 已创建新会话（当前模式：{model_name}）")
        else:
            yield event.plain_result("❌ 创建会话失败，请稍后再试。")

    @filter.command("neko")
    async def chat(self, event: AstrMessageEvent):
        """与 AnuNeko AI 对话：/neko <内容>"""
        session_key = self._get_session_key(event)
        text = event.message_str.replace("neko", "", 1).strip()

        if not text:
            yield event.plain_result("❗ 请输入内容，例如：/neko 你好")
            return

        if session_key not in self.sessions:
            cid = await self._create_session(session_key)
            if not cid:
                yield event.plain_result("❌ 创建会话失败，请稍后再试。")
                return

        chat_id = self.sessions[session_key]
        reply = await self._stream_reply(chat_id, text)

        yield event.plain_result(reply)
