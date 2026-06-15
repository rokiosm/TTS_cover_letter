import argparse
import csv
import json
import os
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LABEL_DIR = ROOT / "DB" / "aihub_interview_labels"
DEFAULT_LABEL_DIR = Path(
    os.environ.get(
        "AIHUB_INTERVIEW_LABEL_DIR",
        LOCAL_LABEL_DIR,
    )
)
OUTPUT_CSV = ROOT / "Embedding" / "interview_question_contexts.csv"

ZIP_NAMES = [
    "TL_01.Management_Female_Experienced.zip",
    "TL_01.Management_Female_New.zip",
    "TL_01.Management_Male_Experienced.zip",
    "TL_01.Management_Male_New.zip",
    "TL_02.SalesMarketing_Female_Experienced.zip",
    "TL_02.SalesMarketing_Female_New.zip",
    "TL_02.SalesMarketing_Male_Experienced.zip",
    "TL_02.SalesMarketing_Male_New.zip",
    "TL_03.PublicService_Female_Experienced.zip",
    "TL_03.PublicService_Female_New.zip",
    "TL_03.PublicService_Male_Experienced.zip",
    "TL_03.PublicService_Male_New.zip",
    "TL_04.RND_Female_Experienced.zip",
    "TL_04.RND_Female_New.zip",
    "TL_04.RND_Male_Experienced.zip",
    "TL_04.RND_Male_New.zip",
    "TL_05.ICT_Female_Experienced.zip",
    "TL_05.ICT_Female_New.zip",
    "TL_05.ICT_Male_Experienced.zip",
    "TL_05.ICT_Male_New.zip",
    "TL_06.Design_Female_Experienced.zip",
    "TL_06.Design_Female_New.zip",
    "TL_06.Design_Male_Experienced.zip",
    "TL_06.Design_Male_New.zip",
    "TL_07.ProductionManufacturing_Female_Experienced.zip",
    "TL_07.ProductionManufacturing_Female_New.zip",
    "TL_07.ProductionManufacturing_Male_Experienced.zip",
    "TL_07.ProductionManufacturing_Male_New.zip",
]

OCCUPATION_LABELS = {
    "BM": "Management",
    "SM": "SalesMarketing",
    "PS": "PublicService",
    "RND": "RND",
    "ICT": "ICT",
    "ARD": "Design",
    "MM": "ProductionManufacturing",
}

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣+#.]+")


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def tokenize(text):
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token) > 1]


def zip_paths(label_dir=DEFAULT_LABEL_DIR):
    return [Path(label_dir) / name for name in ZIP_NAMES]


def parse_json_bytes(raw):
    text = raw.decode("utf-8-sig")
    try:
        return json.loads(text), "normal"
    except json.JSONDecodeError:
        return json.loads(text, strict=False), "strict_false"


def first_values(items, key):
    values = []
    for item in items or []:
        value = normalize_space(item.get(key, ""))
        if value and value not in values:
            values.append(value)
    return values


def row_from_json(zip_name, member_name, data):
    data_set = data.get("dataSet") or {}
    info = data_set.get("info") or {}
    question = data_set.get("question") or {}
    answer = data_set.get("answer") or {}
    raw_info = data.get("rawDataInfo") or {}

    occupation = info.get("occupation", "")
    question_text = normalize_space((question.get("raw") or {}).get("text", ""))
    answer_text = normalize_space((answer.get("raw") or {}).get("text", ""))
    summary = normalize_space((answer.get("summary") or {}).get("text", ""))
    intent_items = answer.get("intent") or []
    emotion_items = answer.get("emotion") or []
    intent_categories = first_values(intent_items, "category")
    intent_expressions = first_values(intent_items, "expression")
    emotion_categories = first_values(emotion_items, "category")
    emotion_expressions = first_values(emotion_items, "expression")

    context = " ".join(
        [
            OCCUPATION_LABELS.get(occupation, occupation),
            occupation,
            info.get("experience", ""),
            info.get("gender", ""),
            info.get("ageRange", ""),
            " ".join(intent_categories),
            " ".join(intent_expressions),
            " ".join(emotion_categories),
            question_text,
            summary,
            answer_text,
        ]
    )

    question_audio = raw_info.get("question") or {}
    answer_audio = raw_info.get("answer") or {}
    member_id = Path(member_name).stem
    return {
        "question_id": member_id,
        "source_zip": zip_name,
        "source_file": member_name.lstrip("/"),
        "date": info.get("date", ""),
        "occupation": occupation,
        "occupation_label": OCCUPATION_LABELS.get(occupation, occupation),
        "channel": info.get("channel", ""),
        "place": info.get("place", ""),
        "gender": info.get("gender", ""),
        "age_range": info.get("ageRange", ""),
        "experience": info.get("experience", ""),
        "question_text": question_text,
        "question_word_count": (question.get("raw") or {}).get("wordCount", ""),
        "answer": answer_text,
        "answer_word_count": (answer.get("raw") or {}).get("wordCount", ""),
        "summary": summary,
        "summary_word_count": (answer.get("summary") or {}).get("wordCount", ""),
        "intent_category": ", ".join(intent_categories),
        "intent_expression": ", ".join(intent_expressions),
        "emotion_category": ", ".join(emotion_categories),
        "emotion_expression": ", ".join(emotion_expressions),
        "question_audio_path": question_audio.get("audioPath", ""),
        "answer_audio_path": answer_audio.get("audioPath", ""),
        "answer_duration_ms": answer_audio.get("duration", ""),
        "tokens": " ".join(tokenize(context)),
        "context_300": normalize_space(context)[:300],
        "context_600": normalize_space(context)[:600],
        "context_1000": normalize_space(context)[:1000],
    }


def load_rows(label_dir=DEFAULT_LABEL_DIR, limit=0):
    rows = []
    errors = []
    parse_modes = {"normal": 0, "strict_false": 0, "failed": 0}
    for path in zip_paths(label_dir):
        if not path.exists():
            errors.append({"source_zip": path.name, "source_file": "", "error": "zip_not_found"})
            continue
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                try:
                    data, mode = parse_json_bytes(archive.read(member))
                    parse_modes[mode] = parse_modes.get(mode, 0) + 1
                    rows.append(row_from_json(path.name, member.filename, data))
                except Exception as exc:
                    parse_modes["failed"] = parse_modes.get("failed", 0) + 1
                    errors.append({"source_zip": path.name, "source_file": member.filename, "error": str(exc)})
                if limit and len(rows) >= limit:
                    return rows, errors, parse_modes
    return rows, errors, parse_modes


def dataset_status(label_dir=DEFAULT_LABEL_DIR):
    files = []
    total_members = 0
    total_bytes = 0
    missing = []
    for path in zip_paths(label_dir):
        if not path.exists():
            missing.append(path.name)
            continue
        with zipfile.ZipFile(path) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            file_size = sum(member.file_size for member in members)
        total_members += len(members)
        total_bytes += file_size
        files.append({"name": path.name, "count": len(members), "bytes": file_size})
    return {
        "label_dir": str(label_dir),
        "zip_count": len(files),
        "expected_zip_count": len(ZIP_NAMES),
        "json_count": total_members,
        "json_bytes": total_bytes,
        "missing_zips": missing,
        "files": files,
    }


def write_rows(rows, output_csv=OUTPUT_CSV):
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "question_id",
        "source_zip",
        "source_file",
        "date",
        "occupation",
        "occupation_label",
        "channel",
        "place",
        "gender",
        "age_range",
        "experience",
        "question_text",
        "question_word_count",
        "answer",
        "answer_word_count",
        "summary",
        "summary_word_count",
        "intent_category",
        "intent_expression",
        "emotion_category",
        "emotion_expression",
        "question_audio_path",
        "answer_audio_path",
        "answer_duration_ms",
        "tokens",
        "context_300",
        "context_600",
        "context_1000",
    ]
    with output_csv.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="AI Hub 채용면접 라벨 ZIP을 RAG용 CSV로 변환합니다.")
    parser.add_argument("--label-dir", default=str(DEFAULT_LABEL_DIR))
    parser.add_argument("--output", default=str(OUTPUT_CSV))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    label_dir = Path(args.label_dir)
    if args.status:
        print(json.dumps(dataset_status(label_dir), ensure_ascii=False, indent=2))
        return

    rows, errors, parse_modes = load_rows(label_dir, args.limit)
    write_rows(rows, Path(args.output))
    print(f"rows={len(rows)} errors={len(errors)} parse_modes={parse_modes} output={args.output}")
    if errors:
        print(json.dumps(errors[:10], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
