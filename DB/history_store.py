import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "DB"
DB_PATH = DB_DIR / "interview_history.sqlite3"


def compact_piece(text):
    return " ".join((text or "").replace("\n", " ").split()).strip().rstrip(".")


def has_final_consonant(text):
    text = compact_piece(text)
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


def experience_phrase(text):
    text = compact_piece(text)
    replacements = [
        ("했습니다", "한 경험"),
        ("정리했습니다", "정리한 경험"),
        ("분석했습니다", "분석한 경험"),
        ("구현했습니다", "구현한 경험"),
        ("수정했습니다", "수정한 경험"),
        ("제안했습니다", "제안한 경험"),
        ("만들었습니다", "만든 경험"),
        ("맡았습니다", "맡은 경험"),
        ("활용했습니다", "활용한 경험"),
    ]
    for suffix, replacement in replacements:
        if text.endswith(suffix):
            return text[: -len(suffix)] + replacement
    return text


def experience_noun(text):
    text = experience_phrase(text)
    if not text:
        return ""
    if text.endswith("경험"):
        return text
    return f"{text} 경험"


def choose_two_history_specs(major, certificates, team_projects, other_specs):
    candidates = [
        ("핵심 활동", team_projects, 40),
        ("보조 활동", other_specs, 30),
        ("직무 기반", certificates, 15),
        ("전공 기반", major, 10),
    ]
    selected = []
    for label, text, _score in sorted(candidates, key=lambda item: item[2], reverse=True):
        text = compact_piece(text)
        if text and text not in [item["text"] for item in selected]:
            selected.append({"label": label, "text": text, "phrase": experience_noun(text)})
        if len(selected) >= 2:
            break
    return selected


def history_domain_terms(target_job):
    lowered = (target_job or "").lower()
    if any(keyword in lowered for keyword in ["마케팅", "브랜드", "콘텐츠", "광고", "영업", "crm"]):
        return {
            "work": "고객 반응을 읽고 다음 실행으로 바꾸는 일",
            "develop": "반응 지표와 메시지 구조를 함께 보며 개선 기준을 세우는 방식",
            "lesson": "성과는 감각이 아니라 타깃, 채널, 반응 근거가 연결될 때 설득력을 얻는다는 점",
        }
    if any(keyword in lowered for keyword in ["개발", "백엔드", "프론트", "데이터", "ai", "분석", "엔지니어", "api"]):
        return {
            "work": "문제를 동작하는 구조와 검증 가능한 결과로 바꾸는 일",
            "develop": "요구사항을 기능, 데이터, 예외 흐름으로 나누어 확인하는 방식",
            "lesson": "기술은 많이 아는 것보다 문제에 맞게 선택하고 결과를 설명할 수 있을 때 역량이 된다는 점",
        }
    if any(keyword in lowered for keyword in ["행정", "복지", "공공", "교육"]):
        return {
            "work": "사람의 불편을 줄이고 기준을 신뢰할 수 있게 설명하는 일",
            "develop": "요청을 유형별로 정리하고 가능한 범위와 절차를 분명히 남기는 방식",
            "lesson": "친절함만큼이나 일관된 기준과 기록이 신뢰를 만든다는 점",
        }
    if any(keyword in lowered for keyword in ["연구", "제품", "바이오", "품질", "생산", "제조"]):
        return {
            "work": "조건을 나누어 확인하고 재현 가능한 결과를 만드는 일",
            "develop": "측정 조건, 원인 후보, 기록 방식을 분리해 검증하는 방식",
            "lesson": "좋은 결과보다 다시 확인할 수 있는 과정과 기록이 실무의 신뢰를 만든다는 점",
        }
    if any(keyword in lowered for keyword in ["디자인", "ux", "ui", "디자이너"]):
        return {
            "work": "사용자의 불편을 발견하고 화면과 메시지로 해결하는 일",
            "develop": "감각보다 문제 정의, 피드백, 적용 매체를 기준으로 시안을 다듬는 방식",
            "lesson": "좋아 보이는 결과보다 왜 필요한지 설명할 수 있는 근거가 디자인의 설득력을 만든다는 점",
        }
    return {
        "work": "업무 상황을 이해하고 실행 가능한 결과로 연결하는 일",
        "develop": "목적과 제약을 먼저 확인한 뒤 필요한 자료와 실행 순서를 정리하는 방식",
        "lesson": "스펙은 보유 사실보다 실제 행동과 판단 기준으로 이어질 때 강점이 된다는 점",
    }


def build_cover_letter(occupation, target_job, major, certificates, team_projects, other_specs):
    selected_specs = choose_two_history_specs(major, certificates, team_projects, other_specs)
    terms = history_domain_terms(target_job)
    first = selected_specs[0] if selected_specs else {"label": "핵심 활동", "text": target_job, "phrase": f"{target_job} 관련 경험"}
    second = selected_specs[1] if len(selected_specs) > 1 else {"label": "보조 활동", "text": major or certificates, "phrase": experience_phrase(major or certificates)}
    return "\n\n".join(
        [
            f"저는 {target_job}{josa(target_job, '을', '를')} 단순히 맡은 일을 처리하는 직무가 아니라 {terms['work']}이라고 이해하고 있습니다. 그 관점에서 제 스펙 중 가장 먼저 선택한 것은 {first['phrase']}입니다. 이 활동을 통해 직무와 맞닿은 문제를 직접 다뤄 보며, 결과를 만들기 전 어떤 기준으로 상황을 봐야 하는지 익혔습니다.",
            f"두 번째로 연결한 스펙은 {second['phrase']}입니다. 이 경험은 앞선 활동을 보완하면서 {terms['develop']}으로 제 경험을 더 발전시키는 계기가 되었습니다. 그래서 자기소개서에서도 여러 이력을 한꺼번에 나열하기보다, 두 경험이 어떻게 이어져 {target_job}에 필요한 실행 방식으로 확장됐는지를 중심으로 설명하려고 합니다.",
            f"이 과정에서 배운 점은 {terms['lesson']}입니다. 입사 후에도 {target_job} 담당자로서 활동명을 앞세우기보다, 제가 선택한 방법과 확인한 결과를 근거로 말하는 사람이 되고 싶습니다. 작은 업무라도 목적, 실행, 결과, 개선점을 남기며 팀이 믿고 이어갈 수 있는 방식으로 기여하겠습니다.",
        ]
    )
def build_related_questions(target_job, question):
    common = [
        question,
        f"{target_job} 직무를 선택한 이유와 준비 과정을 말씀해주세요.",
        "프로젝트에서 본인이 직접 맡은 역할과 결과를 구체적으로 설명해주세요.",
    ]
    if any(keyword in target_job for keyword in ["연구", "제품개발", "바이오"]):
        return common + ["실험 결과가 예상과 다를 때 어떤 방식으로 검증했나요?", "반복 업무에서 정확성을 유지하는 방법은 무엇인가요?"]
    if any(keyword in target_job for keyword in ["백엔드", "프론트", "데이터", "분석", "ICT"]):
        return common + ["기술 선택 과정에서 가장 고민했던 기준은 무엇인가요?", "장애나 오류가 발생했을 때 어떤 순서로 원인을 찾나요?"]
    if any(keyword in target_job for keyword in ["디자이너", "디자인"]):
        return common + ["사용자 피드백을 시안에 반영한 과정을 설명해주세요.", "포트폴리오에서 문제 정의가 가장 잘 드러나는 작업은 무엇인가요?"]
    if any(keyword in target_job for keyword in ["마케팅", "영업", "브랜드"]):
        return common + ["고객 반응이 예상과 달랐을 때 어떻게 개선했나요?", "성과를 판단할 때 어떤 지표를 가장 먼저 보나요?"]
    if any(keyword in target_job for keyword in ["생산", "품질", "제조"]):
        return common + ["불량이나 지연이 반복될 때 어떤 방식으로 원인을 찾나요?", "현장 의견과 데이터가 다를 때 어떻게 판단하겠습니까?"]
    if any(keyword in target_job for keyword in ["행정", "복지", "공공", "교육"]):
        return common + ["규정과 민원 요구가 충돌할 때 어떻게 설명하겠습니까?", "상대방의 감정이 격해진 상황을 어떻게 대처했나요?"]
    return common + ["협업 중 의견 차이가 있었을 때 어떤 기준으로 조율했나요?", "입사 후 3개월 동안 가장 먼저 보여주고 싶은 역량은 무엇인가요?"]


SAMPLE_HISTORIES = [
    ("Management", "사업기획", "경영학과", "SQLD, 컴퓨터활용능력 1급", "시장 진입 전략 수립 팀프로젝트", "B2B SaaS 경쟁사 분석, Notion 문서화", "최근 관심 있게 본 서비스와 개선 방향을 설명해주세요.", "경쟁사 기능을 비교하고 고객 불편을 기준으로 개선 우선순위를 정했던 경험을 말했습니다.", 78),
    ("Management", "인사/HR", "심리학과", "직업상담사 2급 필기, TOEIC 820", "채용 브랜딩 캠페인 기획", "동아리 운영진, 면접 일정 조율 경험", "여러 이해관계자와 일정을 조율한 경험을 말씀해주세요.", "동아리 면접 운영에서 지원자와 평가자 일정을 조율하고 공지 템플릿을 만든 경험을 답했습니다.", 82),
    ("SalesMarketing", "콘텐츠 마케팅", "미디어커뮤니케이션학과", "GA4 기초 수료, 검색광고마케터 준비", "SNS 콘텐츠 A/B 테스트", "블로그 30건 운영, 카드뉴스 제작", "고객 반응이 낮았던 콘텐츠를 어떻게 개선했나요?", "조회수보다 저장률을 기준으로 후킹 문구와 썸네일을 바꾼 경험을 답했습니다.", 80),
    ("SalesMarketing", "영업관리", "경영정보학과", "유통관리사 2급, TOEIC Speaking IM3", "CRM 고객 등급 분석", "편의점 아르바이트 클레임 응대", "고객 불만을 해결한 경험이 있다면 설명해주세요.", "불만 고객의 요구를 먼저 분류하고 가능한 보상 범위를 확인해 해결한 경험을 말했습니다.", 76),
    ("PublicService", "공공행정", "행정학과", "한국사능력검정 1급, 컴퓨터활용능력 1급", "지역 민원 데이터 분류 프로젝트", "공공기관 서포터즈, 봉사 80시간", "공공 서비스에서 가장 중요하다고 생각하는 가치는 무엇인가요?", "민원 처리 속도보다 설명 가능성과 공정성이 중요하다고 답했습니다.", 84),
    ("PublicService", "사회복지 행정", "사회복지학과", "사회복지사 2급, 운전면허 1종", "복지관 프로그램 만족도 조사", "노인복지관 봉사, 사례관리 보조", "상대방의 감정이 격해진 상황을 어떻게 대처했나요?", "감정을 먼저 인정하고 사실 확인과 지원 가능 범위를 분리해 설명한 경험을 말했습니다.", 79),
    ("RND", "연구개발", "화학공학과", "위험물산업기사 필기, OPIC IM2", "흡착 소재 실험 데이터 정리", "Python으로 실험 결과 시각화", "실험이나 연구에서 실패한 경험과 보완 과정을 말해주세요.", "반복 실험의 조건 기록이 부족했던 문제를 템플릿으로 개선한 경험을 답했습니다.", 81),
    ("RND", "제품개발", "기계공학과", "일반기계기사 필기, CAD 실습", "3D 프린팅 시제품 제작", "캡스톤 설계, 공차 분석", "새로운 환경에서 몰랐던 일을 맡았던 경험이 있나요?", "처음 쓰는 CAD 기능을 문서와 실습으로 익혀 시제품 수정 시간을 줄인 경험을 말했습니다.", 77),
    ("ICT", "백엔드 개발자", "컴퓨터공학과", "정보처리기사 필기, SQLD", "FastAPI RAG 검색 서비스", "Python, MySQL, Docker, GitHub Actions", "과거 프로젝트에서 어떤 역할을 수행했습니까?", "검색 API와 DB 스키마를 맡아 응답 속도와 검색 품질을 개선한 경험을 답했습니다.", 86),
    ("ICT", "데이터 분석가", "통계학과", "ADsP, SQLD", "이탈 고객 예측 모델", "Python, pandas, Tableau 대시보드", "데이터를 활용해 문제를 해결한 경험을 말씀해주세요.", "불균형 데이터를 재샘플링하고 지표를 F1로 바꿔 모델을 개선한 경험을 답했습니다.", 88),
    ("Design", "UX/UI 디자이너", "시각디자인학과", "GTQ 1급, Figma 활용", "모바일 앱 리디자인 포트폴리오", "사용자 인터뷰 6명, 와이어프레임 제작", "최근 인상 깊게 본 디자인 사례를 설명해주세요.", "온보딩 화면의 정보량과 CTA 위치가 전환에 미치는 영향을 중심으로 답했습니다.", 83),
    ("Design", "브랜드 디자이너", "산업디자인학과", "컴퓨터그래픽스운용기능사", "로컬 브랜드 아이덴티티 프로젝트", "로고, 패키지, SNS 템플릿 제작", "포트폴리오에서 가장 자신 있는 작업과 이유를 말해주세요.", "문제 정의, 무드보드, 적용 매체 확장까지 설명할 수 있는 프로젝트를 중심으로 답했습니다.", 80),
    ("ProductionManufacturing", "생산관리", "산업공학과", "품질경영기사 필기, 6시그마 GB", "공정 병목 분석 프로젝트", "엑셀 VBA, 현장 실습 4주", "일정이 촉박할 때 어떻게 우선순위를 정하나요?", "납기 영향도와 불량 가능성을 기준으로 작업 우선순위를 세운 경험을 답했습니다.", 82),
    ("ProductionManufacturing", "품질관리", "신소재공학과", "품질경영산업기사, 한국사 1급", "불량 원인 분석 실습", "QC 7 tools, 미니탭 기초", "문제가 반복될 때 어떤 방식으로 원인을 찾나요?", "현상, 발생 조건, 측정 기준을 분리해 체크시트를 만든 경험을 답했습니다.", 85),
    ("ICT", "프론트엔드 개발자", "소프트웨어학과", "정보처리기사 필기", "React 일정관리 앱", "TypeScript, 접근성 개선, Lighthouse 점검", "사용자 입장에서 서비스를 개선한 경험을 말해주세요.", "폼 오류 메시지와 키보드 이동 흐름을 고쳐 사용성을 높인 경험을 답했습니다.", 81),
    ("SalesMarketing", "브랜드 마케팅", "광고홍보학과", "검색광고마케터 1급", "신제품 런칭 캠페인 제안", "공모전 본선, 설문조사 120명", "타깃 고객을 어떻게 정의했나요?", "설문 결과와 구매 상황을 기준으로 페르소나를 나눈 경험을 답했습니다.", 79),
    ("Management", "재무/회계", "회계학과", "전산회계 1급, FAT 1급", "스타트업 비용 구조 분석", "Excel 피벗, 회계 동아리", "숫자를 다룰 때 실수를 줄이는 방법은 무엇인가요?", "입력-검산-근거 파일 연결 순서로 체크리스트를 만든 경험을 답했습니다.", 84),
    ("PublicService", "교육행정", "교육학과", "컴퓨터활용능력 1급, 한국사 1급", "비교과 프로그램 운영 보조", "학생 상담 접수, 만족도 설문", "규정과 민원 사이에서 어떻게 균형을 잡겠습니까?", "규정을 먼저 확인하고 예외 가능성과 설명 방식을 분리해야 한다고 답했습니다.", 78),
    ("RND", "바이오 연구보조", "생명공학과", "바이오화학제품제조기사 준비", "세포 배양 조건 비교 실험", "실험노트 관리, R 기초", "반복적인 업무에서 집중력을 어떻게 유지하나요?", "실험 단계별 체크포인트와 이상값 기록 습관을 중심으로 답했습니다.", 76),
    ("Design", "프로덕트 디자이너", "디지털미디어디자인학과", "UX 리서치 교육 수료", "구독 서비스 결제 흐름 개선", "Figma prototype, 사용성 테스트", "사용자 피드백을 디자인에 반영한 경험을 말해주세요.", "결제 이탈 원인을 인터뷰로 확인하고 가격 비교 화면을 바꾼 경험을 답했습니다.", 87),
]


CURATED_SOURCE_NOTE = "curated cover-letter library sample"
OLD_SAMPLE_SOURCE_NOTE = "public job-prep guidance inspired synthetic sample"


def curated_library_samples():
    groups = [
        (
            "ICT",
            "iOS 개발자",
            [
                ("컴퓨터공학과", "정보처리기사 필기", "운영체제 수업에서 스케줄링 알고리즘을 C로 구현하고 대기시간과 반환시간을 비교 분석", "Swift 기초, UIKit 화면 전환 실습", "지원 분야에 적합하다고 생각하는 이유와 직무 역량을 키운 사례를 작성해주세요.", "예상과 다른 실행 결과를 입력 조건과 우선순위 처리 기준으로 나누어 검증한 경험을 답했습니다.", 88),
                ("소프트웨어학과", "SQLD 준비", "Todo 앱에서 로컬 저장과 화면 상태 동기화 오류를 수정", "SwiftUI, Git, 앱 접근성 점검", "사용자 입장에서 서비스를 개선한 경험을 설명해주세요.", "상태 갱신 순서와 사용자 흐름을 함께 확인해 앱 오류를 줄인 경험을 답했습니다.", 86),
            ],
        ),
        (
            "ICT",
            "백엔드 개발자",
            [
                ("컴퓨터공학과", "정보처리기사 필기, SQLD", "FastAPI 기반 RAG 검색 API와 SQLite 히스토리 저장 구조 구현", "Python, Docker, REST API", "프로젝트에서 본인이 맡은 역할과 성과를 설명해주세요.", "검색 API와 DB 저장 구조를 맡아 응답 흐름과 재사용성을 개선한 경험을 답했습니다.", 89),
                ("정보통신공학과", "리눅스마스터 2급", "게시판 서비스에서 인증 미들웨어와 예외 처리 로직 구현", "Java, Spring Boot, MySQL", "장애나 오류가 발생했을 때 어떻게 원인을 찾았나요?", "로그, 요청값, DB 상태를 순서대로 확인해 인증 오류를 해결한 경험을 답했습니다.", 85),
            ],
        ),
        (
            "ICT",
            "데이터 분석가",
            [
                ("통계학과", "ADsP, SQLD", "이탈 고객 예측 모델을 만들고 불균형 데이터를 보정", "Python, pandas, Tableau", "데이터를 활용해 문제를 해결한 경험을 작성해주세요.", "정확도보다 F1과 재현율을 기준으로 모델을 비교한 경험을 답했습니다.", 87),
                ("산업공학과", "빅데이터분석기사 필기", "생산 불량 데이터를 공정 조건별로 분류하고 시각화", "scikit-learn, Excel PowerQuery", "분석 결과를 팀원이 이해하도록 전달한 경험을 설명해주세요.", "복잡한 변수보다 현장에서 확인 가능한 조건 중심으로 대시보드를 만든 경험을 답했습니다.", 84),
            ],
        ),
        (
            "SalesMarketing",
            "콘텐츠 마케팅",
            [
                ("미디어커뮤니케이션학과", "GA4 기초 수료", "SNS 콘텐츠 제목과 썸네일 A/B 테스트", "블로그 운영 30건, 카드뉴스 제작", "성과가 낮았던 콘텐츠를 어떻게 개선했나요?", "조회수보다 저장률과 클릭 후 이탈을 기준으로 문구를 수정한 경험을 답했습니다.", 82),
                ("광고홍보학과", "검색광고마케터 1급", "신제품 런칭 콘텐츠 캘린더와 채널별 메시지 설계", "설문조사 120명, 공모전 본선", "타깃 고객을 어떻게 정의했나요?", "구매 상황과 정보 탐색 경로를 기준으로 페르소나를 나눈 경험을 답했습니다.", 84),
            ],
        ),
        (
            "SalesMarketing",
            "영업관리",
            [
                ("경영정보학과", "유통관리사 2급", "CRM 고객 등급별 구매 패턴 분석", "편의점 아르바이트 클레임 응대", "고객 불만을 해결한 경험을 설명해주세요.", "요구를 먼저 분류하고 가능한 보상 범위를 확인해 해결한 경험을 답했습니다.", 79),
                ("경영학과", "컴퓨터활용능력 1급", "매장 재고 회전율을 기준으로 발주 우선순위 정리", "Excel 피벗, 고객 응대", "숫자와 현장 의견이 다를 때 어떻게 판단했나요?", "데이터를 먼저 확인하되 현장 상황을 함께 기록해 판단한 경험을 답했습니다.", 80),
            ],
        ),
        (
            "Management",
            "사업기획",
            [
                ("경영학과", "SQLD", "B2B SaaS 경쟁사 기능과 가격 정책 비교", "Notion 문서화, 시장 리서치", "최근 관심 있게 본 서비스와 개선 방향을 설명해주세요.", "고객 불편과 비용 구조를 기준으로 개선 우선순위를 정한 경험을 답했습니다.", 83),
                ("경제학과", "컴퓨터활용능력 1급", "구독 서비스 이탈 원인과 가격 민감도 조사", "설문 설계, Excel 분석", "기획안에서 가장 중요하게 본 기준은 무엇인가요?", "멋진 아이디어보다 실행 가능성과 검증 기준을 우선한 경험을 답했습니다.", 81),
            ],
        ),
        (
            "Management",
            "인사/HR",
            [
                ("심리학과", "직업상담사 2급 필기", "채용 브랜딩 캠페인과 지원자 안내 문구 개선", "동아리 운영진, 면접 일정 조율", "여러 이해관계자와 일정을 조율한 경험을 말씀해주세요.", "지원자와 평가자 일정을 나누어 공지 템플릿을 만든 경험을 답했습니다.", 82),
                ("교육학과", "컴퓨터활용능력 1급", "신입 부원 온보딩 문서와 역할 체크리스트 제작", "교육 봉사 운영, Google Sheets", "조직 적응을 돕기 위해 무엇을 해봤나요?", "처음 온 사람이 같은 질문을 반복하지 않도록 문서와 안내 흐름을 만든 경험을 답했습니다.", 80),
            ],
        ),
        (
            "PublicService",
            "공공행정",
            [
                ("행정학과", "한국사능력검정 1급", "지역 민원 데이터를 유형별로 분류하고 안내 문구 제안", "공공기관 서포터즈", "공공 서비스에서 가장 중요하다고 생각하는 가치는 무엇인가요?", "처리 속도보다 설명 가능성과 공정성이 중요하다고 답했습니다.", 84),
                ("법학과", "컴퓨터활용능력 1급", "규정 안내 자료를 사례 중심으로 재정리", "민원 응대 보조, 문서 편집", "규정과 민원 요구가 충돌할 때 어떻게 설명하겠습니까?", "가능한 범위와 불가능한 이유를 분리해 설명해야 한다고 답했습니다.", 81),
            ],
        ),
        (
            "PublicService",
            "사회복지 행정",
            [
                ("사회복지학과", "사회복지사 2급", "복지관 프로그램 만족도 조사와 개선안 정리", "노인복지관 봉사, 사례관리 보조", "상대방의 감정이 격해진 상황을 어떻게 대처했나요?", "감정을 인정한 뒤 사실 확인과 지원 가능 범위를 나누어 설명한 경험을 답했습니다.", 79),
                ("아동복지학과", "운전면허 1종", "아동 프로그램 출석과 피드백 기록 체계화", "아동 봉사, 보호자 안내", "도움이 필요한 사람을 대할 때 중요하게 보는 태도는 무엇인가요?", "선의보다 지속적으로 기록하고 확인하는 책임감을 중심으로 답했습니다.", 78),
            ],
        ),
        (
            "RND",
            "연구개발",
            [
                ("화학공학과", "위험물산업기사 필기", "흡착 소재 실험 조건과 결과를 반복 기록", "Python 실험 결과 시각화", "실험이나 연구에서 실패한 경험과 보완 과정을 말해주세요.", "조건 기록이 부족했던 문제를 실험노트 템플릿으로 개선한 경험을 답했습니다.", 83),
                ("신소재공학과", "품질경영기사 필기", "시편 열처리 조건별 강도 변화 비교", "Minitab 기초, SEM 분석 보조", "결과가 예상과 다를 때 어떤 방식으로 검증했나요?", "측정 조건과 샘플 준비 과정을 분리해 재확인한 경험을 답했습니다.", 82),
            ],
        ),
        (
            "RND",
            "제품개발",
            [
                ("기계공학과", "일반기계기사 필기", "3D 프린팅 시제품을 제작하고 공차 문제 수정", "CAD, 캡스톤 설계", "새로운 도구를 빠르게 익혀 적용한 경험이 있나요?", "문서와 실습을 병행해 설계 수정 시간을 줄인 경험을 답했습니다.", 80),
                ("전자공학과", "전기기사 필기", "센서 모듈을 활용한 온도 측정 프로토타입 제작", "Arduino, 회로 디버깅", "제품 문제를 발견하고 개선한 경험을 설명해주세요.", "측정 오차를 배선, 센서 위치, 코드 처리 순서로 나누어 확인한 경험을 답했습니다.", 81),
            ],
        ),
        (
            "Design",
            "UX/UI 디자이너",
            [
                ("시각디자인학과", "GTQ 1급", "모바일 앱 온보딩 화면 리디자인", "Figma, 사용자 인터뷰 6명", "사용자 피드백을 디자인에 반영한 경험을 말해주세요.", "사용자가 건너뛰는 지점을 찾아 정보량과 CTA 위치를 조정한 경험을 답했습니다.", 85),
                ("디지털미디어디자인학과", "UX 리서치 교육 수료", "구독 서비스 결제 흐름 개선 프로토타입", "사용성 테스트, 와이어프레임", "포트폴리오에서 문제 정의가 잘 드러나는 작업은 무엇인가요?", "결제 이탈 원인을 인터뷰로 확인하고 비교 화면을 바꾼 경험을 답했습니다.", 87),
            ],
        ),
        (
            "Design",
            "브랜드 디자이너",
            [
                ("산업디자인학과", "컴퓨터그래픽스운용기능사", "로컬 브랜드 아이덴티티와 패키지 시스템 제작", "로고, SNS 템플릿, 무드보드", "가장 자신 있는 디자인 작업과 이유를 설명해주세요.", "문제 정의부터 적용 매체 확장까지 일관성을 만든 작업을 중심으로 답했습니다.", 82),
                ("커뮤니케이션디자인학과", "ACP Photoshop", "행사 포스터와 온라인 배너 비주얼 시스템 설계", "인쇄물 제작, 피드백 반영", "피드백이 많을 때 어떤 기준으로 수정했나요?", "취향보다 전달 목적과 사용 매체를 기준으로 수정한 경험을 답했습니다.", 80),
            ],
        ),
        (
            "ProductionManufacturing",
            "생산관리",
            [
                ("산업공학과", "품질경영기사 필기", "공정 병목 구간을 작업 시간 데이터로 분석", "Excel VBA, 현장 실습 4주", "일정이 촉박할 때 어떻게 우선순위를 정하나요?", "납기 영향도와 불량 가능성을 기준으로 우선순위를 세운 경험을 답했습니다.", 82),
                ("기계공학과", "6시그마 GB", "조립 공정 작업 순서와 대기 시간을 비교", "공정 시뮬레이션, 체크시트", "현장 개선안을 제안한 경험을 설명해주세요.", "작업자 동선과 대기 시간을 함께 보고 개선안을 만든 경험을 답했습니다.", 81),
            ],
        ),
        (
            "ProductionManufacturing",
            "품질관리",
            [
                ("신소재공학과", "품질경영산업기사", "불량 원인을 재료, 설비, 측정 조건별로 분류", "QC 7 tools, Minitab 기초", "문제가 반복될 때 어떤 방식으로 원인을 찾나요?", "현상과 발생 조건을 분리해 체크시트를 만든 경험을 답했습니다.", 85),
                ("화학공학과", "위험물산업기사 필기", "공정 샘플의 pH 편차 원인 점검", "실험실 안전관리, 데이터 기록", "품질 기준을 지키기 위해 어떤 습관이 필요하다고 보나요?", "측정값만 보지 않고 샘플링 조건과 기록 방식을 함께 확인한다고 답했습니다.", 83),
            ],
        ),
    ]
    samples = []
    for occupation, target_job, variants in groups:
        for major, certificates, team_projects, other_specs, question, answer_text, score in variants:
            samples.append((occupation, target_job, major, certificates, team_projects, other_specs, question, answer_text, score))
    return samples


def connect(db_path=DB_PATH):
    DB_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def create_schema(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            occupation_label TEXT NOT NULL,
            target_job TEXT NOT NULL,
            major TEXT NOT NULL,
            certificates TEXT NOT NULL,
            team_projects TEXT NOT NULL,
            other_specs TEXT NOT NULL,
            question TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            cover_letter TEXT NOT NULL DEFAULT '',
            related_questions_json TEXT NOT NULL DEFAULT '[]',
            score INTEGER NOT NULL,
            source_note TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    existing_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(interview_history)").fetchall()
    }
    if "cover_letter" not in existing_columns:
        connection.execute("ALTER TABLE interview_history ADD COLUMN cover_letter TEXT NOT NULL DEFAULT ''")
    if "related_questions_json" not in existing_columns:
        connection.execute("ALTER TABLE interview_history ADD COLUMN related_questions_json TEXT NOT NULL DEFAULT '[]'")
    connection.commit()


def history_count(connection):
    return connection.execute("SELECT COUNT(*) FROM interview_history").fetchone()[0]


def seed_samples(connection, force=False):
    create_schema(connection)
    if history_count(connection) and not force:
        return 0
    if force:
        connection.execute("DELETE FROM interview_history")
        connection.execute("DELETE FROM sqlite_sequence WHERE name = 'interview_history'")
    rows = []
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    for index, sample in enumerate(curated_library_samples()):
        occupation, target_job, major, certificates, team_projects, other_specs, question, answer_text, score = sample
        cover_letter = build_cover_letter(occupation, target_job, major, certificates, team_projects, other_specs)
        related_questions = build_related_questions(target_job, question)
        created_at = (base_time + timedelta(days=index, hours=index % 4)).isoformat(timespec="seconds").replace("+00:00", "Z")
        payload = {
            "target_job": target_job,
            "structured_profile": {
                "major": major,
                "certificates": certificates,
                "team_projects": team_projects,
                "other_specs": other_specs,
            },
            "cover_letter": cover_letter,
            "related_questions": related_questions,
            "question": question,
            "answer_text": answer_text,
        }
        rows.append(
            (
                created_at,
                occupation,
                target_job,
                major,
                certificates,
                team_projects,
                other_specs,
                question,
                answer_text,
                cover_letter,
                json.dumps(related_questions, ensure_ascii=False),
                score,
                CURATED_SOURCE_NOTE,
                json.dumps(payload, ensure_ascii=False),
            )
        )
    connection.executemany(
        """
        INSERT INTO interview_history (
            created_at, occupation_label, target_job, major, certificates,
            team_projects, other_specs, question, answer_text,
            cover_letter, related_questions_json, score,
            source_note, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()
    return len(rows)


def refresh_curated_samples(connection=None):
    close_after = False
    if connection is None:
        connection = connect()
        close_after = True
    create_schema(connection)
    connection.execute(
        "DELETE FROM interview_history WHERE source_note IN (?, ?)",
        (OLD_SAMPLE_SOURCE_NOTE, CURATED_SOURCE_NOTE),
    )
    inserted = seed_samples(connection, force=False) if history_count(connection) == 0 else insert_curated_samples(connection)
    if close_after:
        connection.close()
    return inserted


def consolidate_split_llm_history(connection=None):
    close_after = False
    if connection is None:
        connection = connect()
        close_after = True
    create_schema(connection)
    rows = [
        row_to_item(row)
        for row in connection.execute(
            "SELECT * FROM interview_history WHERE source_note = ? ORDER BY created_at, id",
            ("openai generated draft for local RAG learning",),
        ).fetchall()
    ]
    groups = {}
    for row in rows:
        key = (row.get("created_at", ""), row.get("target_job", ""), row.get("major", ""), row.get("team_projects", ""))
        groups.setdefault(key, []).append(row)

    merged_count = 0
    for grouped_rows in groups.values():
        if not grouped_rows:
            continue
        first = grouped_rows[0]
        cover_letter = "\n\n".join(
            [
                f"[{index}. {row.get('question', '자소서 문항')}]\n{row.get('cover_letter', '').strip()}"
                for index, row in enumerate(grouped_rows, start=1)
                if row.get("cover_letter", "").strip()
            ]
        )
        related_questions = []
        for row in grouped_rows:
            for question in [row.get("question", "")] + list(row.get("related_questions") or []):
                if question and question not in related_questions:
                    related_questions.append(question)
        payload = {
            "target_job": first.get("target_job", ""),
            "structured_profile": {
                "major": first.get("major", ""),
                "certificates": first.get("certificates", ""),
                "team_projects": first.get("team_projects", ""),
                "other_specs": first.get("other_specs", ""),
            },
            "cover_letter": cover_letter,
            "related_questions": related_questions,
            "question": " / ".join([row.get("question", "") for row in grouped_rows if row.get("question")][:3]),
            "split_source_ids": [row.get("id") for row in grouped_rows],
        }
        connection.execute(
            """
            INSERT INTO interview_history (
                created_at, occupation_label, target_job, major, certificates,
                team_projects, other_specs, question, answer_text,
                cover_letter, related_questions_json, score,
                source_note, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first.get("created_at", ""),
                "LLM generated cover letter",
                first.get("target_job", ""),
                first.get("major", ""),
                first.get("certificates", ""),
                first.get("team_projects", ""),
                first.get("other_specs", ""),
                payload["question"] or "문항별 자기소개서 생성 결과",
                "생성된 자기소개서 전체 결과를 기준으로 면접에서 문항별 근거와 직접 수행한 행동을 설명합니다.",
                cover_letter,
                json.dumps(related_questions, ensure_ascii=False),
                int(first.get("score") or 0),
                "openai generated full result for local RAG learning",
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        merged_count += 1

    if rows:
        connection.execute(
            "DELETE FROM interview_history WHERE source_note = ?",
            ("openai generated draft for local RAG learning",),
        )
    connection.commit()
    if close_after:
        connection.close()
    return merged_count


def insert_curated_samples(connection):
    rows = []
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    for index, sample in enumerate(curated_library_samples()):
        occupation, target_job, major, certificates, team_projects, other_specs, question, answer_text, score = sample
        cover_letter = build_cover_letter(occupation, target_job, major, certificates, team_projects, other_specs)
        related_questions = build_related_questions(target_job, question)
        created_at = (base_time + timedelta(days=index, hours=index % 4)).isoformat(timespec="seconds").replace("+00:00", "Z")
        payload = {
            "target_job": target_job,
            "structured_profile": {
                "major": major,
                "certificates": certificates,
                "team_projects": team_projects,
                "other_specs": other_specs,
            },
            "cover_letter": cover_letter,
            "related_questions": related_questions,
            "question": question,
            "answer_text": answer_text,
        }
        rows.append(
            (
                created_at,
                occupation,
                target_job,
                major,
                certificates,
                team_projects,
                other_specs,
                question,
                answer_text,
                cover_letter,
                json.dumps(related_questions, ensure_ascii=False),
                score,
                CURATED_SOURCE_NOTE,
                json.dumps(payload, ensure_ascii=False),
            )
        )
    connection.executemany(
        """
        INSERT INTO interview_history (
            created_at, occupation_label, target_job, major, certificates,
            team_projects, other_specs, question, answer_text,
            cover_letter, related_questions_json, score,
            source_note, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()
    return len(rows)


def ensure_db():
    connection = connect()
    create_schema(connection)
    return connection


def list_history(limit=50, occupation_label=""):
    connection = ensure_db()
    query = "SELECT * FROM interview_history"
    params = []
    if occupation_label:
        query += " WHERE occupation_label = ?"
        params.append(occupation_label)
    query += " ORDER BY id ASC LIMIT ?"
    params.append(limit)
    rows = []
    for row in connection.execute(query, params):
        rows.append(row_to_item(row))
    connection.close()
    return rows


def purge_mock_history(connection=None):
    close_after = False
    if connection is None:
        connection = connect()
        close_after = True
    create_schema(connection)
    cursor = connection.execute(
        "DELETE FROM interview_history WHERE source_note IN (?, ?)",
        (CURATED_SOURCE_NOTE, OLD_SAMPLE_SOURCE_NOTE),
    )
    connection.commit()
    deleted = cursor.rowcount
    if close_after:
        connection.close()
    return deleted


def reset_history(connection=None):
    close_after = False
    if connection is None:
        connection = connect()
        close_after = True
    create_schema(connection)
    connection.execute("DELETE FROM interview_history")
    connection.execute("DELETE FROM sqlite_sequence WHERE name = 'interview_history'")
    connection.commit()
    if close_after:
        connection.close()


def row_to_item(row):
    item = dict(row)
    try:
        item["related_questions"] = json.loads(item.get("related_questions_json") or "[]")
    except json.JSONDecodeError:
        item["related_questions"] = []
    try:
        item["payload"] = json.loads(item.get("payload_json") or "{}")
    except json.JSONDecodeError:
        item["payload"] = {}
    return apply_history_display_style(item)


def history_profile(item):
    payload = item.get("payload") or {}
    profile = payload.get("structured_profile") or {}
    return {
        "major": item.get("major") or profile.get("major", ""),
        "certificates": item.get("certificates") or profile.get("certificates", ""),
        "team_projects": item.get("team_projects") or profile.get("team_projects", ""),
        "other_specs": item.get("other_specs") or profile.get("other_specs", ""),
        "age": profile.get("age", ""),
        "gender": profile.get("gender", ""),
    }


def history_questions_for_display(item, limit=5):
    payload = item.get("payload") or {}
    full_result = payload.get("full_generation_result") or {}
    questions = []
    for draft in full_result.get("drafts") or []:
        question = draft.get("question", "")
        if question and question not in questions:
            questions.append(question)
    for question in item.get("related_questions") or []:
        if question and question not in questions:
            questions.append(question)
    for question in str(item.get("question", "")).split(" / "):
        question = question.strip()
        if question and question not in questions:
            questions.append(question)
    if not questions:
        questions.append(f"{item.get('target_job', '') or '지원 직무'}와 연결되는 경험과 배운 점을 작성해주세요.")
    return [(question, 1, ["history"]) for question in questions[:limit]]


def apply_history_display_style(item):
    profile = history_profile(item)
    if not any(profile.get(key) for key in ["major", "certificates", "team_projects", "other_specs"]):
        return item
    try:
        from RAG.draft_generator import build_cover_letter_drafts
    except Exception:
        item["cover_letter"] = build_cover_letter(
            item.get("occupation_label", ""),
            item.get("target_job", ""),
            profile.get("major", ""),
            profile.get("certificates", ""),
            profile.get("team_projects", ""),
            profile.get("other_specs", ""),
        )
        return item

    target_company = (item.get("payload") or {}).get("target_company", "")
    target_job = item.get("target_job", "")
    drafts = build_cover_letter_drafts(
        history_questions_for_display(item),
        profile,
        target_company,
        target_job,
        {},
    )
    item["cover_letter"] = "\n\n".join(
        [
            f"[{index}. {draft.get('question', '자소서 문항')}]\n{draft.get('draft', '').strip()}"
            for index, draft in enumerate(drafts, start=1)
            if draft.get("draft", "").strip()
        ]
    )
    payload = item.setdefault("payload", {})
    full_result = payload.setdefault("full_generation_result", {})
    full_result["drafts"] = drafts
    full_result["questions"] = [
        {
            "question": draft.get("question", ""),
            "count": draft.get("source_count", 1),
            "example_companies": draft.get("example_companies", []),
        }
        for draft in drafts
    ]
    full_result["generation_provider"] = "history_display"
    payload["generation_provider"] = payload.get("generation_provider") or "history_display"
    return item


def get_history(row_id):
    connection = ensure_db()
    row = connection.execute("SELECT * FROM interview_history WHERE id = ?", (int(row_id),)).fetchone()
    connection.close()
    return row_to_item(row) if row else None


def add_history(payload):
    connection = ensure_db()
    profile = payload.get("structured_profile") or {}
    connection.execute(
        """
        INSERT INTO interview_history (
            created_at, occupation_label, target_job, major, certificates,
            team_projects, other_specs, question, answer_text,
            cover_letter, related_questions_json, score,
            source_note, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            payload.get("occupation_label", "Custom"),
            payload.get("target_job", ""),
            profile.get("major", ""),
            profile.get("certificates", ""),
            profile.get("team_projects", ""),
            profile.get("other_specs", ""),
            payload.get("question", ""),
            payload.get("answer_text", ""),
            payload.get("cover_letter", ""),
            json.dumps(payload.get("related_questions", []), ensure_ascii=False),
            int(payload.get("score") or 0),
            payload.get("source_note", "user practice history"),
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    connection.commit()
    row_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    connection.close()
    return row_id


if __name__ == "__main__":
    conn = connect()
    deleted = purge_mock_history(conn)
    merged = consolidate_split_llm_history(conn)
    conn.close()
    print(f"deleted_mock={deleted} merged={merged} db={DB_PATH}")
