import math
import re
from collections import Counter

from Embedding.aihub_interview_dataset import dataset_status, load_rows


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣+#.]+")
DOCUMENTS = None
DATASET_META = None
SAMPLE_DOCUMENTS = None
SAMPLE_META = None

DEFAULT_INTERVIEW_QUESTIONS = [
    {
        "type": "basic",
        "category": "지원동기",
        "question": "지원한 직무를 선택한 이유와 이 직무를 잘할 수 있다고 생각하는 근거를 말씀해주세요.",
        "answer_tip": "관심 계기, 준비 과정, 직무와 연결되는 경험을 60초 안에 말합니다.",
    },
    {
        "type": "basic",
        "category": "직무역량",
        "question": "지원 직무에 필요한 핵심 역량은 무엇이고, 본인은 그 역량을 어떻게 준비했나요?",
        "answer_tip": "기술명이나 스펙 나열보다 실제 적용 경험과 결과를 함께 말합니다.",
    },
    {
        "type": "basic",
        "category": "경험/성과",
        "question": "가장 의미 있었던 프로젝트나 경험에서 맡은 역할과 성과를 설명해주세요.",
        "answer_tip": "상황, 역할, 행동, 결과, 배운 점 순서로 구성합니다.",
    },
    {
        "type": "basic",
        "category": "협업/소통",
        "question": "팀으로 일하면서 의견 차이나 갈등을 해결했던 경험을 말씀해주세요.",
        "answer_tip": "갈등 자체보다 조율 기준, 본인의 행동, 결과를 중심으로 말합니다.",
    },
    {
        "type": "basic",
        "category": "입사 후 포부",
        "question": "입사 후 어떤 방식으로 팀과 회사에 기여하고 싶나요?",
        "answer_tip": "초기 적응, 실무 기여, 장기 성장 방향을 나누어 말합니다.",
    },
]

OCCUPATION_KEYWORDS = [
    ("ICT", ["개발", "백엔드", "프론트", "데이터", "ai", "인공지능", "소프트웨어", "서버", "api", "ict", "it"]),
    ("RND", ["연구", "r&d", "rnd", "실험", "개발연구"]),
    ("ARD", ["디자인", "ui", "ux", "브랜드", "콘텐츠", "시각"]),
    ("SM", ["마케팅", "영업", "세일즈", "고객", "시장", "광고", "crm"]),
    ("BM", ["경영", "기획", "전략", "관리", "사업", "운영", "인사", "재무"]),
    ("PS", ["공공", "행정", "공무", "서비스", "복지", "기관"]),
    ("MM", ["생산", "제조", "품질", "설비", "공정", "물류"]),
]

RUBRIC = [
    ("relevance", "질문 적합도", 20),
    ("specificity", "경험 구체성", 20),
    ("structure", "답변 구조", 20),
    ("job_fit", "직무 연결성", 20),
    ("delivery", "전달 안정성", 20),
]


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def tokenize(text):
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token) > 1]


def tokenize_with_bigrams(text):
    tokens = tokenize(text)
    return tokens + [f"{tokens[index]}_{tokens[index + 1]}" for index in range(len(tokens) - 1)]


def infer_occupation(target_job="", large="", medium=""):
    text = " ".join([target_job or "", large or "", medium or ""]).lower()
    for occupation, keywords in OCCUPATION_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return occupation
    return ""


def profile_filters(structured_profile=None, target_job="", large="", medium=""):
    structured_profile = structured_profile or {}
    gender_map = {"남성": "MALE", "여성": "FEMALE"}
    age_map = {"20대 초반": "-34", "20대 후반": "-34", "30대 이상": "35-44"}
    return {
        "occupation": infer_occupation(target_job, large, medium),
        "gender": gender_map.get(structured_profile.get("gender", ""), ""),
        "age_range": age_map.get(structured_profile.get("age", ""), ""),
        "experience": "NEW",
    }


def document_from_row(row):
    text = " ".join(
        [
            row.get("occupation_label", ""),
            row.get("occupation", ""),
            row.get("experience", ""),
            row.get("question_text", ""),
            row.get("summary", ""),
            row.get("answer", ""),
            row.get("intent_category", ""),
            row.get("intent_expression", ""),
            row.get("emotion_category", ""),
        ]
    )
    document = dict(row)
    document["tokens"] = tokenize_with_bigrams(text)
    return document


def load_interview_documents():
    global DOCUMENTS, DATASET_META
    if DOCUMENTS is None:
        rows, errors, parse_modes = load_rows()
        DOCUMENTS = [document_from_row(row) for row in rows if row.get("question_text") and row.get("answer")]
        DATASET_META = {
            "row_count": len(DOCUMENTS),
            "errors": errors[:20],
            "error_count": len(errors),
            "parse_modes": parse_modes,
            "status": dataset_status(),
        }
    return DOCUMENTS


def load_sample_documents(limit=300):
    global SAMPLE_DOCUMENTS, SAMPLE_META
    if SAMPLE_DOCUMENTS is None:
        rows, errors, parse_modes = load_rows(limit=limit)
        SAMPLE_DOCUMENTS = [document_from_row(row) for row in rows if row.get("question_text") and row.get("answer")]
        status = dataset_status()
        SAMPLE_META = {
            "row_count": status.get("json_count", len(SAMPLE_DOCUMENTS)) - len(errors),
            "sample_count": len(SAMPLE_DOCUMENTS),
            "errors": errors[:20],
            "error_count": len(errors),
            "parse_modes": parse_modes,
            "status": status,
        }
    return SAMPLE_DOCUMENTS


def interview_dataset_meta():
    load_interview_documents()
    return DATASET_META


def sample_dataset_meta():
    load_sample_documents()
    return SAMPLE_META


def filter_documents(documents, filters):
    filtered = []
    for document in documents:
        if filters.get("occupation") and document.get("occupation") != filters["occupation"]:
            continue
        if filters.get("gender") and document.get("gender") != filters["gender"]:
            continue
        if filters.get("age_range") and document.get("age_range") != filters["age_range"]:
            continue
        if filters.get("experience") and document.get("experience") != filters["experience"]:
            continue
        filtered.append(document)
    if filtered:
        return filtered
    relaxed = []
    for document in documents:
        if filters.get("occupation") and document.get("occupation") != filters["occupation"]:
            continue
        relaxed.append(document)
    return relaxed or documents


def build_idf(documents):
    df = Counter()
    for document in documents:
        df.update(set(document["tokens"]))
    total = len(documents) or 1
    return {token: math.log((total - freq + 0.5) / (freq + 0.5) + 1) for token, freq in df.items()}


def bm25_score(query_tokens, document, idf, avgdl, k1=1.5, b=0.75):
    frequencies = Counter(document["tokens"])
    dl = len(document["tokens"]) or 1
    score = 0.0
    for token in query_tokens:
        if token not in frequencies:
            continue
        tf = frequencies[token]
        score += idf.get(token, 0.0) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    return score


def retrieve(documents, query, top_k=20):
    if not documents:
        return []
    idf = build_idf(documents)
    avgdl = sum(len(document["tokens"]) for document in documents) / len(documents)
    query_tokens = tokenize_with_bigrams(query)
    scored = [(bm25_score(query_tokens, document, idf, avgdl), document) for document in documents]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [(score, document) for score, document in scored[:top_k] if score > 0]


def personalized_questions(target_job="", target_company="", structured_profile=None):
    structured_profile = structured_profile or {}
    job = target_job or "지원 직무"
    company = target_company or "지원 회사"
    major = structured_profile.get("major", "")
    certificates = structured_profile.get("certificates", "")
    team_projects = structured_profile.get("team_projects", "")
    other_specs = structured_profile.get("other_specs", "")

    questions = []
    if major:
        questions.append(f"{major}에서 배운 내용 중 {job}와 가장 직접적으로 연결되는 부분은 무엇인가요?")
    if certificates:
        questions.append(f"자격증이나 학습 경험이 {job} 실무에 어떻게 도움이 된다고 생각하나요?")
    if team_projects:
        questions.append(f"팀프로젝트에서 본인이 맡은 역할과 어려웠던 문제를 어떻게 해결했는지 말씀해주세요.")
    if other_specs:
        questions.append(f"입력한 기타 경험 중 {company}의 {job} 업무와 가장 연결되는 경험은 무엇인가요?")
    questions.append(f"{company}에서 {job}로 일하게 된다면 처음 3개월 동안 어떤 역량을 먼저 보여주고 싶나요?")
    return questions[:5]


def serialize_document(score, document):
    return {
        "score": round(score, 4),
        "question_id": document.get("question_id", ""),
        "source_zip": document.get("source_zip", ""),
        "occupation": document.get("occupation", ""),
        "occupation_label": document.get("occupation_label", ""),
        "gender": document.get("gender", ""),
        "age_range": document.get("age_range", ""),
        "experience": document.get("experience", ""),
        "question": document.get("question_text", ""),
        "summary": document.get("summary", ""),
        "answer_preview": normalize_space(document.get("answer", ""))[:360],
        "intent_category": document.get("intent_category", ""),
        "emotion_category": document.get("emotion_category", ""),
        "answer_audio_path": document.get("answer_audio_path", ""),
    }


def build_interview_set(payload):
    structured_profile = payload.get("structured_profile") or {}
    query = " ".join(
        [
            payload.get("target_company", ""),
            payload.get("target_job", ""),
            payload.get("user_profile", ""),
            structured_profile.get("major", ""),
            structured_profile.get("certificates", ""),
            structured_profile.get("team_projects", ""),
            structured_profile.get("other_specs", ""),
        ]
    ).strip()
    documents = load_interview_documents() if query else load_sample_documents()
    filters = profile_filters(
        structured_profile,
        payload.get("target_job", ""),
        payload.get("large", ""),
        payload.get("medium", ""),
    )
    filtered = filter_documents(documents, filters)
    if query:
        results = retrieve(filtered, query, top_k=30)
    else:
        results = []
    if not results:
        results = [(0.0, document) for document in filtered[:30]]

    seen = set()
    dataset_questions = []
    for score, document in results:
        question = document.get("question_text", "")
        key = normalize_space(question)
        if not key or key in seen:
            continue
        seen.add(key)
        dataset_questions.append(serialize_document(score, document))
        if len(dataset_questions) >= 8:
            break

    personal = [
        {"type": "personalized", "category": "사용자 맞춤", "question": question, "answer_tip": "입력한 스펙을 실제 행동과 결과 중심으로 말합니다."}
        for question in personalized_questions(payload.get("target_job", ""), payload.get("target_company", ""), structured_profile)
    ]
    return {
        "dataset": interview_dataset_meta() if query else sample_dataset_meta(),
        "filters": filters,
        "filtered_count": len(filtered),
        "basic_questions": DEFAULT_INTERVIEW_QUESTIONS,
        "personalized_questions": personal,
        "dataset_questions": dataset_questions,
    }


def score_answer(question, answer_text, audio_features=None):
    question_tokens = set(tokenize(question))
    answer_tokens = set(tokenize(answer_text))
    overlap = len(question_tokens & answer_tokens)
    answer_len = len(normalize_space(answer_text))
    has_numbers = bool(re.search(r"\d|%|명|건|회|개월|년", answer_text))
    has_structure = sum(keyword in answer_text for keyword in ["상황", "역할", "문제", "해결", "결과", "배웠", "기여"])
    positive_words = sum(keyword in answer_text for keyword in ["해결", "개선", "성장", "협업", "기여", "노력", "성과"])
    job_words = sum(keyword in answer_text for keyword in ["직무", "회사", "서비스", "고객", "팀", "프로젝트", "기술", "업무"])
    audio_features = audio_features or {}
    duration = float(audio_features.get("duration_seconds") or 0)
    transcript_confidence = float(audio_features.get("transcript_confidence") or 0)
    words_per_minute = (len(tokenize(answer_text)) / duration * 60) if duration > 0 else 0

    scores = {
        "relevance": min(20, 8 + overlap * 3),
        "specificity": min(20, 8 + (6 if has_numbers else 0) + min(6, answer_len // 120)),
        "structure": min(20, 8 + has_structure * 3),
        "job_fit": min(20, 8 + min(8, job_words * 2) + min(4, positive_words)),
        "delivery": 14,
    }
    if duration:
        if 35 <= duration <= 100:
            scores["delivery"] += 4
        if 80 <= words_per_minute <= 180:
            scores["delivery"] += 2
    if transcript_confidence:
        scores["delivery"] = min(20, scores["delivery"] + round(transcript_confidence * 2))

    total = sum(min(20, value) for value in scores.values())
    feedback = []
    if answer_len < 180:
        feedback.append("답변이 짧습니다. 상황, 본인 행동, 결과를 한 문장씩 더 넣어주세요.")
    if not has_numbers:
        feedback.append("성과나 규모를 숫자로 말하면 더 설득력 있게 들립니다.")
    if has_structure < 2:
        feedback.append("문제-행동-결과 흐름이 더 분명하게 보이도록 답변 순서를 정리해보세요.")
    if job_words < 2:
        feedback.append("마지막에 지원 직무나 회사 업무와 연결되는 문장을 추가해보세요.")
    if not feedback:
        feedback.append("질문에 맞는 핵심 경험이 들어가 있습니다. 꼬리 질문에 대비해 판단 근거를 더 준비하세요.")

    return {
        "total": total,
        "rubric": [
            {"key": key, "label": label, "max": maximum, "score": min(maximum, scores[key])}
            for key, label, maximum in RUBRIC
        ],
        "feedback": feedback,
        "audio_note": "현재 점수는 STT 텍스트와 녹음 길이 기반입니다. 목소리 떨림 분석은 실제 wav 저장과 음성 특징 추출을 붙이면 확장할 수 있습니다.",
        "words_per_minute": round(words_per_minute, 1) if words_per_minute else 0,
    }
