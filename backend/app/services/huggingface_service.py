from typing import List, Dict, Generator
from huggingface_hub import InferenceClient
import traceback
import re

from app.config import get_settings

class HuggingFaceService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.huggingface_api_key or None
        
        # 1순위 메인 모델 (성능 중심)
        self.primary_model = "Qwen/Qwen2.5-14B-Instruct"
        # 2순위 대체 모델 (안정성 중심)
        self.fallback_model = "google/gemma-2-9b-it"
        
        self.primary_client = InferenceClient(model=self.primary_model, token=self.api_key,timeout=120.0  )# 120초 대기
        self.fallback_client = InferenceClient(model=self.fallback_model, token=self.api_key,timeout=120.0 ) # 120초 대기

    def generate_response(
        self,
        user_message: str,
        context_docs: List[Dict[str, str]],
        chat_history: List[Dict[str, str]] = None
    ) -> str:
        messages = self._build_messages(user_message, context_docs, chat_history)

        try:
            print(f"[{self.primary_model}]로 생성을 시도합니다...")
            return self._call_model(self.primary_client, messages)
        except Exception as e:
            print(f"⚠️ [PRIMARY 오류] {self.primary_model} 실패: {str(e)}")
            print(f"[{self.fallback_model}]로 Fallback 시도합니다...")
            try:
                return self._call_model(self.fallback_client, messages)
            except Exception as e2:
                print(f"🚨 [FALLBACK 오류] {self.fallback_model} 실패: {str(e2)}")
                traceback.print_exc()
                raise Exception("모든 LLM 모델 응답에 실패했습니다.")

    def _build_messages(
        self,
        user_message: str,
        context_docs: List[Dict[str, str]],
        chat_history: List[Dict[str, str]] = None
    ) -> List[Dict[str, str]]:
        if context_docs:
            context_text = "\n\n".join([
                f"[사례 {i+1}]\n{doc['content']}"
                for i, doc in enumerate(context_docs)
            ])
            context_section = f"""
아래는 비슷한 상황을 겪은 사람들의 실제 사례입니다.
사례를 그대로 인용하지 말고, 핵심 인사이트만 참고해서 사용자에게 맞는 조언을 직접 만들어 주세요.

<사례 참고>
{context_text}
</사례 참고>
"""
        else:
            context_section = ""

        system_prompt = f"""너는 연애 고민을 들어주는 따뜻한 친구야.

말투 규칙 (반드시 지켜):
- 마크다운 절대 사용 금지. *, **, #, -, 번호 목록 전부 쓰지 마.
- 자연스러운 대화체로만 써. 마치 카톡으로 친한 친구한테 답장하는 것처럼.
- 딱딱한 "첫째, 둘째" "우선, 또한" 같은 나열식 구조 쓰지 마.
- 문단은 2~3개 이내로 짧게. 각 문단 사이에 줄바꿈 하나만.
- 이모지는 쓰지 마.

상담 방식:
- 먼저 상대방 감정에 공감해줘. 판단하지 말고.
- 상황을 보고 현실적인 조언을 편하게 얘기해줘.
- 필요하면 질문 하나 던져서 더 얘기 나눠봐.
- 사례가 있으면 내용을 그대로 쓰지 말고 네 말로 녹여서 전달해.
{context_section}"""

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            # 직전 1쌍(user+assistant)만 포함 — 이전 답변이 너무 많이 반영되면 같은 답변을 반복함
            for msg in chat_history[-2:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
        return messages

    def _clean_response(self, text: str) -> str:
        """마크다운 제거 후처리"""
        # 볼드/이탤릭 제거 (**text**, *text*, ***text***)
        text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}', r'\1', text)
        # 남은 단독 * 제거
        text = re.sub(r'\*+', '', text)
        # 헤더 제거 (# 제목)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # 불릿 리스트 제거 (- 항목)
        text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE)
        # 숫자 목록 제거 (1. 2. 3.)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        # 3줄 이상 빈 줄 → 2줄로
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _call_model(self, client: InferenceClient, messages: List[Dict[str, str]]):
        response = client.chat_completion(
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )
        return self._clean_response(response.choices[0].message.content)

    def stream_response(
        self,
        user_message: str,
        context_docs: List[Dict[str, str]],
        chat_history: List[Dict[str, str]] = None
    ) -> Generator[str, None, None]:
        """전체 응답 수집 후 마크다운 제거 → 단어 단위 스트리밍"""
        messages = self._build_messages(user_message, context_docs, chat_history)

        def _collect(client: InferenceClient) -> str:
            full = ""
            for chunk in client.chat_completion(
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
                stream=True
            ):
                if not chunk.choices:
                    continue
                token = chunk.choices[0].delta.content
                if token:
                    full += token
            return full

        try:
            print(f"[{self.primary_model}] 생성 중...")
            raw = _collect(self.primary_client)
        except Exception as e:
            print(f"[PRIMARY 오류] {self.primary_model}: {e}")
            print(f"[{self.fallback_model}] Fallback...")
            try:
                raw = _collect(self.fallback_client)
            except Exception as e2:
                print(f"[FALLBACK 오류] {self.fallback_model}: {e2}")
                traceback.print_exc()
                raise Exception("모든 LLM 모델 스트리밍에 실패했습니다.")

        cleaned = self._clean_response(raw)
        # 단어 단위로 나눠서 yield (스트리밍 효과 유지)
        words = cleaned.split(' ')
        for i, word in enumerate(words):
            yield word if i == len(words) - 1 else word + ' '


_hf_service = None

def get_huggingface_service() -> HuggingFaceService:
    global _hf_service
    if _hf_service is None:
        _hf_service = HuggingFaceService()
    return _hf_service
