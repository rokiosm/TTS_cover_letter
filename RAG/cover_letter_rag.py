import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from RAG.draft_generator import (
    build_reference_guides,
    build_cover_letter_drafts,
    build_interview_api_seed,
    build_interview_plan,
    common_questions_for_job,
    normalize_structured_profile,
    profile_has_content,
    structured_profile_to_text,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "linkareer_1to740.csv"
JOB_CATEGORY_PATH = ROOT / "categories" / "직무_카테고리.csv"
QUESTION_CONTEXT_PATH = ROOT / "Embedding" / "question_contexts.csv"
RETRIEVAL_CONTEXT_FIELD = "context_300"

QUESTION_PATTERNS = [
    re.compile(r"(?m)^\s*(?:\[\s*)?(\d+(?:[-.]\d+)?)\s*[\].)-]?\s*([^\n]{8,160})"),
    re.compile(r"(?m)^\s*\[([^\]]{8,120})\]"),
]

CANONICAL_QUESTIONS = [
    ("지원동기", "회사와 직무에 지원한 동기를 작성해주세요.", ["지원동기", "지원 동기", "지원한 동기", "지원하게", "지원한 이유"]),
    ("직무역량", "지원 직무에 필요한 역량과 이를 쌓아온 경험을 작성해주세요.", ["직무역량", "직무 역량", "역량", "강점", "전문성", "경쟁력", "차별화"]),
    ("경험/성과", "가장 의미 있었던 경험과 성과를 구체적으로 작성해주세요.", ["성과", "경험", "프로젝트", "수상", "공모전"]),
    ("도전/문제해결", "어려움을 해결했거나 도전했던 경험을 작성해주세요.", ["도전", "문제", "해결", "갈등", "실패", "극복"]),
    ("협업/소통", "협업 또는 소통을 통해 목표를 달성한 경험을 작성해주세요.", ["협업", "소통", "팀", "커뮤니케이션", "조직"]),
    ("성장과정", "본인의 성장 과정이나 가치관을 직무와 연결해 작성해주세요.", ["성장과정", "성장 과정", "가치관", "본인", "자신"]),
    ("입사 후 포부", "입사 후 이루고 싶은 목표와 기여 방안을 작성해주세요.", ["입사 후", "포부", "목표", "기여", "계획"]),
]

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣+#.]+")


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def tokenize(text):
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token) > 1]


def tokenize_with_bigrams(text):
    tokens = tokenize(text)
    return tokens + [f"{tokens[index]}_{tokens[index + 1]}" for index in range(len(tokens) - 1)]


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def has_final_consonant(text):
    text = normalize_space(text)
    if not text:
        return False
    char = text[-1]
    if "가" <= char <= "힣":
        return (ord(char) - ord("가")) % 28 != 0
    return char.isdigit() and char not in "2459"


def josa(text, consonant_form, vowel_form):
    return consonant_form if has_final_consonant(text) else vowel_form


def load_documents():
    if QUESTION_CONTEXT_PATH.exists():
        return load_question_documents()

    rows = read_csv(DATA_PATH)
    categories = read_csv(JOB_CATEGORY_PATH)
    category_by_source_row = {int(row["원본행"]): row for row in categories if row.get("원본행")}

    documents = []
    for index, row in enumerate(rows, start=2):
        category = category_by_source_row.get(index, {})
        text = " ".join(
            [
                row.get("회사", ""),
                row.get("직무", ""),
                row.get("유형", ""),
                row.get("스펙", ""),
                row.get("내용", ""),
                category.get("직무_대분류", ""),
                category.get("직무_중분류", ""),
                category.get("직무_소분류", ""),
            ]
        )
        documents.append(
            {
                "source_row": index,
                "period": row.get("기간", ""),
                "company": row.get("회사", ""),
                "job": row.get("직무", ""),
                "spec": row.get("스펙", ""),
                "content": row.get("내용", ""),
                "link": row.get("링크", ""),
                "large": category.get("직무_대분류", ""),
                "medium": category.get("직무_중분류", ""),
                "small": category.get("직무_소분류", ""),
                "tokens": tokenize(text),
            }
        )
    return documents


def load_question_documents():
    documents = []
    for row in read_csv(QUESTION_CONTEXT_PATH):
        retrieval_context = row.get(RETRIEVAL_CONTEXT_FIELD) or row.get("answer", "")
        text = " ".join([row.get("job", ""), row.get("large", ""), row.get("medium", ""), retrieval_context])
        documents.append(
            {
                "question_id": row.get("question_id", ""),
                "source_row": int(row.get("source_row") or 0),
                "period": row.get("period", ""),
                "company": row.get("company", ""),
                "job": row.get("job", ""),
                "spec": row.get("spec", ""),
                "content": row.get("answer", ""),
                "question_text": row.get("question_text", ""),
                "question_label": row.get("question_label", ""),
                "link": row.get("link", ""),
                "large": row.get("large", ""),
                "medium": row.get("medium", ""),
                "small": row.get("small", ""),
                "retrieval_context": retrieval_context,
                "tokens": tokenize_with_bigrams(text),
            }
        )
    return documents


def build_idf(documents):
    df = Counter()
    for document in documents:
        df.update(set(document["tokens"]))
    total = len(documents)
    return {token: math.log((total - freq + 0.5) / (freq + 0.5) + 1) for token, freq in df.items()}


def bm25_score(query_tokens, document, idf, avgdl, k1=1.5, b=0.75):
    frequencies = Counter(document["tokens"])
    dl = len(document["tokens"]) or 1
    score = 0.0
    for token in query_tokens:
        if token not in frequencies:
            continue
        tf = frequencies[token]
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * dl / avgdl)
        score += idf.get(token, 0.0) * numerator / denominator
    return score


def filter_documents(documents, large="", medium="", small="", job_keyword=""):
    filtered = []
    for document in documents:
        if large and document["large"] != large:
            continue
        if medium and document["medium"] != medium:
            continue
        if small and document["small"] != small:
            continue
        if job_keyword and job_keyword.lower() not in document["job"].lower():
            continue
        filtered.append(document)
    return filtered


def retrieve(documents, query, top_k):
    if not documents:
        return []
    idf = build_idf(documents)
    avgdl = sum(len(document["tokens"]) for document in documents) / len(documents)
    query_tokens = tokenize(query)
    scored = []
    for document in documents:
        score = bm25_score(query_tokens, document, idf, avgdl)
        scored.append((score, document))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [(score, document) for score, document in scored[:top_k] if score > 0]


def extract_questions(content):
    questions = []
    for pattern in QUESTION_PATTERNS:
        for match in pattern.finditer(content or ""):
            text = match.group(match.lastindex or 1)
            text = normalize_space(text)
            if 8 <= len(text) <= 60 and not re.search(r"①|②|③|자격증|온라인 몰|페이스북|구글", text):
                questions.append(text)
    return questions


def common_questions(results, limit=5):
    counter = Counter()
    examples = defaultdict(list)
    for _, document in results:
        if document.get("question_text"):
            question = document["question_text"]
            counter[question] += 1
            if len(examples[question]) < 3:
                examples[question].append(document["company"])
            continue
        content = document["content"]
        for label, question, keywords in CANONICAL_QUESTIONS:
            if any(keyword in content for keyword in keywords):
                counter[question] += 1
                if len(examples[question]) < 3:
                    examples[question].append(document["company"])
        for question in extract_questions(document["content"]):
            normalized = re.sub(r"\([^)]*\)", "", question)
            normalized = normalize_space(normalized)
            normalized = normalized[:120]
            if len(normalized) > 60:
                continue
            if not re.search(r"작성|주세요|기술|설명|서술|무엇|어떻게", normalized):
                continue
            if not any(keyword in normalized for _, _, keywords in CANONICAL_QUESTIONS for keyword in keywords):
                continue
            counter[normalized] += 1
            if len(examples[normalized]) < 3:
                examples[normalized].append(document["company"])
    if not counter:
        for _, question, _ in CANONICAL_QUESTIONS[:5]:
            counter[question] += 1
    return [(question, count, examples[question]) for question, count in counter.most_common(limit)]


def content_preview(content, max_chars=650):
    content = normalize_space(content)
    return content[:max_chars] + ("..." if len(content) > max_chars else "")


def build_generation_prompt(results, questions, user_profile, target_company, target_job):
    context_blocks = []
    for rank, (score, document) in enumerate(results, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[참고 {rank}] score={score:.3f}",
                    f"회사: {document['company']}",
                    f"직무: {document['job']}",
                    f"카테고리: {document['large']} > {document['medium']} > {document['small']}",
                    f"질문유형: {document.get('question_label', '')}",
                    f"질문: {document.get('question_text', '')}",
                    f"스펙: {document['spec']}",
                    f"답변요약: {content_preview(document['content'])}",
                ]
            )
        )

    question_lines = [f"- {question} ({count}회)" for question, count, _ in questions]
    return "\n\n".join(
        [
            "너는 합격 자기소개서 작성 도우미다.",
            f"지원 회사: {target_company or '(미지정)'}",
            f"지원 직무: {target_job or '(미지정)'}",
            f"지원자 정보: {user_profile or '(미지정)'}",
            "공통 문항 후보:\n" + ("\n".join(question_lines) if question_lines else "- 지원동기\n- 직무역량\n- 입사 후 포부"),
            "검색된 합격 자기소개서 컨텍스트:\n" + "\n\n".join(context_blocks),
            "작성 지시:\n- 위 컨텍스트의 표현을 그대로 복사하지 말고 구조와 논리만 참고한다.\n- 공통 문항 후보별로 질문을 정리하고, 각 질문에 맞는 자기소개서 초안을 작성한다.\n- 경험-행동-결과-직무연결 순서가 드러나게 쓴다.",
        ]
    )


def run_rag(
    large="",
    medium="",
    small="",
    job_keyword="",
    query="",
    top_k=5,
    target_company="",
    target_job="",
    user_profile="",
    structured_profile=None,
    documents=None,
):
    documents = documents or load_documents()
    filtered = filter_documents(documents, large, medium, small, job_keyword)
    structured_profile = normalize_structured_profile(structured_profile, user_profile)
    profile_text = structured_profile_to_text(structured_profile)
    if not profile_has_content(structured_profile):
        return {
            "filtered_count": len(filtered),
            "retrieved_count": 0,
            "results": [],
            "questions": [],
            "prompt": "지원자 정보를 입력하면 직무별 공통 질문, 자기소개서 초안, 면접 준비 질문이 만들어집니다.",
            "drafts": [],
            "interview_plan": {},
            "interview_api_seed": {},
            "requires_profile": True,
        }

    search_query = " ".join([target_job, profile_text, job_keyword, query]).strip()
    if not search_query:
        search_query = "지원동기 직무역량 성과 경험 입사 후 포부"

    results = retrieve(filtered, search_query, top_k)
    questions = common_questions_for_job(target_job, results, structured_profile)
    reference_guides = build_reference_guides(results)
    drafts = build_cover_letter_drafts(questions, structured_profile, target_company, target_job, reference_guides)
    interview_plan = build_interview_plan(drafts, profile_text, target_job)
    prompt = build_generation_prompt(results, questions, profile_text, target_company, target_job)
    return {
        "filtered_count": len(filtered),
        "retrieved_count": len(results),
        "results": results,
        "questions": questions,
        "drafts": drafts,
        "interview_plan": interview_plan,
        "interview_api_seed": build_interview_api_seed(
            drafts,
            interview_plan,
            target_company,
            target_job,
            profile_text,
            structured_profile,
        ),
        "prompt": prompt,
        "requires_profile": False,
    }


def category_counts(documents=None):
    documents = documents or load_documents()
    counter = Counter((doc["large"], doc["medium"], doc["small"]) for doc in documents)
    return [
        {"large": large, "medium": medium, "small": small, "count": count}
        for (large, medium, small), count in counter.most_common()
    ]


def serialize_rag_output(output):
    return {
        "filtered_count": output["filtered_count"],
        "retrieved_count": output["retrieved_count"],
        "requires_profile": output.get("requires_profile", False),
        "score_note": "BM25 기반 관련도 점수라 고정 만점은 없고, 같은 검색 결과 안에서 높을수록 더 유사합니다.",
        "results": [
            {
                "score": round(score, 4),
                "source_row": document["source_row"],
                "period": document["period"],
                "company": document["company"],
                "job": document["job"],
                "question_id": document.get("question_id", ""),
                "question_label": document.get("question_label", ""),
                "question_text": document.get("question_text", ""),
                "spec": document["spec"],
                "link": document["link"],
                "category": {
                    "large": document["large"],
                    "medium": document["medium"],
                    "small": document["small"],
                },
                "preview": content_preview(document["content"]),
            }
            for score, document in output["results"]
        ],
        "questions": [
            {"question": question, "count": count, "example_companies": companies}
            for question, count, companies in output["questions"]
        ],
        "drafts": output.get("drafts", []),
        "interview_plan": output.get("interview_plan", {}),
        "interview_api_seed": output.get("interview_api_seed", {}),
        "prompt": output["prompt"],
    }


def list_categories(documents):
    for row in category_counts(documents):
        print(f"{row['count']:5d} | {row['large']} > {row['medium']} > {row['small']}")


def main():
    parser = argparse.ArgumentParser(description="직무 카테고리 기반 자기소개서 RAG 검색 도구")
    parser.add_argument("--large", help="직무 대분류")
    parser.add_argument("--medium", help="직무 중분류")
    parser.add_argument("--small", help="직무 소분류")
    parser.add_argument("--job-keyword", help="직무명 포함 키워드")
    parser.add_argument("--query", default="", help="검색 질문 또는 강조할 역량")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--target-company", default="")
    parser.add_argument("--target-job", default="")
    parser.add_argument("--user-profile", default="")
    parser.add_argument("--list-categories", action="store_true")
    args = parser.parse_args()

    documents = load_documents()
    if args.list_categories:
        list_categories(documents)
        return

    output = run_rag(
        large=args.large or "",
        medium=args.medium or "",
        small=args.small or "",
        job_keyword=args.job_keyword or "",
        query=args.query,
        top_k=args.top_k,
        target_company=args.target_company,
        target_job=args.target_job,
        user_profile=args.user_profile,
    )
    results = output["results"]
    questions = output["questions"]

    print(f"filtered_documents={output['filtered_count']}")
    print(f"retrieved={output['retrieved_count']}")
    print("\nTopK")
    for rank, (score, document) in enumerate(results, start=1):
        print(f"{rank}. score={score:.3f} row={document['source_row']} {document['company']} / {document['job']} / {document['large']} > {document['medium']}")
        print(f"   link={document['link']}")

    print("\nCommon Questions")
    for question, count, companies in questions:
        print(f"- {question} ({count}회, 예: {', '.join(companies)})")

    print("\nGeneration Prompt")
    print(output["prompt"])


if __name__ == "__main__":
    main()
