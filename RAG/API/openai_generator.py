import json
import os

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_MODEL = "gpt-5.2"


def openai_enabled(generation_options):
    return bool((generation_options or {}).get("use_openai"))


def ensure_api_key():
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY가 없습니다. 프로젝트 루트의 .env 파일에 OPENAI_API_KEY=sk-... 형태로 저장하세요."
        )


def draft_payload(serialized):
    return [
        {
            "index": item.get("index"),
            "question": item.get("question"),
            "label": item.get("label"),
            "evidence_status": item.get("evidence_status"),
            "evidence_items": item.get("evidence_items", []),
            "reference_examples": item.get("reference_examples", []),
            "local_draft": item.get("draft", ""),
        }
        for item in serialized.get("drafts", [])
    ]


def build_prompt(serialized, generation_options):
    api_input = serialized.get("api_input", {})
    structured_profile = api_input.get("structured_profile", {})
    min_chars = int(generation_options.get("min_chars", 1000))
    max_chars = int(generation_options.get("max_chars", 1500))
    paragraphs = int(generation_options.get("paragraphs", 3))

    instructions = {
        "role": "cover_letter_editor",
        "language": "ko",
        "json_output_required": True,
        "output_format": "json",
        "target_company": api_input.get("target_company", ""),
        "target_job": api_input.get("target_job", ""),
        "output_style": generation_options.get("output_style", "자기소개서 문체"),
        "rules": [
            "각 답변은 반드시 공통질문의 표현과 요구사항을 우선적으로 사용한다.",
            f"각 답변은 {paragraphs}문단으로 작성한다.",
            f"각 답변은 최소 {min_chars}자, 최대 {max_chars}자 사이로 작성한다.",
            "스펙은 뭉뚱그리지 말고 학과/전공, 자격증, 팀프로젝트, 기타 스펙을 문항에 맞게 분리해 사용한다.",
            "팀/협업 문항에는 자격증이나 전공만으로 답하지 말고 팀프로젝트 경험을 우선 사용한다.",
            "나이와 성별은 면접 데이터셋 비교용 선택값이므로 자기소개서 본문에는 직접 반영하지 않는다.",
            "기존 합격자 문장은 그대로 복사하지 말고 구조와 논리만 참고한다.",
            "답변은 실제 자기소개서처럼 자연스럽고 유기적으로 연결한다.",
        ],
        "structured_profile": structured_profile,
        "drafts": draft_payload(serialized),
        "response_schema": {
            "drafts": [
                {
                    "index": "number",
                    "question": "string",
                    "label": "string",
                    "draft": "string",
                    "draft_chars": "number",
                    "paragraphs": "number",
                }
            ]
        },
    }
    return json.dumps(instructions, ensure_ascii=False, indent=2)


def parse_json_output(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM 응답이 JSON 형식이 아닙니다: {exc}") from exc


def regenerate_with_openai(serialized, generation_options):
    ensure_api_key()
    model = generation_options.get("model") or DEFAULT_MODEL
    client = OpenAI()
    response = client.responses.create(
        model=model,
        instructions=(
            "당신은 한국어 자기소개서 편집자입니다. "
            "반드시 유효한 JSON만 출력하고, markdown 코드블록은 사용하지 마세요."
        ),
        input=build_prompt(serialized, generation_options),
        text={"format": {"type": "json_object"}},
    )
    generated = parse_json_output(response.output_text)
    drafts_by_index = {
        int(item.get("index")): item
        for item in generated.get("drafts", [])
        if isinstance(item, dict) and item.get("index") is not None
    }

    for item in serialized.get("drafts", []):
        replacement = drafts_by_index.get(int(item.get("index", 0)))
        if not replacement:
            continue
        draft = replacement.get("draft", "")
        item["local_draft"] = item.get("draft", "")
        item["draft"] = draft
        item["draft_chars"] = len(draft)
        item["openai_generated"] = True
        item["openai_paragraphs"] = draft.count("\n\n") + 1 if draft else 0

    serialized["openai"] = {
        "enabled": True,
        "model": model,
        "response_id": getattr(response, "id", ""),
    }
    return serialized
