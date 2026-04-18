"""智能体基类"""

from abc import ABC, abstractmethod
from app.services.local_ai import LocalAI


class BaseAgent(ABC):
    def __init__(self):
        self.ai = LocalAI()
        self.name = self.__class__.__name__

    @abstractmethod
    async def run(self, **kwargs):
        pass

    async def think(self, system_prompt: str, user_prompt: str) -> str:
        """调用本地规则引擎进行结构化分析"""
        return await self.ai.analyze(system_prompt, user_prompt)
