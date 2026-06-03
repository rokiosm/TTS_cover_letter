import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = ROOT / "linkareer_1to740.csv"
JOB_CATEGORY_CSV = ROOT / "categories" / "직무_카테고리.csv"
OUTPUT_CSV = ROOT / "Embedding" / "question_contexts.csv"

NUMBERED_QUESTION_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*[\.)]\s+")
CHAR_LIMIT_PATTERN = re.compile(r"\(\s*\d{2,4}\s*자[^)]*\)")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣+#.]+")

LABEL_RULES = [
    ("지원동기", ["지원동기", "지원 동기", "지원한 동기", "지원하게 된"]),
    ("직무역량", ["직무", "역량", "강점", "전문성", "관련 경험"]),
    ("경험/성과", ["성과", "경험", "프로젝트", "공모전", "대외활동"]),
    ("문제해결", ["문제", "해결", "도전", "실패", "극복", "갈등"]),
    ("협업/소통", ["협업", "소통", "팀워크", "커뮤니케이션", "조직"]),
    ("산업/기업이해", ["산업", "제품", "서비스", "기업", "시장", "트렌드"]),
    ("입사후포부", ["입사 후", "포부", "목표", "기여", "계획"]),
    ("성장/가치관", ["성장", "가치관", "본인", "자신", "성격"]),
]


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def tokenize(text):
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token) > 1]


def question_label(question):
    for label, keywords in LABEL_RULES:
        if any(keyword in question for keyword in keywords):
            return label
    return "기타"


def load_category_map():
    if not JOB_CATEGORY_CSV.exists():
        return {}
    rows = read_csv(JOB_CATEGORY_CSV)
    return {int(row["원본행"]): row for row in rows if row.get("원본행")}


def split_numbered_sections(content):
    content = normalize_space(content)
    matches = list(NUMBERED_QUESTION_PATTERN.finditer(content))
    sections = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        section = normalize_space(content[start:end])
        if len(section) < 30:
            continue
        sections.append((int(match.group(1)), section))
    return sections


def split_question_answer(section):
    limit_match = CHAR_LIMIT_PATTERN.search(section)
    if limit_match:
        question = normalize_space(section[: limit_match.end()])
        answer = normalize_space(section[limit_match.end() :])
        return question, answer

    sentence_match = re.search(r"(?<=[.?])\s+", section)
    if sentence_match and sentence_match.start() <= 220:
        question = normalize_space(section[: sentence_match.start() + 1])
        answer = normalize_space(section[sentence_match.end() :])
        return question, answer

    boundary = min(len(section), 180)
    question = normalize_space(section[:boundary])
    answer = normalize_space(section[boundary:])
    return question, answer


def build_question_rows(source_csv=SOURCE_CSV):
    rows = read_csv(source_csv)
    category_by_source_row = load_category_map()
    question_rows = []
    for source_index, row in enumerate(rows, start=2):
        category = category_by_source_row.get(source_index, {})
        sections = split_numbered_sections(row.get("내용", ""))
        if not sections:
            continue
        for question_order, section in sections:
            question, answer = split_question_answer(section)
            if len(question) < 10 or len(answer) < 60:
                continue
            label = question_label(question)
            context = " ".join(
                [
                    row.get("회사", ""),
                    row.get("직무", ""),
                    row.get("유형", ""),
                    category.get("직무_대분류", ""),
                    category.get("직무_중분류", ""),
                    label,
                    question,
                    answer,
                ]
            )
            question_rows.append(
                {
                    "question_id": f"{source_index}-{question_order}",
                    "source_row": source_index,
                    "period": row.get("기간", ""),
                    "company": row.get("회사", ""),
                    "job": row.get("직무", ""),
                    "type": row.get("유형", ""),
                    "spec": row.get("스펙", ""),
                    "link": row.get("링크", ""),
                    "large": category.get("직무_대분류", ""),
                    "medium": category.get("직무_중분류", ""),
                    "small": category.get("직무_소분류", ""),
                    "question_order": question_order,
                    "question_label": label,
                    "question_text": question,
                    "answer": answer,
                    "answer_chars": len(answer),
                    "tokens": " ".join(tokenize(context)),
                    "context_300": normalize_space(context)[:300],
                    "context_600": normalize_space(context)[:600],
                    "context_1000": normalize_space(context)[:1000],
                }
            )
    return question_rows


def write_question_rows(rows, output_csv=OUTPUT_CSV):
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "question_id",
        "source_row",
        "period",
        "company",
        "job",
        "type",
        "spec",
        "link",
        "large",
        "medium",
        "small",
        "question_order",
        "question_label",
        "question_text",
        "answer",
        "answer_chars",
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
    rows = build_question_rows()
    write_question_rows(rows)
    labels = {}
    for row in rows:
        labels[row["question_label"]] = labels.get(row["question_label"], 0) + 1
    print(f"wrote={OUTPUT_CSV}")
    print(f"question_rows={len(rows):,}")
    for label, count in sorted(labels.items(), key=lambda item: item[1], reverse=True):
        print(f"{label}: {count:,}")


if __name__ == "__main__":
    main()
