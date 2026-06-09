import os
import re

from dotenv import load_dotenv

from RAG.API.openai_generator import build_prompt, draft_payload, parse_json_output


DEFAULT_MODEL = "Qwen/Qwen3-14B"
DEFAULT_BASE_URL = "http://127.0.0.1:8001/v1"


def vllm_enabled(generation_options):
    generation_options = generation_options or {}
    return generation_options.get("provider") == "vllm" or bool(generation_options.get("use_vllm"))


def vllm_base_url(generation_options):
    load_dotenv()
    return (
        (generation_options or {}).get("base_url")
        or (generation_options or {}).get("openai_api_base")
        or os.getenv("VLLM_API_BASE")
        or DEFAULT_BASE_URL
    )


def strip_json_markdown(text):
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return fenced.group(1).strip() if fenced else text


def regenerate_with_vllm(serialized, generation_options):
    from langchain_openai import ChatOpenAI

    generation_options = generation_options or {}
    model = generation_options.get("model") or DEFAULT_MODEL
    base_url = vllm_base_url(generation_options)
    api_key = generation_options.get("api_key") or os.getenv("VLLM_API_KEY") or "EMPTY"
    temperature = float(generation_options.get("temperature", 0.2))
    max_tokens = int(generation_options.get("max_tokens", 4096))

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    response = llm.invoke(
        [
            (
                "system",
                "당신은 한국어 자기소개서 편집자입니다. 반드시 유효한 JSON만 출력하고 markdown 코드블록은 사용하지 마세요.",
            ),
            ("human", build_prompt(serialized, generation_options)),
        ]
    )
    generated = parse_json_output(strip_json_markdown(response.content))
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
        item["vllm_generated"] = True
        item["vllm_paragraphs"] = draft.count("\n\n") + 1 if draft else 0

    serialized["vllm"] = {
        "enabled": True,
        "model": model,
        "base_url": base_url,
    }
    serialized["generation_provider"] = "vllm"
    serialized["generation_draft_payload"] = draft_payload(serialized)
    return serialized
