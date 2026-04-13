from anthropic import Anthropic, AsyncAnthropic
from typing import List, Dict, AsyncGenerator

from app.config import get_settings


class ClaudeService:
    def __init__(self):
        settings = get_settings()
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.async_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-haiku-4-5-20251001"

    def _build_messages(
        self,
        user_message: str,
        context_docs: List[Dict[str, str]],
        chat_history: List[Dict[str, str]] = None
    ):
        context_text = "\n\n".join([
            f"[참고 자료 {i+1}]\n{doc['content']}"
            for i, doc in enumerate(context_docs)
        ]) if context_docs else "관련 참고 자료가 없습니다."

        system_prompt = f"""당신은 따뜻하고 공감적인 연애 상담사입니다.
사용자의 연애 고민을 진심으로 들어주고, 실질적인 조언을 제공해주세요.

다음 참고 자료들은 비슷한 상황의 사람들의 경험과 조언입니다.
이를 참고하되, 사용자의 상황에 맞게 개인화된 답변을 해주세요.

<참고자료>
{context_text}
</참고자료>

가이드라인:
- 먼저 사용자의 감정에 공감해주세요
- 판단하지 말고 이해하는 자세로 대화해주세요
- 구체적이고 실행 가능한 조언을 제공해주세요
- 필요한 경우 추가 질문을 통해 상황을 더 잘 이해하세요
- 한국어로 자연스럽게 대화해주세요"""

        messages = []
        if chat_history:
            for msg in chat_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        return system_prompt, messages

    async def stream_response(
        self,
        user_message: str,
        context_docs: List[Dict[str, str]],
        chat_history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """SSE 스트리밍 응답 생성"""
        system_prompt, messages = self._build_messages(user_message, context_docs, chat_history)

        async with self.async_client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def generate_response(
        self,
        user_message: str,
        context_docs: List[Dict[str, str]],
        chat_history: List[Dict[str, str]] = None
    ) -> str:
        """연애 상담 응답 생성

        Args:
            user_message: 사용자 메시지
            context_docs: RAG로 검색된 관련 문서들
            chat_history: 이전 대화 기록

        Returns:
            Claude의 응답
        """
        system_prompt, messages = self._build_messages(user_message, context_docs, chat_history)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text


# 싱글톤 인스턴스
_claude_service = None


def get_claude_service() -> ClaudeService:
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
