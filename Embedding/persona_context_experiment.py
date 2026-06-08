import argparse
import csv
import hashlib
import math
import random
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTION_CSV = ROOT / "Embedding" / "question_contexts.csv"
OUTPUT_CSV = ROOT / "Embedding" / "persona_context_results.csv"

PERSONAS = [
    {
        "name": "ai_developer",
        "target_job": "AI 개발자",
        "large": "IT·개발",
        "medium": "AI·머신러닝",
        "labels": {"지원동기", "직무역량", "경험/성과", "협업/소통", "입사후포부"},
        "profile": {
            "major": "컴퓨터공학과",
            "certificates": "정보처리기사 필기 합격",
            "team_projects": "4인 팀 프로젝트에서 RAG 검색 기능 개발, 역할 분담 조율, 발표 자료 정리",
            "other_specs": "CNN 사진 분류 실습, Python, FastAPI",
            "age": "20대 후반",
            "gender": "",
        },
    },
    {
        "name": "backend_developer",
        "target_job": "백엔드 개발자",
        "large": "IT·개발",
        "medium": "백엔드 개발",
        "labels": {"지원동기", "직무역량", "경험/성과", "협업/소통", "입사후포부"},
        "profile": {
            "major": "소프트웨어학과",
            "certificates": "정보처리기사, SQLD",
            "team_projects": "팀 프로젝트에서 인증 서버와 Spring API 개발 담당, MySQL 쿼리 성능 개선",
            "other_specs": "Java, Spring Boot, Docker 기초",
            "age": "",
            "gender": "",
        },
    },
    {
        "name": "data_analyst",
        "target_job": "데이터 분석가",
        "large": "IT·개발",
        "medium": "데이터 분석",
        "labels": {"지원동기", "직무역량", "경험/성과", "문제해결", "입사후포부"},
        "profile": {
            "major": "통계학과",
            "certificates": "ADsP",
            "team_projects": "매출 데이터 분석 팀 프로젝트에서 대시보드 제작과 지표 정의 담당",
            "other_specs": "Python, SQL, 데이터 시각화 공모전 참여",
            "age": "20대 초반",
            "gender": "여성",
        },
    },
    {
        "name": "brand_marketer",
        "target_job": "브랜드 마케터",
        "large": "마케팅·광고",
        "medium": "브랜드 마케팅",
        "labels": {"지원동기", "직무역량", "경험/성과", "협업/소통", "산업/기업이해"},
        "profile": {
            "major": "경영학과",
            "certificates": "",
            "team_projects": "브랜드 리서치 팀 프로젝트에서 고객 인터뷰와 콘텐츠 캠페인 기획 담당",
            "other_specs": "SNS 운영, 전환율 개선 리포트 작성",
            "age": "",
            "gender": "",
        },
    },
    {
        "name": "semiconductor_engineer",
        "target_job": "반도체 공정 엔지니어",
        "large": "연구개발",
        "medium": "전기·전자·반도체",
        "labels": {"지원동기", "직무역량", "경험/성과", "문제해결", "입사후포부"},
        "profile": {
            "major": "전자공학과",
            "certificates": "전기기사 자격 준비",
            "team_projects": "회로 설계 팀 프로젝트에서 수율 문제 분석과 품질 개선안 정리 담당",
            "other_specs": "반도체 공정 실습, 계측 장비 사용 경험",
            "age": "20대 후반",
            "gender": "남성",
        },
    },
]


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def tokenize(text):
    return [token for token in (text or "").lower().split() if len(token) > 1]


def token_bigrams(text):
    tokens = tokenize(text)
    return tokens + [f"{tokens[index]}_{tokens[index + 1]}" for index in range(len(tokens) - 1)]


def feature_terms(text, mode):
    if mode == "token_unigram":
        return tokenize(text)
    if mode == "token_bigram":
        return token_bigrams(text)
    raise ValueError(f"unknown mode: {mode}")


def hashed_vector(text, mode, dimensions):
    counts = Counter()
    for term in feature_terms(text, mode):
        digest = hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, "little") % dimensions
        counts[index] += 1.0
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {index: value / norm for index, value in counts.items()}


def cosine(left, right):
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(index, 0.0) for index, value in left.items())


def profile_to_text(profile, include_demographics=False):
    labels = [
        ("major", "학과"),
        ("certificates", "자격증"),
        ("team_projects", "팀프로젝트 작업"),
        ("other_specs", "기타 스펙"),
    ]
    if include_demographics:
        labels.extend([("age", "나이"), ("gender", "성별")])
    return " ".join(f"{label}: {profile[key]}" for key, label in labels if profile.get(key))


def persona_query(persona, label):
    return " ".join([persona["target_job"], persona["large"], persona["medium"], label, profile_to_text(persona["profile"])])


def build_context(row, context_chars):
    context = " ".join(
        [
            row.get("company", ""),
            row.get("job", ""),
            row.get("type", ""),
            row.get("large", ""),
            row.get("medium", ""),
            row.get("question_label", ""),
            row.get("question_text", ""),
            row.get("answer", ""),
        ]
    )
    return " ".join(context.split())[:context_chars]


def evaluate(rows, context_chars, mode, dimensions):
    doc_vectors = [hashed_vector(build_context(row, context_chars), mode, dimensions) for row in rows]
    checks = []
    for persona in PERSONAS:
        for label in persona["labels"]:
            query_vector = hashed_vector(persona_query(persona, label), mode, dimensions)
            scored = [(cosine(query_vector, doc_vectors[index]), row) for index, row in enumerate(rows)]
            scored.sort(key=lambda item: item[0], reverse=True)
            top5 = scored[:5]
            top20 = scored[:20]
            checks.append(
                {
                    "large_hit": any(row["large"] == persona["large"] for _, row in top5),
                    "medium_hit": any(row["medium"] == persona["medium"] for _, row in top5),
                    "label_hit": any(row["question_label"] == label for _, row in top5),
                    "mrr": next((1 / rank for rank, (_, row) in enumerate(top20, start=1) if row["question_label"] == label), 0.0),
                    "top_score": top5[0][0] if top5 else 0.0,
                }
            )
    total = len(checks) or 1
    large_hit = sum(item["large_hit"] for item in checks) / total
    medium_hit = sum(item["medium_hit"] for item in checks) / total
    label_hit = sum(item["label_hit"] for item in checks) / total
    label_mrr = sum(item["mrr"] for item in checks) / total
    composite = (medium_hit * 0.35) + (label_hit * 0.4) + (label_mrr * 0.25)
    return {
        "context_chars": context_chars,
        "mode": mode,
        "persona_queries": total,
        "large_hit_at_5": round(large_hit, 4),
        "medium_hit_at_5": round(medium_hit, 4),
        "label_hit_at_5": round(label_hit, 4),
        "label_mrr_at_20": round(label_mrr, 4),
        "composite_score": round(composite, 4),
        "avg_top_score": round(sum(item["top_score"] for item in checks) / total, 4),
        "recommendation": "",
    }


def write_results(results, output_csv):
    if results:
        best_index, _ = max(enumerate(results), key=lambda item: item[1]["composite_score"])
        results[best_index]["recommendation"] = "best"
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)


def main():
    parser = argparse.ArgumentParser(description="Evaluate context length with fixed user personas.")
    parser.add_argument("--input", type=Path, default=QUESTION_CSV)
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV)
    parser.add_argument("--max-docs", type=int, default=12000)
    parser.add_argument("--dimensions", type=int, default=4096)
    parser.add_argument("--min-context", type=int, default=300)
    parser.add_argument("--max-context", type=int, default=1000)
    parser.add_argument("--step", type=int, default=100)
    args = parser.parse_args()

    rows = read_csv(args.input)
    random.Random(11).shuffle(rows)
    rows = rows[: min(args.max_docs, len(rows))]
    results = []
    for context_chars in range(args.min_context, args.max_context + 1, args.step):
        for mode in ["token_unigram", "token_bigram"]:
            print(f"running context={context_chars} mode={mode}", flush=True)
            result = evaluate(rows, context_chars, mode, args.dimensions)
            results.append(result)
            print(result, flush=True)
    write_results(results, args.output)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
