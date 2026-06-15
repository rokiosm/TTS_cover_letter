import json
import os

from openai import OpenAI

from RAG.env_utils import load_env_file
from RAG.prompt_policy import COVER_LETTER_SYSTEM_ROLE, cover_letter_rules

DEFAULT_MODEL = "gpt-5.2"


def openai_enabled(generation_options):
    generation_options = generation_options or {}
    return generation_options.get("provider") in {"openai", "auto"} or bool(generation_options.get("use_openai"))


def ensure_api_key(generation_options=None):
    load_env_file()
    api_key = (generation_options or {}).get("openai_api_key") or (generation_options or {}).get("api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 없습니다. 프로젝트 루트의 .env 파일에 OPENAI_API_KEY=sk-... 형태로 저장하세요."
        )
    return api_key


def draft_payload(serialized, draft_limit=0):
    payload = [
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
        if item.get("evidence_status") == "matched" and item.get("draft_type") != "needs_input"
    ]
    return payload[:draft_limit] if draft_limit else payload


def evidence_labels(evidence_items):
    labels = []
    for evidence in evidence_items or []:
        if isinstance(evidence, dict):
            field = evidence.get("field_label") or "스펙"
            text = evidence.get("text") or ""
            if text:
                labels.append(f"{field}: {text}")
        elif evidence:
            labels.append(str(evidence))
    return labels


def apply_replacement_metadata(item, replacement):
    applied = replacement.get("applied_evidence")
    if not isinstance(applied, list):
        applied = evidence_labels(item.get("evidence_items", []))
    missing = replacement.get("missing_information")
    if isinstance(missing, str):
        missing = [missing] if missing.strip() else []
    if not isinstance(missing, list):
        missing = []
    item["applied_evidence"] = [str(value) for value in applied if str(value).strip()]
    item["missing_information"] = [str(value) for value in missing if str(value).strip()]


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
        "rules": cover_letter_rules([
            "각 답변은 반드시 공통질문의 표현과 요구사항을 우선적으로 사용한다.",
            f"각 답변은 {paragraphs}문단으로 작성한다.",
            f"각 답변은 최소 {min_chars}자, 최대 {max_chars}자 사이로 작성한다.",
            "draft 본문에는 자기소개서 답변만 작성한다.",
            "applied_evidence에는 실제로 draft 작성에 사용한 evidence_items만 짧게 적는다.",
            "missing_information에는 작성에 부족했던 정보만 적고, 부족한 정보가 없으면 빈 배열로 둔다.",
            "applied_evidence와 missing_information 내용을 draft 본문에 반복하지 않는다.",
            "각 문항마다 evidence_items 중 직무와 문항에 가장 맞는 2개만 골라 본문에 사용한다.",
            "선택한 2개 스펙은 어떤 활동이었는지, 그 활동을 직무에 맞게 어떻게 발전시켰는지, 무엇을 배웠는지를 문단 안에서 자연스럽게 풀어 쓴다.",
            "학과에서는, 자격증에서는, 기타 스펙에서는 같은 필드 나열 문장을 절대 쓰지 않는다.",
            "자격증과 어학 점수는 문항에 직접 답하는 핵심 경험이 아니면 본문에서 제외한다.",
            "사용자가 직접 쓴 문장이나 저장된 합격 자소서의 전개 방식을 우선 참고해 실제 자소서 문체로 작성한다.",
            "스펙은 문항에 맞는 행동, 판단, 결과로 풀어 쓸 수 있을 때만 사용한다.",
            "팀/협업 문항에는 자격증이나 전공만으로 답하지 말고 팀프로젝트 경험을 우선 사용한다.",
            "나이와 성별은 면접 데이터셋 비교용 선택값이므로 자기소개서 본문에는 직접 반영하지 않는다.",
            "기존 합격자 문장은 그대로 복사하지 말고 구조와 논리만 참고한다.",
            "답변은 실제 자기소개서처럼 자연스럽고 유기적으로 연결한다.",
        ]),
        "structured_profile": structured_profile,
        "drafts": draft_payload(serialized, int(generation_options.get("draft_limit") or 0)),
        "response_schema": {
            "drafts": [
                {
                    "index": "number",
                    "question": "string",
                    "label": "string",
                    "draft": "string",
                    "draft_chars": "number",
                    "paragraphs": "number",
                    "applied_evidence": ["string"],
                    "missing_information": ["string"],
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
    payload = draft_payload(serialized, int(generation_options.get("draft_limit") or 0))
    if not payload:
        serialized["openai"] = {
            "enabled": False,
            "model": generation_options.get("openai_model") or generation_options.get("model") or DEFAULT_MODEL,
            "success_count": 0,
            "attempted_count": 0,
            "fallback_to_next": True,
            "fallback_reason": "문항에 직접 연결되는 근거가 없어 OpenAI 생성을 건너뛰었습니다.",
        }
        return serialized

    api_key = ensure_api_key(generation_options)
    model = generation_options.get("openai_model") or generation_options.get("model") or DEFAULT_MODEL
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=(
            f"{COVER_LETTER_SYSTEM_ROLE} "
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
        apply_replacement_metadata(item, replacement)
        item["openai_generated"] = True
        item["openai_paragraphs"] = draft.count("\n\n") + 1 if draft else 0

    success_count = len([item for item in serialized.get("drafts", []) if item.get("openai_generated")])
    serialized["openai"] = {
        "enabled": True,
        "model": model,
        "response_id": getattr(response, "id", ""),
        "success_count": success_count,
        "attempted_count": len(payload),
        "fallback_to_next": success_count == 0,
        "fallback_reason": "OpenAI 응답에 적용 가능한 초안이 없어 다음 생성기로 전환합니다." if success_count == 0 else "",
    }
    serialized["generation_provider"] = "openai"
    serialized["generation_draft_payload"] = draft_payload(serialized)
    return serialized
