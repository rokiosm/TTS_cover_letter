import re
from collections import Counter, defaultdict


DEFAULT_COMMON_QUESTION_TEMPLATES = [
    ("지원동기", "{job}에 지원한 동기와 이 직무를 선택하게 된 계기를 작성해주세요."),
    ("직무역량", "{job} 수행에 필요한 핵심 역량과 이를 준비해 온 과정을 작성해주세요."),
    ("경험/성과", "{job}와 연결되는 프로젝트 또는 경험에서 맡은 역할과 성과를 구체적으로 작성해주세요."),
    ("협업/소통", "팀을 이뤄 협업하면서 성과를 만들었던 경험을 작성해주세요."),
    ("입사 후 포부", "입사 후 {job}로서 이루고 싶은 목표와 기여 방안을 작성해주세요."),
]

PROFILE_SIGNAL_RULES = [
    ("데이터 분석", ["데이터", "분석", "sql", "python", "파이썬", "ga4", "excel", "엑셀", "통계"]),
    ("프로젝트 실행", ["프로젝트", "공모전", "캠페인", "서비스", "개발", "기획", "운영"]),
    ("협업", ["팀", "협업", "소통", "커뮤니케이션", "리더", "조율"]),
    ("성과 개선", ["성과", "개선", "전환율", "매출", "효율", "지표", "%", "증가", "감소"]),
    ("고객/사용자 이해", ["고객", "사용자", "유저", "시장", "리서치", "인터뷰", "VOC"]),
    ("전문성", ["자격증", "전공", "인턴", "실무", "논문", "교육", "수료"]),
]

QUESTION_EVIDENCE_RULES = {
    "지원동기": {
        "prefer": ["지원", "회사", "직무", "관심", "목표", "서비스", "제품", "사용자", "ai", "개발"],
        "avoid": [],
        "fallback": "지원 회사와 직무를 선택한 이유가 되는 경험이나 관심 계기를 한 가지 더 입력하면 문항에 맞는 답변을 만들 수 있습니다.",
    },
    "직무역량": {
        "prefer": ["프로젝트", "개발", "분석", "기획", "운영", "python", "sql", "rag", "cnn", "ai", "데이터", "기술"],
        "avoid": [],
        "fallback": "직무 역량을 보여줄 프로젝트, 실습, 인턴, 사용 기술 중 하나를 구체적으로 입력하면 좋습니다.",
    },
    "경험/성과": {
        "prefer": ["프로젝트", "성과", "개선", "수상", "공모전", "개발", "분류", "분석", "완성", "운영", "%"],
        "avoid": ["수업", "필기", "합격", "자격증"],
        "fallback": "성과로 설명할 프로젝트나 활동 결과가 필요합니다. 단순 보유 스펙보다 무엇을 만들고 개선했는지가 중요합니다.",
    },
    "도전/문제해결": {
        "prefer": ["문제", "해결", "개선", "실패", "어려움", "오류", "분석", "검증", "rag", "cnn", "프로젝트"],
        "avoid": ["필기", "합격"],
        "fallback": "문제 상황, 본인이 시도한 해결 방법, 결과를 입력하면 문제해결형 답변을 만들 수 있습니다.",
    },
    "협업/소통": {
        "prefer": ["팀", "협업", "소통", "조율", "회의", "분담", "역할", "리더", "팀원", "공동", "커뮤니케이션"],
        "avoid": ["정보처리기사", "필기", "합격", "자격증", "전공", "수업", "수료"],
        "fallback": "현재 입력한 스펙에는 팀을 이뤄 협업한 경험이 뚜렷하지 않습니다. 팀 프로젝트에서 맡은 역할, 조율한 내용, 공동 성과를 추가해야 이 문항에 맞는 자소서가 됩니다.",
    },
    "성장과정": {
        "prefer": ["전공", "수업", "학습", "관심", "성장", "기록", "개선", "ai", "컴퓨터공학"],
        "avoid": [],
        "fallback": "성장 과정과 가치관으로 연결할 학습 계기나 반복적으로 개선해 온 경험을 입력하면 좋습니다.",
    },
    "입사 후 포부": {
        "prefer": ["목표", "기여", "개발", "분석", "사용자", "서비스", "ai", "직무", "성장"],
        "avoid": [],
        "fallback": "입사 후 어떤 업무에서 어떤 방식으로 기여하고 싶은지 한 문장을 추가하면 포부 답변이 좋아집니다.",
    },
}

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣+#.]+")
QUESTION_SPLIT_PATTERN = re.compile(r"\n+|(?:(?:^|\s)\d+[.)]\s*)")


def tokenize(text):
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token) > 1]


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def has_final_consonant(text):
    text = normalize_space(text)
    if not text:
        return False
    char = text[-1]
    if "가" <= char <= "힣":
        return (ord(char) - ord("가")) % 28 != 0
    if char.lower() in set("bcdfghjklmnpqrstvxz"):
        return True
    return char.isdigit() and char not in "2459"


def josa(text, consonant_form, vowel_form):
    return consonant_form if has_final_consonant(text) else vowel_form


def content_preview(content, max_chars=650):
    content = normalize_space(content)
    return content[:max_chars] + ("..." if len(content) > max_chars else "")


def normalize_structured_profile(structured_profile=None, user_profile=""):
    structured_profile = structured_profile or {}
    fields = {
        "major": normalize_space(structured_profile.get("major", "")),
        "certificates": normalize_space(structured_profile.get("certificates", "")),
        "team_projects": normalize_space(structured_profile.get("team_projects", "")),
        "other_specs": normalize_space(structured_profile.get("other_specs", "")),
        "age": normalize_space(structured_profile.get("age", "")),
        "gender": normalize_space(structured_profile.get("gender", "")),
        "freeform": normalize_space(user_profile),
    }
    return fields


def structured_profile_to_text(structured_profile):
    labels = [
        ("major", "학과/전공"),
        ("certificates", "자격증"),
        ("team_projects", "팀프로젝트 작업"),
        ("other_specs", "기타 스펙"),
        ("age", "나이"),
        ("gender", "성별"),
        ("freeform", "추가 입력"),
    ]
    parts = [f"{label}: {structured_profile[key]}" for key, label in labels if structured_profile.get(key)]
    return "\n".join(parts)


def profile_has_content(structured_profile):
    return any(value for key, value in structured_profile.items() if key not in {"age", "gender"})


def infer_profile_signals(profile_text):
    tokens = set(tokenize(profile_text))
    lowered = (profile_text or "").lower()
    signals = []
    for label, keywords in PROFILE_SIGNAL_RULES:
        if any(keyword.lower() in tokens or keyword.lower() in lowered for keyword in keywords):
            signals.append(label)
    return signals or ["지원 직무와 연결 가능한 경험"]


def split_profile_items(text, split_commas=True):
    delimiter_pattern = r"(?<=[.!?。])\s+|\n+|[;,·]+" if split_commas else r"(?<=[.!?。])\s+|\n+|[;·]+"
    pieces = re.split(delimiter_pattern, text or "")
    return [normalize_space(piece) for piece in pieces if normalize_space(piece)]


def split_question_items(text):
    pieces = QUESTION_SPLIT_PATTERN.split(text or "")
    questions = []
    for piece in pieces:
        piece = normalize_space(piece).strip("-• ")
        if len(piece) < 8:
            continue
        if not re.search(r"요\??|까\??|작성|기술|서술|설명|무엇|어떻게|경험|동기|목표|역량", piece):
            continue
        questions.append(piece[:180])
    return questions


def token_counter(text):
    return Counter(tokenize(text))


def cosine_similarity(left, right):
    left_counter = token_counter(left)
    right_counter = token_counter(right)
    if not left_counter or not right_counter:
        return 0.0
    shared = set(left_counter) & set(right_counter)
    numerator = sum(left_counter[token] * right_counter[token] for token in shared)
    left_norm = sum(value * value for value in left_counter.values()) ** 0.5
    right_norm = sum(value * value for value in right_counter.values()) ** 0.5
    return numerator / (left_norm * right_norm or 1)


def jaccard_similarity(left, right):
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def question_similarity(left, right):
    return (cosine_similarity(left, right) * 0.65) + (jaccard_similarity(left, right) * 0.35)


def source_weight(source):
    weights = {
        "custom": 8,
        "company": 6,
        "retrieved": 3,
        "template": 1,
    }
    return weights.get(source, 1)


def split_structured_profile_items(structured_profile):
    items = []
    field_labels = {
        "major": "학과",
        "certificates": "자격증",
        "team_projects": "팀프로젝트",
        "other_specs": "기타 스펙",
        "freeform": "추가 입력",
    }
    for key, label in field_labels.items():
        split_commas = key not in {"team_projects", "other_specs"}
        for order, piece in enumerate(split_profile_items(structured_profile.get(key, ""), split_commas=split_commas)):
            items.append({"field": key, "field_label": label, "text": piece, "order": order})
    return items


def polish_profile_item(piece):
    piece = normalize_space(piece).rstrip(".")
    if piece in {"컴퓨터공학", "컴퓨터공학과"}:
        return "컴퓨터공학 전공에서 자료구조, 알고리즘, 시스템 흐름을 학습한 경험"
    replacements = [
        (r"하고$", "했습니다"),
        (r"하며$", "했습니다"),
        (r"하고,", "하고"),
        (r"들음$", "수강했습니다"),
        (r"사용$", "활용했습니다"),
        (r"분류$", "분류를 수행했습니다"),
        (r"함$", "했습니다"),
        (r"함\)$", "했습니다)"),
        (r"됨$", "되었습니다"),
        (r"합격$", "합격했습니다"),
        (r"수료$", "수료했습니다"),
    ]
    for pattern, replacement in replacements:
        piece = re.sub(pattern, replacement, piece)
    return piece


def score_profile_item(piece, label):
    rules = QUESTION_EVIDENCE_RULES.get(label, {})
    lowered = piece.lower()
    indirect_specs = ["toeic", "토익", "토스", "토익스피킹", "opic", "오픽", "봉사", "volunteer"]
    if any(keyword in lowered for keyword in indirect_specs):
        return -8
    if label in {"직무역량", "경험/성과", "도전/문제해결", "협업/소통"} and not any(
        keyword in lowered
        for keyword in ["프로젝트", "개발", "구현", "분석", "실험", "개선", "설계", "운영", "인턴", "팀", "협업", "데이터", "모델", "시스템"]
    ):
        return -5
    score = sum(2 for keyword in rules.get("prefer", []) if keyword.lower() in lowered)
    score -= sum(3 for keyword in rules.get("avoid", []) if keyword.lower() in lowered)
    if re.search(r"\d|%|명|건|회|개월|년", piece):
        score += 1
    if len(piece) >= 80:
        score += 2
    if "프로젝트" in piece and label in {"직무역량", "경험/성과", "도전/문제해결"}:
        score += 2
    if label == "협업/소통" and not any(keyword in lowered for keyword in ["팀", "협업", "소통", "조율", "분담", "팀원", "공동"]):
        score -= 5
    return score


def field_bonus(field, label):
    if field == "team_projects" and label in {"협업/소통", "경험/성과", "직무역량", "도전/문제해결"}:
        return 10
    if field == "major" and label in {"성장과정", "지원동기"}:
        return 3
    if field == "major" and label in {"직무역량", "경험/성과", "도전/문제해결", "협업/소통"}:
        return -8
    if field == "certificates" and label in {"입사 후 포부"}:
        return 2
    if field == "certificates" and label in {"직무역량", "협업/소통", "경험/성과", "도전/문제해결"}:
        return -6
    if field == "other_specs":
        return 4
    return 0


def select_evidence_items(structured_profile, label, limit=2):
    candidates = split_structured_profile_items(structured_profile)
    scored = [
        (score_profile_item(item["text"], label) + field_bonus(item["field"], label), len(item["text"]), item)
        for item in candidates
    ]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if any(item["field"] == "team_projects" for _, _, item in scored):
        scored = [item for item in scored if item[2]["field"] != "major" or label in {"지원동기", "성장과정"}]
    selected = [item for _, _, item in scored[:limit]]
    if label in {"협업/소통", "경험/성과", "직무역량", "도전/문제해결"}:
        team_items = [item for _, _, item in scored if item["field"] == "team_projects"]
        support_items = [item for _, _, item in scored if item["field"] == "other_specs"]
        certificate_items = [item for _, _, item in scored if item["field"] == "certificates"]
        selected = []
        if team_items:
            selected.append(team_items[0])
        for item in support_items + certificate_items:
            if len(selected) >= limit:
                break
            if item not in selected:
                selected.append(item)
        if len(selected) < 2:
            for item in [item for _, _, item in scored]:
                if len(selected) >= limit:
                    break
                if item not in selected:
                    selected.append(item)
        if len(selected) < limit:
            fallback_fields = ["other_specs", "certificates", "major"]
            for field in fallback_fields:
                for item in candidates:
                    if len(selected) >= limit:
                        break
                    if item["field"] == field and item not in selected:
                        selected.append(item)
    selected.sort(key=lambda item: (item["field"] != "team_projects", item.get("order", 0)))
    selected = selected[:limit]
    return [
        {"field": item["field"], "field_label": item["field_label"], "text": polish_profile_item(item["text"])}
        for item in selected
    ]


def question_label(question):
    priority_rules = [
        ("지원동기", ["지원동기", "지원 동기", "지원한 동기", "지원하게", "지원한 이유", "희망분야", "희망 분야"]),
        ("입사 후 포부", ["입사 후", "포부", "목표", "기여", "계획"]),
        ("협업/소통", ["협업", "팀", "소통", "커뮤니케이션", "조직", "역할 분담", "의견", "조율"]),
        ("경험/성과", ["성과", "결과물", "수치", "프로젝트 성과", "맡은 역할과 결과", "수행한 프로젝트", "프로젝트 또는 경험", "프로젝트 또는 활동"]),
        ("도전/문제해결", ["도전", "열정", "문제", "해결", "갈등", "실패", "극복"]),
        ("직무역량", ["직무", "역량", "강점", "전문성", "경쟁력", "차별화"]),
        ("경험/성과", ["성과", "경험", "프로젝트", "수상", "공모전"]),
        ("성장과정", ["성장", "가치관", "본인", "자신"]),
    ]
    for label, keywords in priority_rules:
        if any(keyword in question for keyword in keywords):
            return label
    return "공통 문항"


def polish_question(question, label):
    question = normalize_space(question)
    if question.endswith("?"):
        return question
    if question.endswith("요"):
        return question + "?"
    if re.search(r"작성|기술|서술", question):
        return question.rstrip(".") + "."
    defaults = {
        "지원동기": "지원한 회사와 직무를 선택한 이유를 본인의 경험과 연결해 작성해주세요.",
        "직무역량": "지원 직무에 필요한 핵심 역량과 이를 실제로 적용한 경험을 작성해주세요.",
        "경험/성과": "직무와 연결되는 경험에서 맡은 역할, 실행 과정, 결과를 구체적으로 작성해주세요.",
        "도전/문제해결": "어려운 문제를 해결하기 위해 시도한 방법과 그 결과를 작성해주세요.",
        "협업/소통": "팀 안에서 역할을 나누고 의견을 조율해 공동 결과를 만든 경험을 작성해주세요.",
        "입사 후 포부": "입사 후 이루고 싶은 목표와 회사에 기여할 방법을 작성해주세요.",
    }
    return defaults.get(label, question)


def representative_question(items, label):
    preferred = sorted(
        items,
        key=lambda item: (source_weight(item["source"]), len(item["question"])),
        reverse=True,
    )[0]["question"]
    return polish_question(preferred, label)


def most_common_label(items):
    labels = Counter(question_label(item["question"]) for item in items)
    label, _ = labels.most_common(1)[0]
    return label


def cluster_question_candidates(candidates, threshold=0.32):
    clusters = []
    for candidate in candidates:
        best_cluster = None
        best_score = 0.0
        for cluster in clusters:
            score = max(question_similarity(candidate["question"], item["question"]) for item in cluster["items"])
            if score > best_score:
                best_cluster = cluster
                best_score = score
        if best_cluster and best_score >= threshold:
            best_cluster["items"].append(candidate)
        else:
            clusters.append({"items": [candidate]})

    for cluster in clusters:
        cluster["label"] = most_common_label(cluster["items"])
        cluster["score"] = sum(source_weight(item["source"]) for item in cluster["items"])
        cluster["representative"] = representative_question(cluster["items"], cluster["label"])
        cluster["sources"] = sorted({item["source"] for item in cluster["items"]})
        cluster["examples"] = [item.get("company", "") for item in cluster["items"] if item.get("company")][:3]
    clusters.sort(key=lambda cluster: (cluster["score"], len(cluster["items"])), reverse=True)
    return clusters


def question_focus_words(question, label):
    words = []
    if "팀" in question or "협업" in question:
        words.append("팀을 이뤄 협업")
    if "성과" in question:
        words.append("성과")
    if "지원" in question and "동기" in question:
        words.append("지원동기")
    if "역량" in question:
        words.append("직무역량")
    if "문제" in question or "도전" in question:
        words.append("문제해결")
    if "포부" in question or "입사 후" in question:
        words.append("입사 후 포부")
    return words or [label]


def profile_traits(structured_profile):
    profile_text = structured_profile_to_text(structured_profile).lower()
    return {
        "has_major": bool(structured_profile.get("major")),
        "has_certificates": bool(structured_profile.get("certificates")),
        "has_team_projects": bool(structured_profile.get("team_projects")),
        "has_other_specs": bool(structured_profile.get("other_specs")),
        "has_ai": any(keyword in profile_text for keyword in ["ai", "인공지능", "머신러닝", "딥러닝", "rag", "cnn"]),
        "has_data": any(keyword in profile_text for keyword in ["데이터", "분석", "sql", "통계", "시각화"]),
        "has_backend": any(keyword in profile_text for keyword in ["api", "spring", "fastapi", "서버", "백엔드", "db", "mysql"]),
        "has_quant_result": bool(re.search(r"\d|%|명|건|회|개월|년", profile_text)),
    }


def personalized_question_templates(target_job, structured_profile):
    job_name = target_job or "지원 직무"
    traits = profile_traits(structured_profile)
    questions = []

    if traits["has_ai"]:
        questions.append(("지원동기", f"AI/RAG/CNN 등 기술 경험을 바탕으로 {job_name}{josa(job_name, '을', '를')} 선택한 이유와 앞으로 해결하고 싶은 문제를 작성해주세요."))
    elif traits["has_major"]:
        questions.append(("지원동기", f"전공 학습을 바탕으로 {job_name}에 관심을 갖게 된 계기와 지원 동기를 작성해주세요."))
    else:
        questions.append(("지원동기", f"{job_name}에 지원한 동기와 이 직무를 선택하게 된 계기를 작성해주세요."))

    if traits["has_team_projects"] and traits["has_backend"]:
        questions.append(("직무역량", f"팀프로젝트에서 구현한 기능과 API/서버 경험을 중심으로 {job_name} 수행 역량을 작성해주세요."))
    elif traits["has_certificates"]:
        questions.append(("직무역량", f"전공 지식과 자격증 준비 경험을 실제 프로젝트에 어떻게 연결했는지 {job_name} 역량 중심으로 작성해주세요."))
    elif traits["has_other_specs"]:
        questions.append(("직무역량", f"수업, 실습, 사용 기술을 통해 준비한 {job_name} 핵심 역량을 구체적으로 작성해주세요."))
    else:
        questions.append(("직무역량", f"{job_name} 수행에 필요한 핵심 역량과 이를 준비해 온 과정을 작성해주세요."))

    if traits["has_quant_result"]:
        questions.append(("경험/성과", f"{job_name}와 연결되는 경험 중 수치나 결과로 설명할 수 있는 성과를 맡은 역할과 함께 작성해주세요."))
    elif traits["has_team_projects"]:
        questions.append(("경험/성과", f"팀프로젝트에서 맡은 역할과 결과물을 중심으로 {job_name}와 연결되는 성과를 작성해주세요."))
    else:
        questions.append(("경험/성과", f"{job_name}와 연결되는 프로젝트 또는 경험에서 맡은 역할과 성과를 구체적으로 작성해주세요."))

    if traits["has_team_projects"]:
        questions.append(("협업/소통", f"팀프로젝트에서 역할을 분담하거나 의견을 조율해 {job_name}와 관련된 결과를 만든 경험을 작성해주세요."))
    else:
        questions.append(("협업/소통", f"팀을 이뤄 협업하면서 {job_name}와 관련된 성과를 만들었던 경험을 작성해주세요."))

    if traits["has_ai"] and traits["has_data"]:
        questions.append(("입사 후 포부", f"데이터와 AI 기술 경험을 바탕으로 입사 후 {job_name}로서 개선하고 싶은 서비스나 업무 목표를 작성해주세요."))
    elif traits["has_certificates"] and not traits["has_team_projects"]:
        questions.append(("입사 후 포부", f"현재 보유한 전공/자격증 기반을 입사 후 {job_name} 실무 역량으로 어떻게 확장할지 작성해주세요."))
    else:
        questions.append(("입사 후 포부", f"입사 후 {job_name}로서 이루고 싶은 목표와 기여 방안을 작성해주세요."))

    return questions


def common_questions_for_job(target_job, results, structured_profile=None, company_questions="", custom_questions=None, limit=5):
    job_name = target_job or "지원 직무"
    label_examples = defaultdict(list)
    label_counts = Counter()
    candidates = []

    for question in custom_questions or []:
        question = normalize_space(question)
        if question:
            candidates.append({"question": question, "source": "custom"})

    if custom_questions:
        clusters = cluster_question_candidates(candidates)
        return [
            (cluster["representative"], max(cluster["score"], 1), cluster["examples"])
            for cluster in clusters[:limit]
        ]

    for question in split_question_items(company_questions):
        candidates.append({"question": question, "source": "company"})

    for _, document in results:
        label = question_label(document.get("question_text") or document.get("question_label") or "")
        label_counts[label] += 1
        if len(label_examples[label]) < 3 and document.get("company"):
            label_examples[label].append(document["company"])
        if document.get("question_text"):
            candidates.append(
                {
                    "question": document["question_text"],
                    "source": "retrieved",
                    "company": document.get("company", ""),
                }
            )

    for label, question in personalized_question_templates(job_name, structured_profile or {}):
        candidates.append({"question": question, "source": "template", "label": label})

    clusters = cluster_question_candidates(candidates)
    if clusters:
        questions = []
        used_labels = set()
        for cluster in clusters:
            label = cluster["label"]
            if label in used_labels and len(questions) >= 3:
                continue
            used_labels.add(label)
            examples = cluster["examples"] or label_examples[label]
            questions.append((cluster["representative"], max(label_counts[label], cluster["score"], 1), examples))
            if len(questions) >= limit:
                break
        return questions

    questions = []
    for label, question in personalized_question_templates(job_name, structured_profile or {})[:limit]:
        questions.append((question, max(label_counts[label], 1), label_examples[label]))
    return questions


def split_sentences(text):
    text = normalize_space(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s+|(?<=요\.)\s+", text)
    return [part.strip() for part in parts if len(part.strip()) >= 20]


def reference_pattern_for(label, document):
    preview_sentences = split_sentences(document.get("content", ""))[:3]
    joined = " ".join(preview_sentences)
    if label == "지원동기":
        pattern = "관심 계기 -> 직무/회사 이해 -> 보유 경험으로 기여 순서"
    elif label == "직무역량":
        pattern = "핵심 역량 정의 -> 관련 프로젝트/기술 경험 -> 실무 적용 가능성 순서"
    elif label == "경험/성과":
        pattern = "문제 상황 -> 맡은 역할과 실행 -> 결과와 직무 연결 순서"
    elif label == "협업/소통":
        pattern = "팀 목표 -> 역할 분담/조율 -> 공동 결과와 배운 점 순서"
    elif label == "입사 후 포부":
        pattern = "초기 적응 목표 -> 보유 역량 활용 -> 장기 기여 방향 순서"
    else:
        pattern = "경험 배경 -> 직접 행동 -> 결과와 직무 연결 순서"
    return {
        "company": document.get("company", ""),
        "job": document.get("job", ""),
        "question": document.get("question_text", ""),
        "label": document.get("question_label", ""),
        "usable_pattern": pattern,
        "preview": content_preview(joined or document.get("content", ""), 360),
    }


def build_reference_guides(results):
    guides = defaultdict(list)
    for _, document in results:
        labels = {question_label(document.get("question_text", "")), question_label(document.get("question_label", ""))}
        if document.get("question_label") == "입사후포부":
            labels.add("입사 후 포부")
        if document.get("question_label") == "성장/가치관":
            labels.add("성장과정")
        for label in labels:
            if label == "공통 문항" or len(guides[label]) >= 3:
                continue
            guides[label].append(reference_pattern_for(label, document))
    return guides


def build_evidence_sentence(items):
    texts = [item["text"] for item in items]
    if not texts:
        return ""
    if len(texts) == 1:
        return texts[0]
    return ", ".join(texts[:-1]) + f", 그리고 {texts[-1]}"


def evidence_by_field(items):
    grouped = defaultdict(list)
    for item in items:
        grouped[item["field_label"]].append(item["text"])
    return {label: values for label, values in grouped.items() if values}


def evidence_context_sentence(evidence_items):
    texts = [item["text"].rstrip(".") for item in evidence_items if item.get("text")]
    if not texts:
        return ""
    sentences = []
    for index, text in enumerate(texts):
        prefix = "저는 " if index == 0 and not text.startswith("저는 ") else "또한 "
        if text.endswith(("했습니다", "수행했습니다", "되었습니다", "분석했습니다", "수정했습니다", "구현했습니다")):
            sentences.append(f"{prefix}{text}.")
        else:
            sentences.append(f"{prefix}{text}을 중심으로 문제를 분석했습니다.")
    sentences.append("이 과정에서 활동명을 나열하는 데 그치지 않고, 왜 그 방법이 필요한지와 결과를 어떻게 확인할지 함께 고민했습니다.")
    return " ".join(sentences)


def evidence_texts_by_field(evidence_items):
    grouped = defaultdict(list)
    for item in evidence_items:
        grouped[item.get("field", "")].append(item.get("text", "").rstrip("."))
    return grouped


def experience_phrase(text):
    text = normalize_space(text).rstrip(".")
    replacements = [
        (r"했습니다$", "한 경험"),
        (r"수행했습니다$", "수행한 경험"),
        (r"정리했습니다$", "정리한 경험"),
        (r"분석했습니다$", "분석한 경험"),
        (r"구현했습니다$", "구현한 경험"),
        (r"수정했습니다$", "수정한 경험"),
        (r"바꿨습니다$", "바꾼 경험"),
        (r"만들었습니다$", "만든 경험"),
        (r"맡았습니다$", "맡은 경험"),
        (r"활용했습니다$", "활용한 경험"),
    ]
    for pattern, replacement in replacements:
        next_text = re.sub(pattern, replacement, text)
        if next_text != text:
            return next_text
    return text


def experience_noun(text):
    text = experience_phrase(text)
    if not text:
        return ""
    if text.endswith("경험"):
        return text
    return f"{text} 경험"


def job_role_name(target_job):
    job_name = target_job or "지원 직무"
    if job_name.endswith(("담당자", "엔지니어", "디자이너", "마케터", "간호사", "승무원")):
        return job_name
    return f"{job_name} 담당자"


def spec_focus_label(item):
    text = item.get("text", "")
    if item.get("field") == "team_projects":
        return f"핵심 활동인 {experience_noun(text)}"
    if item.get("field") == "other_specs":
        return f"이를 발전시킨 보조 경험인 {experience_noun(text)}"
    if item.get("field") == "certificates":
        return f"실무 기준을 보완한 {experience_noun(text)}"
    if item.get("field") == "major":
        return f"기초 관점을 만든 {experience_noun(text)}"
    return experience_noun(text)


def selected_specs_phrase(evidence_items):
    labels = [spec_focus_label(item) for item in evidence_items[:2] if item.get("text")]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return f"{labels[0]}{josa(labels[0], '과', '와')} {labels[1]}"


def build_experience_scene(evidence_items, label, target_job):
    grouped = evidence_texts_by_field(evidence_items)
    team = experience_phrase((grouped.get("team_projects") or [""])[0])
    supports = (grouped.get("other_specs") or [])[:2]
    certs = (grouped.get("certificates") or [])[:1]
    major = (grouped.get("major") or [])[:1]
    job_name = target_job or "지원 직무"
    terms = job_domain_terms(job_name)
    selected_phrase = selected_specs_phrase(evidence_items)
    support_sentence = ""
    if supports:
        support_sentence = f" 이 과정에서 {', '.join(experience_noun(text) for text in supports)}도 함께 다루며 판단 근거를 더 구체화했습니다."
    elif certs and label in {"직무역량", "입사 후 포부", "지원동기"}:
        support_sentence = f" {certs[0]}은 이 경험을 실무 기준으로 정리하는 보조 근거가 되었습니다."
    elif major and label in {"지원동기", "성장과정"}:
        support_sentence = f" {major[0]}은 이 관심을 직무 관점으로 확장하는 기반이 되었습니다."

    if team:
        if label == "협업/소통":
            return (
                f"이 답변에서는 {selected_phrase}{josa(selected_phrase, '을', '를')} 중심 근거로 삼았습니다."
                f" 저는 이 활동을 단순한 팀 참여 기록으로 두지 않고, 역할을 나누고 진행 상황을 맞추며 하나의 결과물로 연결하는 경험으로 발전시켰습니다."
                f"{support_sentence} 그 과정에서 배운 점은 협업의 핵심이 각자 맡은 일을 끝내는 데 그치지 않고, 서로의 작업이 이어지는 기준을 계속 맞추는 일이라는 것입니다."
            )
        if label == "직무역량":
            return (
                f"이 답변에서는 {selected_phrase}{josa(selected_phrase, '을', '를')} 직무역량의 근거로 선택했습니다."
                f" 이 활동에서 저는 경험을 단순한 과제 수행으로 두지 않고, {terms['process']}으로 발전시켰습니다."
                f"{support_sentence} 그래서 {job_name}{josa(job_name, '에서', '에서')}도 먼저 시장과 업무 조건을 나누어 보고, 실행 우선순위를 설명하는 방식으로 일할 수 있다고 생각합니다."
            )
        if label == "경험/성과":
            return (
                f"{job_name}{josa(job_name, '과', '와')} 연결해 설명할 경험으로 {selected_phrase}{josa(selected_phrase, '을', '를')} 골랐습니다."
                f" 저는 이 경험에서 제 역할이 결과물의 어느 부분에 기여하는지 확인하면서 활동을 더 구체화했고, 중간 결과를 기준으로 부족한 부분을 다시 보완했습니다."
                f"{support_sentence} 이를 통해 성과는 활동명을 많이 적는 것이 아니라, 선택한 방식과 확인한 결과를 함께 설명할 때 설득력이 생긴다는 점을 배웠습니다."
            )
        if label == "도전/문제해결":
            return (
                f"문제를 해결한 경험으로는 {selected_phrase}{josa(selected_phrase, '을', '를')} 들 수 있습니다."
                f" 처음부터 답을 정해 놓기보다 상황을 나누어 보고, 원인을 확인할 수 있는 순서대로 접근하면서 활동을 문제해결 경험으로 발전시켰습니다."
                f"{support_sentence} 이 과정에서 배운 점은 문제 해결이 한 번의 시도로 끝나는 것이 아니라 가설을 세우고 확인하며 수정하는 과정이라는 점입니다."
            )
        return (
            f"제 경험 중 {job_name}와 가장 직접적으로 연결되는 근거로 {selected_phrase}{josa(selected_phrase, '을', '를')} 선택했습니다."
            f" 이 활동을 통해 관심을 실제 행동으로 옮기고, 결과를 확인하며 다음 개선점을 찾는 방식으로 경험을 발전시켰습니다."
            f"{support_sentence}"
        )

    fallback_texts = [text for values in grouped.values() for text in values]
    if not fallback_texts:
        return ""
    return (
        f"이 답변에서는 {', '.join(fallback_texts[:2])}을 근거로 삼았습니다."
        f" 다만 단순한 보유 스펙으로 나열하기보다 {job_name}{josa(job_name, '에서', '에서')} 필요한 실행 방식과 연결해 설명하겠습니다."
    )


def reference_style_sentence(reference_examples, label):
    examples = reference_examples or []
    if not examples:
        return ""
    return ""


def job_domain_terms(target_job):
    lowered = (target_job or "").lower()
    if any(keyword in lowered for keyword in ["마케팅", "브랜드", "콘텐츠", "광고", "영업", "crm"]):
        return {
            "problem": "고객 반응과 시장 흐름",
            "tool": "캠페인과 콘텐츠 전략",
            "environment": "브랜드와 채널 운영 기준",
            "future": "고객 반응을 실행 전략으로 바꾸는 실무자",
            "result": "타깃 이해와 성과 지표",
            "capability": "고객과 시장을 나누어 보고 반응의 이유를 설명하는 힘",
            "process": "타깃, 채널, 메시지, 반응 지표를 함께 비교하는 과정",
        }
    if any(keyword in lowered for keyword in ["개발", "백엔드", "프론트", "ai", "데이터", "엔지니어", "서버", "api"]):
        return {
            "problem": "기술 문제와 서비스 흐름",
            "tool": "기술 선택과 구현 경험",
            "environment": "개발 환경과 업무 기준",
            "future": "기술을 문제 해결로 연결하는 실무자",
            "result": "구현 결과와 검증 기준",
            "capability": "문제를 구조화하고 구현 결과를 검증하는 힘",
            "process": "요구사항, 데이터 흐름, 예외 상황, 결과 확인 기준을 나누어 보는 과정",
        }
    if any(keyword in lowered for keyword in ["해외", "글로벌", "무역", "수출", "수입", "사업 운영", "사업운영", "사업개발"]):
        return {
            "problem": "국가별 시장 조건과 운영상의 제약",
            "tool": "시장조사와 유통 구조 분석 경험",
            "environment": "해외 시장과 파트너 커뮤니케이션 기준",
            "future": "시장 정보를 실행 가능한 운영 판단으로 바꾸는 실무자",
            "result": "국가별 비교 기준과 실행 우선순위",
            "capability": "시장, 유통 채널, 소비자 가격을 비교해 운영 판단으로 정리하는 힘",
            "process": "국가별 유통 구조, 가격대, 소비자 특성, 진입 조건을 나누어 비교하는 과정",
        }
    if any(keyword in lowered for keyword in ["행정", "복지", "공공", "교육"]):
        return {
            "problem": "이용자의 요구와 운영 기준",
            "tool": "절차 정리와 안내 개선 경험",
            "environment": "규정과 현장 요청이 함께 있는 업무 흐름",
            "future": "기준을 신뢰할 수 있게 설명하는 실무자",
            "result": "요청 유형과 처리 기준",
            "capability": "요청을 유형별로 나누고 가능한 범위를 분명히 설명하는 힘",
            "process": "요청 배경, 적용 기준, 예외 가능성, 안내 방식을 나누어 정리하는 과정",
        }
    return {
        "problem": "업무 상황과 사용자의 요구",
        "tool": "경험에서 얻은 실행 방식",
        "environment": "업무 흐름과 조직 기준",
        "future": "경험을 실제 성과로 연결하는 실무자",
        "result": "실행 과정과 결과",
        "capability": "업무 상황을 기준으로 나누고 실행 가능한 판단으로 정리하는 힘",
        "process": "목적, 조건, 자료, 실행 순서를 나누어 확인하는 과정",
    }


def trim_to_char_range(text, min_chars=1000, max_chars=1500):
    text = normalize_space(text).replace(". ", ".\n")
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    sentence_end = max(cut.rfind("."), cut.rfind("다."), cut.rfind("요."))
    if sentence_end >= min_chars:
        return cut[: sentence_end + 1]
    return cut.rstrip()


def expand_to_min_chars(text, label, target_job, target_company, min_chars=1100, max_chars=1500):
    job_name = target_job or "지원 직무"
    company_name = target_company or "지원 회사"
    additions = [
        "이 경험에서 제가 중요하게 생각한 것은 결과를 만들기 전까지의 과정을 스스로 설명할 수 있어야 한다는 점이었습니다. 단순히 주어진 일을 수행하는 데서 멈추면 같은 문제가 다시 생겼을 때 대응하기 어렵기 때문에, 저는 왜 그 방법을 선택했는지와 어떤 기준으로 다음 행동을 정했는지를 함께 정리하려고 했습니다.",
        f"또한 {job_name}{josa(job_name, '에서는', '에서는')} 개인이 알고 있는 지식보다 그 지식을 실제 문제에 맞게 적용하는 태도가 더 중요하다고 생각합니다. 저는 앞으로도 과제를 받을 때 먼저 목적과 제약을 이해하고, 필요한 자료를 빠르게 확인한 뒤, 동료가 이해할 수 있는 방식으로 진행 상황을 공유하겠습니다.",
        f"{company_name}에서도 이러한 방식으로 일한다면 초기에는 맡은 업무를 정확히 수행하고, 이후에는 반복되는 문제나 개선 가능한 부분을 찾아 팀에 기여할 수 있다고 생각합니다. 특히 결과를 낸 뒤에도 과정과 근거를 남기는 습관은 면접과 실무 모두에서 검증 가능한 강점이 될 것입니다.",
    ]
    if label == "협업/소통":
        additions.insert(
            1,
            "협업 과정에서는 제 역할만 끝냈다고 해서 성과가 완성되지 않는다는 점도 배웠습니다. 팀원이 맡은 부분과 제 작업이 맞물리는 지점을 확인해야 했고, 논의가 길어질 때는 기준을 다시 세워 결정해야 했습니다. 이러한 조율 과정은 최종 결과물의 완성도를 높이는 데 직접적으로 연결되었습니다.",
        )
    if label == "직무역량":
        additions.insert(
            1,
            f"직무 역량은 한 번의 활동으로 완성되는 것이 아니라 여러 경험을 통해 반복적으로 다듬어진다고 생각합니다. 그래서 저는 제가 한 활동을 기록하고, {job_name}{josa(job_name, '에서', '에서')} 필요한 기준으로 다시 정리하며, 다음 판단에 활용할 수 있는 방식으로 역량을 쌓아 왔습니다.",
        )
    expanded = text
    for addition in additions:
        if len(expanded) >= min_chars:
            break
        expanded = "\n".join([expanded, addition])
    trimmed = trim_to_char_range(expanded, min_chars, max_chars)
    if len(trimmed) < 1000:
        trimmed = "\n".join(
            [
                trimmed,
                f"따라서 이 경험은 {job_name}{josa(job_name, '에서', '에서')} 제가 어떤 방식으로 문제를 이해하고 실행하는 사람인지 보여주는 근거가 됩니다. 앞으로도 결과만 말하는 것이 아니라 그 결과를 만들기 위해 어떤 판단을 했고 어떤 행동을 했는지 설명할 수 있는 태도로 일하겠습니다.",
            ]
        )
    return trim_to_char_range(trimmed, 1000, max_chars)


def build_missing_evidence_message(question, label, target_job):
    rule = QUESTION_EVIDENCE_RULES.get(label, {})
    job_name = target_job or "지원 직무"
    return "\n".join(
        [
            "이 문항은 아직 자기소개서 초안으로 만들지 않았습니다.",
            f"질문: {question}",
            rule.get("fallback", "문항에 맞는 구체 경험을 한 가지 더 입력해야 합니다."),
            f"{job_name}{josa(job_name, '과', '와')} 연결되는 프로젝트, 실습, 인턴, 구현 경험 중 하나를 입력하면 그 경험을 중심으로 다시 생성합니다.",
        ]
    )


def join_three_paragraphs(paragraphs, label, target_job, target_company):
    job_name = target_job or "지원 직무"
    role_name = job_role_name(target_job)
    company_name = target_company or "지원 회사"
    terms = job_domain_terms(job_name)
    additions = {
        "지원동기": (
            2,
            f" 이러한 태도는 {job_name}{josa(job_name, '에서', '에서')} 새로운 문제를 만났을 때도 빠르게 배경을 이해하고 필요한 지식을 연결하는 데 도움이 된다고 생각합니다. 저는 관심을 말로만 설명하는 지원자가 아니라, 실행 경험을 근거로 기여 가능성을 보여주는 지원자가 되고 싶습니다.",
        ),
        "직무역량": (
            1,
            f" 특히 이 경험을 {job_name}{josa(job_name, '과', '와')} 연결해 다시 정리하면서, 단순히 활동을 수행했다는 사실보다 어떤 기준으로 비교했고 어떤 판단으로 이어졌는지가 더 중요하다는 점을 배웠습니다.",
        ),
        "협업/소통": (
            1,
            " 이 과정에서 중요한 것은 제 작업을 끝내는 것보다 팀원이 다음 작업을 이어갈 수 있도록 기준과 맥락을 남기는 일이었습니다. 그래서 진행 상황을 공유할 때도 단순한 완료 여부가 아니라 남은 이슈와 결정이 필요한 지점을 함께 정리했습니다.",
        ),
        "입사 후 포부": (
            2,
            f" 장기적으로는 {role_name}{josa(role_name, '으로서', '로서')} {terms['future']}가 되고 싶습니다. {company_name}의 업무 안에서도 결과를 만든 뒤 근거와 개선점을 남기는 방식으로 팀의 다음 실행에 기여하겠습니다.",
        ),
        "경험/성과": (
            2,
            f" 따라서 이 경험은 {job_name}{josa(job_name, '에서', '에서')} 제가 어떤 방식으로 문제를 이해하고 실행하는 사람인지 보여주는 근거가 됩니다. 앞으로도 결과만 말하는 것이 아니라 그 결과를 만들기 위해 어떤 판단을 했고 어떤 행동을 했는지 설명할 수 있는 태도로 일하겠습니다.",
        ),
    }
    index, addition = additions.get(label, additions["경험/성과"])
    if sum(len(paragraph) for paragraph in paragraphs) < 1050:
        paragraphs[index] += addition
    if sum(len(paragraph) for paragraph in paragraphs) < 1050:
        paragraphs[2] += f" 또한 {company_name}에서도 맡은 일을 정확히 수행하는 데서 멈추지 않고, 결과를 만든 뒤 근거와 개선점을 남기는 방식으로 {job_name}{josa(job_name, '에', '에')} 기여하겠습니다."
    if sum(len(paragraph) for paragraph in paragraphs) < 1050:
        paragraphs[1] += " 이 과정에서 배운 점은 경험을 설명할 때 단순한 활동명보다 문제를 바라본 기준, 직접 선택한 방법, 결과를 확인한 방식이 함께 드러나야 한다는 것입니다. 그래서 저는 스펙을 나열하기보다 그 스펙이 실제 행동으로 이어진 장면을 중심으로 정리했습니다."
    if sum(len(paragraph) for paragraph in paragraphs) < 1050:
        paragraphs[2] += f" 앞으로도 {job_name}{josa(job_name, '에서', '에서')} 새로운 과제를 맡게 되면 먼저 목적을 이해하고, 제가 맡은 역할을 분명히 한 뒤, 결과를 확인하며 다음 개선점을 남기는 방식으로 일하겠습니다."
    joined = "\n\n".join(trim_to_char_range(paragraph, 250, 720) for paragraph in paragraphs[:3])
    if len(joined) > 1500:
        parts = joined.split("\n\n")
        parts[2] = trim_to_char_range(parts[2], 250, max(250, 1500 - len(parts[0]) - len(parts[1]) - 4))
        joined = "\n\n".join(parts)
    if len(joined) < 1000:
        parts = joined.split("\n\n")
        parts[2] += f" 이처럼 저는 경험을 단순한 이력으로 두지 않고, {job_name}{josa(job_name, '에서', '에서')} 다시 활용할 수 있는 일하는 방식으로 정리해 왔습니다."
        joined = "\n\n".join(parts)
    return joined


def build_answer_paragraph(question, label, evidence_items, signals, target_company, target_job, reference_examples=None):
    job_name = target_job or "지원 직무"
    role_name = job_role_name(target_job)
    company_name = target_company or "지원 회사"
    terms = job_domain_terms(job_name)
    signal_text = ", ".join(signals[:3])
    evidence_sentence = build_experience_scene(evidence_items, label, target_job) or evidence_context_sentence(evidence_items)
    reference_sentence = reference_style_sentence(reference_examples, label)
    if label == "지원동기":
        paragraphs = [
            f"{company_name}에 지원한 이유는 {job_name}{josa(job_name, '이라는', '라는')} 직무가 제가 다뤄 온 경험을 {terms['problem']} 해결로 확장할 수 있는 자리라고 판단했기 때문입니다. 저는 관심을 말로 설명하는 것보다 그 관심을 실제 작업으로 옮긴 과정을 중요하게 생각합니다.",
            f"{reference_sentence} {evidence_sentence} 이를 바탕으로 {job_name}{josa(job_name, '에', '에')} 필요한 문제 정의와 실행 방식을 익혀 왔습니다. 특히 {terms['tool']}{josa(terms['tool'], '을', '를')} 단순히 알고 있는 데서 멈추지 않고, 필요한 자료를 찾고 적용 가능한 방법을 비교하며 결과를 확인하는 과정을 반복했습니다.",
            f"이 경험을 통해 제가 {job_name}{josa(job_name, '에서', '에서')} 기여할 수 있는 지점은 경험을 말로 설명하는 데서 끝내지 않고 {terms['result']}{josa(terms['result'], '으로', '로')} 연결하는 태도라고 생각합니다. {company_name}에서도 업무의 배경을 먼저 파악하고, 제가 가진 {signal_text} 역량을 바탕으로 신뢰할 수 있는 결과를 만들겠습니다.",
        ]
    elif label == "직무역량":
        paragraphs = [
            f"이 문항에서 보여주고 싶은 역량은 {terms['capability']}입니다. {job_name}{josa(job_name, '에서는', '에서는')} 단순히 경험을 많이 했다는 사실보다, 그 경험을 업무 판단에 필요한 기준으로 정리할 수 있는지가 중요하다고 생각합니다.",
            f"{reference_sentence} {evidence_sentence} 이 과정에서는 활동명을 나열하는 데서 멈추지 않고, {terms['process']}으로 경험을 다시 정리했습니다. 특히 어떤 자료를 먼저 보고, 어떤 기준으로 비교해야 실제 업무에 도움이 되는지 고민했습니다.",
            f"이러한 경험은 {job_name}{josa(job_name, '에서', '에서')} 요구되는 실무 태도와 연결됩니다. 실무에서는 정답이 정해진 과제보다 시장, 고객, 조직, 일정처럼 여러 조건을 함께 해석해야 하는 상황이 많기 때문입니다. 저는 앞으로도 경험을 단순한 이력으로 두지 않고, {terms['result']}{josa(terms['result'], '을', '를')} 설명할 수 있는 {role_name}가 되겠습니다.",
        ]
    elif label == "경험/성과":
        paragraphs = [
            f"{job_name}{josa(job_name, '과', '와')} 연결되는 경험에서는 활동 자체보다 맡은 역할과 실행 과정을 먼저 드러내는 것이 중요하다고 생각합니다. {reference_sentence} {evidence_sentence}",
            f"이 경험에서 저는 맡은 역할을 기준으로 해야 할 일을 나누고, 결과가 막연한 느낌으로 끝나지 않도록 중간 산출물을 확인했습니다. 부족한 부분은 다시 자료를 찾아 보완했고, {terms['process']}을 기준으로 제가 담당한 부분이 최종 결과물 안에서 어떤 역할을 하는지 계속 확인했습니다.",
            f"이 과정에서 얻은 성과는 단순히 활동을 완료했다는 점이 아니라 {signal_text} 역량을 실제 행동으로 확인했다는 점입니다. 앞으로 {job_name}{josa(job_name, '에서도', '에서도')} 같은 방식으로 문제를 정의하고, 맡은 역할을 분명히 수행하며, 결과로 설명할 수 있는 경험을 계속 만들겠습니다.",
        ]
    elif label == "협업/소통":
        paragraphs = [
            "팀을 이뤄 협업하면서 성과를 만들기 위해서는 각자가 맡은 일을 잘하는 것뿐 아니라 서로의 작업이 하나의 결과로 이어지도록 맞추는 과정이 중요하다고 생각합니다. 이 문항에서는 개인 스펙보다 팀 안에서 맡은 역할과 조율 과정을 중심으로 말씀드리겠습니다.",
            f"{reference_sentence} {evidence_sentence} 이 과정에서 제 역할을 먼저 분명히 하고, 팀원과 역할을 나눈 뒤 진행 상황을 공유하며 작업했습니다. 의견이 다르거나 일정이 어긋날 때는 논의 내용을 막연히 넘기지 않고 기준을 정리해 다시 확인했습니다.",
            f"그 결과 각자의 작업이 따로 흩어지지 않고 최종 결과물 안에서 자연스럽게 연결될 수 있었습니다. 이 경험을 통해 협업은 단순히 함께 일하는 것이 아니라 공동 목표를 기준으로 역할, 일정, 결과물을 계속 조율하는 과정이라는 점을 배웠습니다. {job_name}{josa(job_name, '에서도', '에서도')} 동료와 맥락을 공유하며 팀 성과에 기여하겠습니다.",
        ]
    else:
        paragraphs = [
            f"입사 후에는 {job_name}의 업무 흐름을 빠르게 익히고, 제가 쌓아 온 경험을 실제 성과로 연결하고 싶습니다. 막연한 성장 의지보다 초기 실행과 장기 기여 방향을 나누어 설명하는 것이 더 설득력 있다고 생각합니다.",
            f"{reference_sentence} {evidence_sentence} 이 과정에서 배운 것은 새로운 업무를 맡았을 때 먼저 목적을 이해하고, 필요한 자료와 실행 방법을 연결한 뒤 결과를 확인하는 방식입니다. 초기에는 {company_name}의 {terms['environment']}{josa(terms['environment'], '을', '를')} 정확히 익히고, 주어진 과제를 안정적으로 수행하는 데 집중하겠습니다.",
            f"이후에는 반복되는 문제나 개선 가능한 지점을 기록하고, 동료와 공유할 수 있는 형태로 정리해 팀의 생산성에 기여하고 싶습니다. 장기적으로는 {role_name}{josa(role_name, '으로서', '로서')} {terms['future']}가 되겠습니다.",
        ]
    return join_three_paragraphs(paragraphs, label, target_job, target_company)


def build_cover_letter_drafts(questions, structured_profile, target_company, target_job, reference_guides=None):
    profile_text = structured_profile_to_text(structured_profile)
    signals = infer_profile_signals(profile_text)
    drafts = []
    for index, (question, count, companies) in enumerate(questions[:5], start=1):
        label = question_label(question)
        evidence_items = select_evidence_items(structured_profile, label)
        evidence_status = "matched" if evidence_items else "needs_input"
        draft = (
            build_answer_paragraph(question, label, evidence_items, signals, target_company, target_job, (reference_guides or {}).get(label, []))
            if evidence_items
            else build_missing_evidence_message(question, label, target_job)
        )
        drafts.append(
            {
                "index": index,
                "question": question,
                "label": label,
                "draft_type": "cover_letter" if evidence_items else "needs_input",
                "evidence_status": evidence_status,
                "evidence_items": evidence_items,
                "applied_evidence": [
                    f"{item.get('field_label', '스펙')}: {item.get('text', '')}"
                    for item in evidence_items
                    if item.get("text")
                ],
                "source_count": count,
                "example_companies": companies,
                "reference_examples": (reference_guides or {}).get(label, []),
                "draft": draft,
                "draft_chars": len(draft),
                "target_chars": "1000-1500" if evidence_items else "입력 보완 후 생성",
                "missing_information": []
                if evidence_items
                else [
                    f"상황, 맡은 역할, 직접 한 행동, 결과, {target_job or '지원 직무'}와의 연결",
                ],
                "missing_input_prompt": "" if evidence_items else f"상황, 맡은 역할, 직접 한 행동, 결과, {target_job or '지원 직무'}와의 연결을 한 가지 경험으로 입력해 주세요.",
                "edit_notes": (
                    [
                        "문항에 없는 스펙은 억지로 넣지 않습니다.",
                        "문항별로 가장 맞는 스펙 2개만 골라 직무 연결과 배운 점으로 풀어 씁니다.",
                        "팀/협업 문항은 팀프로젝트 작업만 우선 사용합니다.",
                        "자격증은 직무역량/포부 보조 근거로만 사용합니다.",
                    ]
                    if evidence_items
                    else [
                        "현재는 초안을 생성하지 않고 입력 보완 상태로 표시합니다.",
                        "LLM API에도 이 문항을 보내지 않아 없는 경험을 만들지 않습니다.",
                    ]
                ),
            }
        )
    return drafts


def build_interview_plan(drafts, profile_text, target_job):
    signals = infer_profile_signals(profile_text)
    job_name = target_job or "지원 직무"
    base_questions = [
        f"{job_name}을 선택한 이유를 본인 경험과 연결해서 설명해 주세요.",
        "자기소개서에 쓴 경험에서 본인이 직접 맡은 역할은 무엇이었나요?",
        "성과를 판단한 기준이나 사용한 지표가 있었나요?",
        "비슷한 문제가 다시 생기면 어떤 점을 다르게 하겠습니까?",
        f"{job_name}에서 입사 후 가장 먼저 보완해야 할 역량은 무엇이라고 생각하나요?",
    ]
    draft_questions = []
    used_labels = set()
    for draft in drafts:
        label = draft["label"]
        if label in used_labels:
            continue
        used_labels.add(label)
        draft_questions.append(f"{label}에 쓴 핵심 경험을 1분 안에 말해 주세요.")
        if len(draft_questions) >= 3:
            break
    return {
        "focus_areas": signals,
        "questions": draft_questions + [
            f"{job_name}{josa(job_name, '을', '를')} 선택한 이유를 본인 경험과 연결해서 설명해 주세요."
            if question.startswith(f"{job_name}을 선택한 이유") else question
            for question in base_questions
        ],
        "answer_rule": "답변은 상황-역할-행동-결과-직무연결 순서로 60~90초 안에 말하도록 준비합니다.",
    }


def build_interview_api_seed(drafts, interview_plan, target_company, target_job, profile_text, structured_profile):
    demographic_options = {
        "age": structured_profile.get("age", ""),
        "gender": structured_profile.get("gender", ""),
        "usage": "선택된 경우에만 면접 데이터셋 비교 필터로 사용하고, 자기소개서 본문 생성 근거로는 사용하지 않습니다.",
    }
    return {
        "target_company": target_company,
        "target_job": target_job,
        "profile_summary": content_preview(profile_text, 700),
        "structured_profile": structured_profile,
        "demographic_options": demographic_options,
        "cover_letter_questions": [
            {"question": draft["question"], "label": draft["label"], "draft": draft["draft"]}
            for draft in drafts
        ],
        "interview_focus_areas": interview_plan["focus_areas"],
        "initial_interview_questions": interview_plan["questions"],
        "answer_rule": interview_plan["answer_rule"],
    }
