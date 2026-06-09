import argparse
import copy
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from RAG.API.run_json import read_json, run_from_payload, write_json


DEFAULT_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash-lite"]
DEFAULT_TEMPERATURES = [0.1, 0.3]
DEFAULT_MAX_TOKENS = [2048, 4096]


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def tokenize(text):
    return re.findall(r"[A-Za-z0-9가-힣+#.]+", text or "")


def split_sentences(text):
    text = normalize_space(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s+|(?<=요\.)\s+", text)
    return [part.strip() for part in parts if part.strip()]


def score_draft(draft):
    text = draft.get("draft", "")
    question = draft.get("question", "")
    evidence_items = draft.get("evidence_items", [])
    chars = len(text)
    paragraphs = text.count("\n\n") + 1 if text else 0
    question_tokens = set(tokenize(question))
    answer_tokens = set(tokenize(text))
    overlap = len(question_tokens & answer_tokens)
    evidence_hits = 0
    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            continue
        evidence_text = evidence.get("text", "")
        if evidence_text and evidence_text[:12] in text:
            evidence_hits += 1
    structure_hits = sum(keyword in text for keyword in ["경험", "역할", "문제", "행동", "결과", "기여", "입사 후"])
    char_score = 1.0 if 1000 <= chars <= 1500 else max(0.0, 1 - abs(chars - 1250) / 1250)
    paragraph_score = 1.0 if paragraphs == 3 else 0.5 if 2 <= paragraphs <= 4 else 0.0
    relevance_score = min(1.0, overlap / 6) if question_tokens else 0.0
    evidence_score = min(1.0, evidence_hits / max(1, len(evidence_items)))
    structure_score = min(1.0, structure_hits / 5)
    composite = round(
        char_score * 0.2
        + paragraph_score * 0.15
        + relevance_score * 0.25
        + evidence_score * 0.25
        + structure_score * 0.15,
        4,
    )
    return {
        "index": draft.get("index"),
        "label": draft.get("label"),
        "chars": chars,
        "paragraphs": paragraphs,
        "sentences": len(split_sentences(text)),
        "question_token_overlap": overlap,
        "evidence_hits": evidence_hits,
        "evidence_count": len(evidence_items),
        "structure_hits": structure_hits,
        "composite_score": composite,
    }


def run_experiments(payload, models, temperatures, max_tokens_values, min_chars=None, max_chars=None, draft_limit=0, timeout=90):
    rows = []
    outputs = []
    for model in models:
        for temperature in temperatures:
            for max_tokens in max_tokens_values:
                case_payload = copy.deepcopy(payload)
                generation = case_payload.setdefault("generation", {})
                generation["provider"] = generation.get("provider") or "gemini"
                generation["use_gemini"] = generation.get("provider") == "gemini"
                generation["model"] = model
                generation["temperature"] = temperature
                generation["max_tokens"] = max_tokens
                generation["timeout"] = timeout
                if min_chars is not None:
                    generation["min_chars"] = min_chars
                if max_chars is not None:
                    generation["max_chars"] = max_chars
                if draft_limit:
                    generation["draft_limit"] = draft_limit
                try:
                    output = run_from_payload(case_payload)
                    scores = [score_draft(draft) for draft in output.get("drafts", [])]
                    generated_scores = [
                        score
                        for score, draft in zip(scores, output.get("drafts", []))
                        if draft.get("gemini_generated")
                    ]
                    average = round(sum(score["composite_score"] for score in scores) / max(1, len(scores)), 4)
                    generated_average = round(
                        sum(score["composite_score"] for score in generated_scores) / max(1, len(generated_scores)),
                        4,
                    )
                    gemini = output.get("gemini", {})
                    row = {
                        "provider": generation.get("provider", ""),
                        "model": generation.get("model", ""),
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "success": True,
                        "average_composite_score": average,
                        "generated_average_composite_score": generated_average,
                        "generated_count": gemini.get("success_count", 0),
                        "attempted_count": gemini.get("attempted_count", 0),
                        "error_count": gemini.get("error_count", 0),
                        "errors": gemini.get("errors", []),
                        "draft_scores": scores,
                    }
                    outputs.append(
                        {
                            "model": model,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "output": output,
                        }
                    )
                except Exception as exc:
                    row = {
                        "provider": generation.get("provider", ""),
                        "model": generation.get("model", ""),
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "success": False,
                        "average_composite_score": 0,
                        "generated_average_composite_score": 0,
                        "generated_count": 0,
                        "attempted_count": draft_limit or 5,
                        "error_count": draft_limit or 5,
                        "error_type": exc.__class__.__name__,
                        "message": str(exc)[:700],
                        "draft_scores": [],
                    }
                    outputs.append(
                        {
                            "model": model,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "error": row,
                        }
                    )
                rows.append(row)
    rows.sort(key=lambda item: (item.get("generated_count", 0), item["generated_average_composite_score"]), reverse=True)
    return {"summary": rows, "outputs": outputs}


def svg_escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_svg(summary, path):
    width = 1100
    row_height = 82
    top = 120
    left = 260
    chart_width = 650
    height = top + max(1, len(summary)) * row_height + 90
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f4ee"/>',
        '<text x="48" y="54" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#1f2933">Gemini Generation Experiment</text>',
        '<text x="48" y="84" font-family="Arial, sans-serif" font-size="14" fill="#52606d">Composite score: length range, paragraph count, question overlap, evidence usage, structure keywords. Failed API calls are shown in red.</text>',
        f'<line x1="{left}" y1="{top - 24}" x2="{left + chart_width}" y2="{top - 24}" stroke="#c7c1b6"/>',
    ]
    for index, item in enumerate(summary):
        y = top + index * row_height
        score = float(item.get("generated_average_composite_score") or item.get("average_composite_score") or 0)
        bar_width = int(chart_width * score)
        success = bool(item.get("generated_count", 0))
        color = "#2f7d6d" if success else "#b42318"
        label = f"{item.get('model')} / T={item.get('temperature')} / max={item.get('max_tokens')}"
        status = f"generated {item.get('generated_count', 0)}/{item.get('attempted_count', 0)} · errors {item.get('error_count', 0)}"
        message = item.get("message", "")
        if not message and item.get("errors"):
            message = item["errors"][0].get("message", "")
        if len(message) > 105:
            message = message[:102] + "..."
        lines.extend(
            [
                f'<text x="48" y="{y + 18}" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="#1f2933">{svg_escape(label)}</text>',
                f'<text x="48" y="{y + 42}" font-family="Arial, sans-serif" font-size="13" fill="{color}">{svg_escape(status)}</text>',
                f'<rect x="{left}" y="{y}" width="{chart_width}" height="30" rx="4" fill="#e4ded4"/>',
                f'<rect x="{left}" y="{y}" width="{bar_width}" height="30" rx="4" fill="{color}"/>',
                f'<text x="{left + chart_width + 18}" y="{y + 21}" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#1f2933">{score:.3f}</text>',
            ]
        )
        if message:
            lines.append(
                f'<text x="{left}" y="{y + 55}" font-family="Arial, sans-serif" font-size="12" fill="#697586">{svg_escape(message)}</text>'
            )
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_float_list(value):
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def parse_int_list(value):
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_args():
    parser = argparse.ArgumentParser(description="Run generation parameter experiments.")
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parent / "input_template.json")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "generation_experiment_output.json")
    parser.add_argument("--svg-output", type=Path, default=Path(__file__).resolve().parents[1] / "visualation" / "gemini_generation_experiment.svg")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--temperatures", default=",".join(str(value) for value in DEFAULT_TEMPERATURES))
    parser.add_argument("--max-tokens", default=",".join(str(value) for value in DEFAULT_MAX_TOKENS))
    parser.add_argument("--min-chars", type=int, default=450)
    parser.add_argument("--max-chars", type=int, default=800)
    parser.add_argument("--draft-limit", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=90)
    return parser.parse_args()


def main():
    args = parse_args()
    payload = read_json(args.input)
    result = run_experiments(
        payload,
        [item.strip() for item in args.models.split(",") if item.strip()],
        parse_float_list(args.temperatures),
        parse_int_list(args.max_tokens),
        args.min_chars,
        args.max_chars,
        args.draft_limit,
        args.timeout,
    )
    write_json(args.output, result)
    write_svg(result["summary"], args.svg_output)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"svg={args.svg_output}")


if __name__ == "__main__":
    main()
