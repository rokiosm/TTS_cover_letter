import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "linkareer_1to740.csv"
OUTPUT_DIR = ROOT / "categories"
TAXONOMY_PATH = ROOT / "category" / "job_taxonomy.json"

FIELDS = ["기간", "회사", "직무", "유형", "스펙", "내용", "링크"]

JOB_TAXONOMY = [
    ("IT·개발", "백엔드 개발", "Java, Spring, Node.js, Python, API 개발", ["백엔드", "서버", "API", "Java", "Spring", "Node", "Python", "SW개발", "sw개발", "개발"]),
    ("IT·개발", "프론트엔드 개발", "React, Vue, Angular, 웹 퍼블리싱", ["프론트", "웹", "React", "Vue", "Angular", "퍼블리싱"]),
    ("IT·개발", "모바일 개발", "Android, iOS, Flutter", ["Android", "iOS", "Flutter", "모바일", "앱 개발"]),
    ("IT·개발", "AI·머신러닝", "머신러닝, 딥러닝, 생성형 AI", ["AI", "머신러닝", "딥러닝", "ML", "생성형"]),
    ("IT·개발", "데이터 엔지니어링", "ETL, 데이터 파이프라인, 데이터 웨어하우스", ["데이터 엔지니어", "ETL", "파이프라인", "웨어하우스"]),
    ("IT·개발", "데이터 분석", "데이터 분석가, BI, 통계 분석", ["데이터 분석", "BI", "통계", "데이터"]),
    ("IT·개발", "클라우드·인프라", "AWS, Azure, DevOps, Kubernetes", ["클라우드", "인프라", "DevOps", "AWS", "Azure", "Kubernetes", "Infra", "네트워크", "ICT", "IT 서비스"]),
    ("IT·개발", "보안", "정보보안, 모의해킹, 보안관제", ["보안", "모의해킹", "보안관제"]),
    ("IT·개발", "게임 개발", "클라이언트, 서버, 엔진 개발", ["게임", "엔진", "클라이언트"]),
    ("경영·사무", "기획", "사업기획, 전략기획", ["기획", "전략", "사업기획", "Biz Dev", "PMO", "사업관리", "경영관리"]),
    ("경영·사무", "인사", "채용, 교육, 조직관리", ["인사", "HR", "채용", "교육", "조직"]),
    ("경영·사무", "총무", "자산관리, 문서관리", ["총무", "자산", "문서", "사무", "행정", "경영지원", "경영지원직", "일반관리"]),
    ("경영·사무", "재무·회계", "회계, 세무, 재무관리", ["재무", "회계", "세무", "원가", "자금", "IR", "재경"]),
    ("경영·사무", "법무", "법무, 준법, 컴플라이언스", ["법무", "준법", "컴플라이언스", "감사"]),
    ("마케팅·광고", "디지털 마케팅", "SNS, 퍼포먼스 마케팅", ["퍼포먼스", "디지털", "SNS", "CRM", "그로스"]),
    ("마케팅·광고", "콘텐츠 마케팅", "블로그, 유튜브, 카피라이팅", ["콘텐츠", "블로그", "유튜브", "카피", "에디터"]),
    ("마케팅·광고", "브랜드 마케팅", "브랜드 전략, 캠페인", ["브랜드", "마케팅", "캠페인", "PR", "홍보"]),
    ("영업·고객관리", "B2B 영업", "기업영업", ["B2B", "기업영업", "법인영업", "해외영업", "영업"]),
    ("영업·고객관리", "B2C 영업", "일반 소비자 영업", ["B2C", "리테일", "판매", "영업관리", "MD", "유통", "매장관리", "Food Sales", "식자재"]),
    ("영업·고객관리", "고객지원", "CS, 고객 상담", ["CS", "CX", "고객", "상담", "Customer Success"]),
    ("디자인", "UI/UX 디자인", "웹·앱 디자인", ["UI", "UX", "웹디자인", "앱 디자인"]),
    ("디자인", "그래픽 디자인", "편집, 브랜딩", ["그래픽", "브랜딩", "편집", "Creative Visual"]),
    ("디자인", "영상 디자인", "영상 편집, 모션그래픽", ["영상", "모션", "편집"]),
    ("생산·품질", "생산관리", "제조 운영", ["생산관리", "생산기술", "공정", "제조", "설비", "생산", "생산운영", "생산지원", "양산기술", "양산/기술"]),
    ("생산·품질", "품질관리", "QA, QC", ["품질", "QA", "QC", "품질관리", "품질보증"]),
    ("연구개발", "연구원", "신기술 연구", ["연구개발", "R&D", "연구원", "설계", "소재", "화학", "연구", "제품개발", "기구개발"]),
    ("연구개발", "전기·전자·반도체", "전기, 전자, 반도체, 회로, 소자", ["전기", "전자", "반도체", "메모리", "LSI", "DS", "소자", "HW", "회로", "파운드리"]),
    ("연구개발", "기계·항공", "기계, 항공우주, 기구", ["기계", "항공", "항공우주", "항공기술", "기구"]),
    ("연구개발", "데이터 사이언스", "AI 연구, 알고리즘 연구", ["데이터 사이언스", "알고리즘", "AI 연구"]),
    ("교육", "교육기획", "교육 콘텐츠 개발", ["교육기획", "교육 콘텐츠", "교육운영"]),
    ("교육", "강의·교수", "교원, 강사", ["강사", "교수", "교원", "강의"]),
    ("금융", "금융일반", "은행, 증권, 보험, 카드, 여신", ["금융", "은행", "증권", "보험", "카드", "여신", "투자"]),
    ("물류·구매", "SCM·물류", "공급망, 물류운영", ["SCM", "물류", "공급망", "CL"]),
    ("물류·구매", "구매", "구매, 조달", ["구매", "조달"]),
    ("건설·환경", "건축·토목", "건축, 토목, 플랜트, BIM", ["건축", "토목", "플랜트", "BIM", "시공"]),
    ("엔지니어링", "장비 엔지니어", "Customer Engineer, Field Engineer", ["Customer Engineer", "장비", "CE", "Field Engineer", "필드", "엔지니어", "기술직"]),
    ("엔지니어링", "안전·환경", "안전관리, 환경관리, 공무", ["안전", "안전관리", "환경", "공무"]),
    ("공공·행정", "공공행정", "공공기관, 정책, 일반행정", ["공공", "정책", "행정", "공기업"]),
    ("미디어·콘텐츠", "콘텐츠 제작", "PD, 영상, 방송, 작가", ["PD", "방송", "제작", "작가", "콘텐츠 제작"]),
    ("서비스", "항공·운송 서비스", "객실승무원, 운송 서비스", ["객실승무원", "승무원", "항공서비스"]),
    ("서비스", "매장·현장 서비스", "현장 운영, 서비스 관리", ["서비스", "멀티플렉스", "매니저", "SM"]),
    ("의료·보건", "간호", "간호사, 간호직", ["간호", "간호사", "간호직"]),
    ("기타", "일반·미분류", "일반직, 인턴, 직무 미상", ["-", "일반", "일반직", "청년인턴"]),
]

TOP5_SCHOOLS = ["서울대", "서울대학교", "연세대", "연세대학교", "고려대", "고려대학교", "카이스트", "KAIST", "포스텍", "POSTECH"]
IN_SEOUL_HINTS = ["서강대", "성균관대", "한양대", "중앙대", "경희대", "한국외대", "서울시립대", "이화여대", "건국대", "동국대", "홍익대", "숙명여대", "국민대", "숭실대", "세종대", "광운대", "명지대", "상명대", "서성한", "중경외시", "건동홍", "국숭세단", "인서울"]
FOREIGN_SCHOOL_HINTS = ["해외", "미국", "중국", "일본", "영국", "캐나다", "호주", "유학"]

MAJOR_GROUPS = [
    ("경영경제", ["경영", "경제", "회계", "세무", "무역", "금융", "마케팅", "국제통상", "글로벌경제"]),
    ("사회과학", ["사회", "정치", "외교", "행정", "심리", "사회복지", "언론", "광고홍보", "미디어", "커뮤니케이션"]),
    ("인문어문", ["국문", "영문", "어문", "문학", "사학", "철학", "러시아", "독일", "중국", "일본", "프랑스", "스페인"]),
    ("법행정", ["법학", "경찰", "공공인재", "정책"]),
    ("공학", ["공학", "기계", "전기", "전자", "화학공", "산업공", "신소재", "반도체", "건축", "토목", "환경공"]),
    ("IT컴퓨터", ["컴퓨터", "소프트웨어", "정보통신", "데이터", "인공지능", "AI", "통계"]),
    ("자연과학", ["수학", "물리", "화학", "생명", "바이오", "식품", "지구", "과학"]),
    ("의약보건간호", ["의학", "약학", "간호", "보건", "치위생", "물리치료", "임상"]),
    ("예체능디자인", ["디자인", "예술", "미술", "체육", "음악", "영상", "패션"]),
    ("교육", ["교육", "교직", "사범"]),
]

LICENSE_KEYWORDS = ["한국사", "컴퓨터활용능력", "컴활", "워드", "MOS", "운전면허", "ADsP", "SQLD", "SQLP", "빅데이터분석기사", "정보처리", "투자자산운용사", "재경관리사", "전산회계", "전산세무", "세무", "회계", "ERP", "사회조사분석사", "6시그마", "GTQ", "기사", "산업기사", "Certified", "자격증"]


def read_source_rows():
    with SOURCE.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        missing = [field for field in FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing columns in {SOURCE}: {', '.join(missing)}")
        return list(reader)


def write_rows(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def split_spec(spec):
    return [part.strip() for part in re.split(r"\s+/\s+", spec or "") if part.strip()]


def school_category(school):
    upper = school.upper()
    if any(name.upper() in upper for name in TOP5_SCHOOLS):
        return "Top5"
    if any(name in school for name in IN_SEOUL_HINTS):
        return "인서울"
    if any(name in school for name in FOREIGN_SCHOOL_HINTS):
        return "해외대"
    if any(token in school for token in ["지방", "지거국", "국립대", "전문대"]):
        return "지방대"
    if "대" in school or "대학교" in school:
        return "지방대"
    return "기타"


def major_group(major):
    for group, keywords in MAJOR_GROUPS:
        if any(keyword.lower() in major.lower() for keyword in keywords):
            return group
    return "기타" if major else ""


def language_fields(parts):
    joined = " / ".join(parts)
    patterns = {
        "TOEIC": r"(?:토익|TOEIC)(?!스피킹| Speaking)\s*[: ]?\s*([0-9]{2,4})",
        "OPIc": r"(?:오픽|OPIc)\s*[: ]?\s*([A-Z]{1,2}[0-9]?|AL|IH|IM[1-3]?|IL|NH|NM|NL)",
        "TOEFL": r"(?:토플|TOEFL)\s*[: +]?\s*([0-9]{2,3})",
        "IELTS": r"(?:아이엘츠|IELTS)\s*[: ]?\s*([0-9.]+)",
    }
    found = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, joined, re.I)
        found[key] = match.group(1) if match else ""

    language_parts = [part for part in parts if re.search(r"토익|TOEIC|오픽|OPIc|토플|TOEFL|아이엘츠|IELTS|토익스피킹|TOEIC Speaking|JLPT|HSK|어학", part, re.I)]
    found["기타어학"] = ", ".join(part for part in language_parts if not re.search(r"토익|TOEIC|오픽|OPIc|토플|TOEFL|아이엘츠|IELTS", part, re.I))
    return found


def collect_language_certificates(parts):
    languages = language_fields(parts)
    values = []
    for label in ["TOEIC", "OPIc", "TOEFL", "IELTS"]:
        if languages[label]:
            values.append(f"{label} {languages[label]}")

    joined = " / ".join(parts)
    for label, pattern in [
        ("토익스피킹", r"(?:토익스피킹|TOEIC Speaking)\s*[: ]?\s*([^,/]+(?:/[^,/]+)?)"),
        ("JLPT", r"JLPT\s*[: ]?\s*(N[1-5])"),
        ("HSK", r"HSK\s*[: ]?\s*([0-9]급?)"),
    ]:
        match = re.search(pattern, joined, re.I)
        if match:
            values.append(f"{label} {match.group(1).strip()}")

    if languages["기타어학"]:
        values.append(languages["기타어학"])
    return ", ".join(values)


def collect_intern(parts):
    return " / ".join(part for part in parts if "인턴" in part)


def collect_licenses(parts):
    licenses = []
    for part in parts:
        if any(keyword.lower() in part.lower() for keyword in LICENSE_KEYWORDS):
            licenses.append(part)
        elif part.startswith("기타:"):
            licenses.append(part)
    return " / ".join(licenses)


def other_spec(parts):
    excluded = set(parts[:2])
    excluded.update(part for part in parts if "학점" in part)
    excluded.update(part for part in parts if re.search(r"토익|TOEIC|오픽|OPIc|토플|TOEFL|아이엘츠|IELTS|토익스피킹|JLPT|HSK|어학", part, re.I))
    excluded.update(part for part in parts if "인턴" in part)
    excluded.update(part for part in parts if any(keyword.lower() in part.lower() for keyword in LICENSE_KEYWORDS) or part.startswith("기타:"))
    return " / ".join(part for part in parts if part not in excluded)


def classify_job(job, company="", kind=""):
    text = f"{company} {job} {kind}".lower()
    best = None
    best_score = 0
    for large, medium, small, keywords in JOB_TAXONOMY:
        score = sum(1 for keyword in keywords if keyword.lower() in text)
        if score > best_score:
            best = (large, medium, small)
            best_score = score
    if best:
        confidence = "상" if best_score >= 2 else "중"
        return (*best, confidence, "")
    return ("기타", "일반·미분류", "일반직, 인턴, 직무 미상", "하", "키워드 미매칭")


def build_job_rows(rows):
    job_rows = []
    for source_row_number, row in enumerate(rows, start=2):
        job = row.get("직무", "")
        large, medium, small, confidence, note = classify_job(job, row.get("회사", ""), row.get("유형", ""))
        job_rows.append(
            {
                "원본행": source_row_number,
                "기간": row.get("기간", ""),
                "회사": row.get("회사", ""),
                "직무": job,
                "zeroshot_input": f"회사: {row.get('회사', '')} | 직무: {job} | 유형: {row.get('유형', '')}",
                "직무_대분류": large,
                "직무_중분류": medium,
                "직무_소분류": small,
                "분류확신도": confidence,
                "검토메모": note,
                "링크": row.get("링크", ""),
            }
        )
    return job_rows


def build_spec_rows(rows):
    spec_rows = []
    for row in rows:
        spec = row.get("스펙", "")
        parts = split_spec(spec)
        school = parts[0] if len(parts) >= 1 else ""
        major = parts[1] if len(parts) >= 2 else ""
        spec_rows.append(
            {
                "기간": row.get("기간", ""),
                "회사": row.get("회사", ""),
                "스펙": spec,
                "학교_원문": school,
                "학교_분류": school_category(school),
                "학과_원문": major,
                "학과_계열": major_group(major),
                "자격증": collect_language_certificates(parts),
                "기타자격증": collect_licenses(parts),
                "인턴": collect_intern(parts),
                "기타": other_spec(parts),
            }
        )
    return spec_rows


def write_taxonomy():
    taxonomy = {}
    for large, medium, small, keywords in JOB_TAXONOMY:
        taxonomy.setdefault(large, {}).setdefault(medium, [])
        item = {"소분류": small, "분류키워드": keywords}
        if item not in taxonomy[large][medium]:
            taxonomy[large][medium].append(item)
    TAXONOMY_PATH.write_text(
        json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    rows = read_source_rows()
    OUTPUT_DIR.mkdir(exist_ok=True)
    job_rows = build_job_rows(rows)
    spec_rows = build_spec_rows(rows)

    write_rows(
        OUTPUT_DIR / "직무_카테고리.csv",
        ["원본행", "기간", "회사", "직무", "zeroshot_input", "직무_대분류", "직무_중분류", "직무_소분류", "분류확신도", "검토메모", "링크"],
        job_rows,
    )
    write_rows(
        OUTPUT_DIR / "스펙_카테고리.csv",
        ["기간", "회사", "스펙", "학교_원문", "학교_분류", "학과_원문", "학과_계열", "자격증", "기타자격증", "인턴", "기타"],
        spec_rows,
    )
    write_taxonomy()

    print(f"source_rows={len(rows)}")
    print(f"job_rows={len(job_rows)}")
    print(f"spec_rows={len(spec_rows)}")
    print(f"taxonomy_rows={len(JOB_TAXONOMY)}")


if __name__ == "__main__":
    main()
