"""占位脚本：后续可在此接入真实工具链。"""

def run(context: dict) -> dict:
    return {
        "skill": "content-agent",
        "status": "ready",
        "message": "Content skill UI 已接入，工具逻辑待补充。",
        "context": context,
    }
