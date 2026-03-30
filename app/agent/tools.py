from typing import List
from langchain.tools import tool

UNSAFE_WORDS = [
    "自杀", "杀人", "炸弹", "毒品", "色情", "强奸",
    "suicide", "kill", "bomb", "drug", "porn"
]

END_CHAT_WORDS = [
    "不想聊了", "不聊了", "到此为止", "结束吧", "先这样",
    "我要走了", "我要离开了", "拜拜", "再见", "今天先到这里",
    "stop", "bye", "goodbye", "end", "finish"
]

@tool
def classify_intent_tool(scene: str, user_text: str) -> str:
    """
    Classify the user's intent into one of:
    create_story, continue_story, ask_about_story, adjust_story, unsafety
    """
    text = user_text.strip().lower()

    if any(word in text for word in UNSAFE_WORDS):
        return "unsafety"
    
    if any(word in text for word in END_CHAT_WORDS):
        return "end_chat"

    continue_keywords = ["继续", "续写", "然后呢", "后面呢", "继续写", "go on", "continue"]
    ask_keywords = ["为什么", "谁", "什么", "怎么", "解释", "why", "what", "who", "how"]
    adjust_keywords = ["改", "修改", "换成", "不要", "更搞笑", "更温柔", "调整", "change", "rewrite"]

    if any(word in text for word in continue_keywords):
        return "continue_story"

    if any(word in text for word in adjust_keywords):
        return "adjust_story"

    if any(word in text for word in ask_keywords):
        return "ask_about_story"

    if scene == "create":
        return "create_story"

    return "continue_story"


@tool
def create_story_tool(age: int, user_text: str) -> str:
    """Generate story content for starting a new story."""
    if age <= 6:
        return f"从前，有一个小小的朋友。它听见了这样一个想法：{user_text}。于是，一场温柔又新奇的冒险开始了。"
    if age <= 9:
        return f"在一个明亮又神奇的早晨，故事围绕“{user_text}”慢慢展开。主角带着好奇心，走进了一个充满惊喜的新世界。"
    return f"故事在一个充满想象力的地方展开，而“{user_text}”成为了这场冒险最初的线索。主角很快发现，前方正有新的变化等待着它。"


@tool
def continue_story_tool(age: int, user_text: str) -> str:
    """Continue the current story."""
    if age <= 6:
        return f"接着，故事继续往前走。因为“{user_text}”，主角鼓起勇气，向前迈出了新的一步。"
    if age <= 9:
        return f"故事继续发展。围绕“{user_text}”，主角做出了新的决定，并在接下来的旅程中遇见了更特别的事情。"
    return f"随着“{user_text}”这个变化出现，故事自然向前推进。主角开始面对新的情境，而冒险也因此变得更加丰富。"


@tool
def ask_story_tool(user_text: str) -> str:
    """Explain or answer a question about the story without adding正文."""
    return f"关于“{user_text}”，可以这样理解：故事里的角色正在面对新的情境，所以它的反应和选择会受到情绪、环境和目标的影响。"


@tool
def adjust_story_tool(age: int, user_text: str) -> str:
    """Adjust story style or direction based on user request."""
    if age <= 6:
        return f"好的，我们把故事轻轻调整一下。根据“{user_text}”这个想法，新的内容会变得更温和、更容易理解。"
    if age <= 9:
        return f"好的，我们根据“{user_text}”来调整故事。这样故事会更贴近你的想法，也会更自然有趣。"
    return f"好的，基于“{user_text}”这个要求，故事将进行相应调整，使情节、角色或氛围更符合你的期待。"


@tool
def safety_redirect_tool() -> str:
    """Safely redirect unsafe content into child-friendly topics."""
    return "这个内容我不能这样继续哦。我们可以换一个更安全、也更有趣的方向，比如神奇动物、勇敢冒险或者搞笑故事。"


@tool
def end_chat_tool() -> str:
    """Gracefully close the conversation without continuing the story."""
    return "用户明确表示想结束对话。请温和收尾，不要继续生成新的故事正文，不要强行开启新情节。"