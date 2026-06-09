import os
import re
import time

import requests
from dotenv import load_dotenv

from RAG.API.openai_generator import draft_payload, parse_json_output


DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta"
DISABLED_UNTIL = 0
DISABLED_REASON = ""


def gemini_enabled(generation_options):
    generation_options = generation_options or {}
    return generation_options.get("provider") == "gemini" or bool(generation_options.get("use_gemini"))


def ensure_api_key(generation_options):
    load_dotenv()
    api_key = (generation_options or {}).get("api_key") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 없습니다. .env에 GEMINI_API_KEY=... 형태로 저장하거나 generation.api_key를 넘기세요.")
    return api_key


def strip_json_markdown(text):
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return fenced.group(1).strip() if fenced else text


def extract_text(payload):
    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini 응답에 candidates가 없습니다: {payload}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts)
    if not text:
        raise RuntimeError(f"Gemini 응답에서 text를 찾지 못했습니다: {payload}")
    return text


def first_finish_reason(payload):
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    return candidates[0].get("finishReason", "")


def retry_delay_seconds(text, fallback):
    match = re.search(r"retry in ([0-9.]+)s", text or "", re.IGNORECASE)
    if match:
        return min(float(match.group(1)) + 1, 90)
    return fallback


def friendly_error_message(message):
    if "429" in message or "RESOURCE_EXHAUSTED" in message or "Quota exceeded" in message:
        return "Gemini 무료 요청 한도를 초과했습니다. 잠시 후 다시 시도하거나 현재 로컬 RAG 초안을 사용하세요."
    if "503" in message or "high demand" in message or "UNAVAILABLE" in message:
        return "Gemini 서버가 혼잡합니다. 잠시 후 다시 시도하면 됩니다. 현재 결과는 로컬 RAG 초안입니다."
    if "JSON" in message or "Unterminated string" in message:
        return "Gemini 응답 JSON이 완성되지 않았습니다. 현재 결과는 로컬 RAG 초안입니다."
    return message[:220]


def is_quota_error(message):
    return "429" in message or "RESOURCE_EXHAUSTED" in message or "Quota exceeded" in message


def mark_local_fallback(serialized, model, temperature, max_tokens, reason):
    for item in serialized.get("drafts", []):
        item["gemini_generated"] = False
        item["generation_fallback"] = "local_rag"
    serialized["gemini"] = {
        "enabled": False,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "success_count": 0,
        "error_count": 0,
        "attempted_count": 0,
        "fallback_to_local": True,
        "fallback_reason": reason,
        "errors": [],
    }
    serialized["generation_provider"] = "local_rag"
    serialized["generation_draft_payload"] = draft_payload(serialized)
    return serialized


def build_single_draft_prompt(serialized, draft, generation_options):
    api_input = serialized.get("api_input", {})
    min_chars = int(generation_options.get("min_chars", 1000))
    max_chars = int(generation_options.get("max_chars", 1500))
    paragraphs = int(generation_options.get("paragraphs", 3))
    payload = {
        "role": "cover_letter_editor",
        "language": "ko",
        "target_company": api_input.get("target_company", ""),
        "target_job": api_input.get("target_job", ""),
        "output_style": generation_options.get("output_style", "자기소개서 문체"),
        "rules": [
            "반드시 이 문항 하나에만 답한다.",
            f"답변은 {paragraphs}문단으로 작성한다.",
            f"답변은 최소 {min_chars}자, 최대 {max_chars}자 사이로 작성한다.",
            "스펙은 문항에 맞는 근거만 선택해 사용한다.",
            "팀/협업 문항에는 팀프로젝트 경험을 우선 사용한다.",
            "나이와 성별은 자기소개서 본문에 직접 반영하지 않는다.",
            "합격자 문장은 그대로 복사하지 말고 구조와 논리만 참고한다.",
            "실제 자기소개서처럼 자연스럽게 작성한다.",
        ],
        "structured_profile": api_input.get("structured_profile", {}),
        "draft": {
            "index": draft.get("index"),
            "question": draft.get("question"),
            "label": draft.get("label"),
            "evidence_status": draft.get("evidence_status"),
            "evidence_items": draft.get("evidence_items", []),
            "reference_examples": draft.get("reference_examples", []),
            "local_draft": draft.get("draft", ""),
        },
        "response_schema": {
            "index": "number",
            "question": "string",
            "label": "string",
            "draft": "string",
            "draft_chars": "number",
            "paragraphs": "number",
        },
    }
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)


def regenerate_with_gemini(serialized, generation_options):
    global DISABLED_UNTIL, DISABLED_REASON
    generation_options = generation_options or {}
    api_key = ensure_api_key(generation_options)
    model = generation_options.get("model") or DEFAULT_MODEL
    endpoint = generation_options.get("endpoint") or os.getenv("GEMINI_API_ENDPOINT") or DEFAULT_ENDPOINT
    temperature = float(generation_options.get("temperature", 0.2))
    max_tokens = int(generation_options.get("max_tokens", 4096))
    now = time.time()
    if DISABLED_UNTIL > now:
        return mark_local_fallback(
            serialized,
            model,
            temperature,
            max_tokens,
            DISABLED_REASON or "Gemini 요청 제한으로 기존 로컬 RAG 생성 방식을 사용합니다.",
        )

    url = f"{endpoint.rstrip('/')}/models/{model}:generateContent"
    timeout = int(generation_options.get("timeout", 120))
    retries = int(generation_options.get("retries", 2))
    successes = 0
    errors = []
    draft_limit = int(generation_options.get("draft_limit") or 0)
    drafts = serialized.get("drafts", [])
    if draft_limit:
        drafts = drafts[:draft_limit]
    for draft_position, item in enumerate(drafts):
        request_payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": "당신은 한국어 자기소개서 편집자입니다. 반드시 유효한 JSON만 출력하고 markdown 코드블록은 사용하지 마세요."
                    }
                ]
            },
            "contents": [{"role": "user", "parts": [{"text": build_single_draft_prompt(serialized, item, generation_options)}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "question": {"type": "string"},
                        "label": {"type": "string"},
                        "draft": {"type": "string"},
                        "draft_chars": {"type": "integer"},
                        "paragraphs": {"type": "integer"},
                    },
                    "required": ["index", "question", "label", "draft"],
                },
            },
        }
        try:
            response_payload = None
            last_error = None
            for attempt in range(retries + 1):
                response = requests.post(
                    url,
                    headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                    json=request_payload,
                    timeout=timeout,
                )
                if response.status_code < 400:
                    response_payload = response.json()
                    break
                last_error = f"Gemini API 오류 {response.status_code}: {response.text[:1000]}"
                if response.status_code not in {429, 503} or attempt >= retries:
                    raise RuntimeError(last_error)
                time.sleep(retry_delay_seconds(response.text, 8 * (attempt + 1)))
            if response_payload is None:
                raise RuntimeError(last_error or "Gemini API 응답이 없습니다.")
            replacement = parse_json_output(strip_json_markdown(extract_text(response_payload)))
            draft = replacement.get("draft", "")
            item["local_draft"] = item.get("draft", "")
            item["draft"] = draft
            item["draft_chars"] = len(draft)
            item["gemini_generated"] = True
            item["gemini_paragraphs"] = draft.count("\n\n") + 1 if draft else 0
            item["gemini_finish_reason"] = first_finish_reason(response_payload)
            successes += 1
        except Exception as exc:
            item["gemini_generated"] = False
            raw_error = str(exc)
            friendly_error = friendly_error_message(raw_error)
            item["gemini_error"] = friendly_error
            errors.append({"index": item.get("index"), "message": friendly_error})
            if is_quota_error(raw_error):
                wait_seconds = retry_delay_seconds(raw_error, 60)
                DISABLED_UNTIL = time.time() + wait_seconds
                DISABLED_REASON = "Gemini 무료 요청 한도를 초과해 기존 로컬 RAG 생성 방식을 사용합니다."
                for remaining in drafts[draft_position + 1 :]:
                    remaining["gemini_generated"] = False
                    remaining["generation_fallback"] = "local_rag"
                for draft in serialized.get("drafts", []):
                    draft.pop("gemini_error", None)
                    draft["generation_fallback"] = "local_rag"
                return mark_local_fallback(serialized, model, temperature, max_tokens, DISABLED_REASON)

    serialized["gemini"] = {
        "enabled": True,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "success_count": successes,
        "error_count": len(errors),
        "attempted_count": len(drafts),
        "fallback_to_local": successes == 0 and bool(errors),
        "fallback_reason": "Gemini 생성이 실패해 기존 로컬 RAG 생성 방식을 사용합니다." if successes == 0 and errors else "",
        "errors": errors,
    }
    serialized["generation_provider"] = "gemini"
    serialized["generation_draft_payload"] = draft_payload(serialized)
    return serialized
