import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from RAG import cover_letter_rag
from RAG.API.openai_generator import openai_enabled, regenerate_with_openai


DEFAULT_INPUT = Path(__file__).resolve().parent / "input_template.json"


def read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def run_from_payload(payload):
    generation_options = payload.get("generation", {})
    output = cover_letter_rag.run_rag(
        large=payload.get("large", ""),
        medium=payload.get("medium", ""),
        small=payload.get("small", ""),
        job_keyword=payload.get("job_keyword", ""),
        query=payload.get("query", ""),
        top_k=int(payload.get("top_k", 8)),
        target_company=payload.get("target_company", ""),
        target_job=payload.get("target_job", ""),
        user_profile=payload.get("user_profile", ""),
        structured_profile=payload.get("structured_profile", {}),
    )
    serialized = cover_letter_rag.serialize_rag_output(output)
    serialized["generation_request"] = generation_options
    serialized["api_input"] = payload
    if openai_enabled(generation_options):
        serialized = regenerate_with_openai(serialized, generation_options)
    return serialized


def compact_summary(serialized):
    return {
        "target_job": serialized.get("api_input", {}).get("target_job", ""),
        "retrieved_count": serialized.get("retrieved_count", 0),
        "questions": [item["question"] for item in serialized.get("questions", [])],
        "drafts": [
            {
                "index": item.get("index"),
                "label": item.get("label"),
                "draft_chars": item.get("draft_chars"),
                "paragraphs": item.get("draft", "").count("\n\n") + 1 if item.get("draft") else 0,
                "openai_generated": item.get("openai_generated", False),
                "evidence_fields": [
                    evidence.get("field_label", "스펙") if isinstance(evidence, dict) else "스펙"
                    for evidence in item.get("evidence_items", [])
                ],
                "reference_count": len(item.get("reference_examples", [])),
            }
            for item in serialized.get("drafts", [])
        ],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Run cover-letter RAG from a JSON input file.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="JSON input file.")
    parser.add_argument("--output", type=Path, default=None, help="Optional output JSON file.")
    parser.add_argument("--summary", action="store_true", help="Print a compact summary instead of the full output.")
    return parser.parse_args()


def main():
    args = parse_args()
    payload = read_json(args.input)
    try:
        serialized = run_from_payload(payload)
        if args.output:
            write_json(args.output, serialized)
        print(json.dumps(compact_summary(serialized) if args.summary else serialized, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": exc.__class__.__name__,
                    "message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
