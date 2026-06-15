import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from DB import history_store


API_URL = "http://127.0.0.1:8000/api/prepare"


def persona(large, job, company, major, certificates, project, other):
    return {
        "large": large,
        "target_job": job,
        "target_company": company,
        "major": major,
        "certificates": certificates,
        "team_projects": project,
        "other_specs": other,
    }


PERSONAS = [
    persona("연구개발", "디스플레이 연구개발", "디스플레이 제조사", "신소재공학과", "품질경영기사 필기", "박막 시편의 열처리 조건별 특성 변화를 비교하고 측정값 편차 원인을 실험노트로 정리했습니다.", "Minitab 기초, SEM 분석 보조, 실험 데이터 기록"),
    persona("연구개발", "바이오 연구보조", "바이오 헬스케어 기업", "생명공학과", "바이오화학제품제조기사 준비", "세포 배양 조건별 생존율을 기록하고 오염 의심 케이스를 배지, 시간, 보관 조건으로 나누어 확인했습니다.", "R 기초, 실험실 안전교육, 반복 실험 관리"),
    persona("경영·사무", "사업기획", "모빌리티 플랫폼 기업", "경영학과", "컴퓨터활용능력 1급", "구독 서비스 이탈 원인을 설문과 사용 흐름으로 나누어 분석하고 개선 우선순위를 제안했습니다.", "Excel 피벗, Notion 문서화, 시장 리서치"),
    persona("경영·사무", "재무회계", "제조 중견기업", "회계학과", "전산회계 1급, FAT 1급", "동아리 예산 집행 내역을 계정별로 분류하고 증빙 누락 항목을 체크리스트로 정리했습니다.", "Excel 함수, 비용 정산, 회계 동아리"),
    persona("기타", "해외사업 운영", "글로벌 소비재 기업", "국제통상학과", "TOEIC 780", "동남아 시장 진출 사례를 국가별 유통 채널과 소비자 가격 기준으로 비교 분석했습니다.", "무역영어 기초, 시장조사 보고서 작성, 팀 발표"),
    persona("기타", "프로젝트 관리", "자동차 부품사", "산업공학과", "6시그마 GB", "캡스톤 일정표를 만들고 설계, 구매, 제작 단계별 지연 요인을 구분해 팀 일정 관리를 맡았습니다.", "MS Project 기초, 회의록 작성, 일정 관리"),
    persona("영업·고객관리", "영업관리", "백화점 유통사", "경영정보학과", "유통관리사 2급", "매장 판매 데이터를 요일과 시간대별로 정리해 재고 보충 우선순위를 제안했습니다.", "고객 응대 아르바이트, Excel 피벗, 클레임 응대"),
    persona("영업·고객관리", "B2B 영업", "산업재 기업", "경영학과", "TOEIC Speaking IM3", "기업 고객 제안서 과제에서 고객 요구를 가격, 납기, 유지보수 기준으로 나누어 제안 구조를 만들었습니다.", "프레젠테이션, 견적 비교, 고객 니즈 정리"),
    persona("생산·품질", "생산관리", "자동차 제조사", "산업공학과", "품질경영기사 필기", "공정 병목 구간의 작업 시간을 측정하고 대기 시간이 긴 단계의 원인을 작업 순서별로 정리했습니다.", "현장 실습 4주, Excel VBA, 공정 분석"),
    persona("생산·품질", "품질관리", "화학 소재 기업", "화학공학과", "위험물산업기사 필기", "공정 샘플의 pH 편차를 측정 조건, 보관 시간, 시료 채취 위치로 나누어 점검했습니다.", "실험실 안전관리, QC 7 tools, 데이터 기록"),
    persona("IT·개발", "백엔드 개발자", "B2B SaaS 기업", "컴퓨터공학과", "SQLD 준비", "FastAPI 기반 RAG 검색 서비스에서 API 라우팅, SQLite 히스토리 저장, 검색 결과 직렬화 구조를 구현했습니다.", "Python, REST API, SQLite, Docker 기초"),
    persona("IT·개발", "데이터 분석가", "카드사 데이터 부서", "통계학과", "ADsP", "고객 행동 데이터를 pandas로 전처리하고 이탈 가능성을 기준으로 그룹을 나누어 시각화했습니다.", "Python, pandas, SQL, Tableau 기초"),
    persona("공공·행정", "일반행정", "공공기관", "행정학과", "한국사능력검정 1급, 컴퓨터활용능력 1급", "지역 민원 데이터를 유형별로 분류하고 반복 문의가 많은 항목의 안내 문구 개선안을 만들었습니다.", "공공기관 서포터즈, 문서 작성, 민원 응대 보조"),
    persona("공공·행정", "교육행정", "교육재단", "교육학과", "컴퓨터활용능력 1급", "비교과 프로그램 신청 데이터를 정리하고 학생 문의가 많은 절차를 FAQ로 만들었습니다.", "학생 상담 접수, 설문 정리, Google Sheets"),
    persona("마케팅·광고", "콘텐츠 마케팅", "화장품 브랜드", "미디어커뮤니케이션학과", "GA4 기초 수료", "SNS 콘텐츠 제목과 썸네일을 A/B 테스트하고 저장률을 기준으로 개선안을 정리했습니다.", "블로그 운영 30건, 카드뉴스 제작, 카피라이팅"),
    persona("마케팅·광고", "브랜드 마케팅", "엔터테인먼트 플랫폼", "광고홍보학과", "검색광고마케터 1급", "신규 캠페인 기획 과제에서 타깃 고객을 구매 상황과 콘텐츠 이용 맥락으로 나누어 정의했습니다.", "공모전 본선, 설문조사 120명, SNS 운영"),
    persona("금융", "금융일반", "시중은행", "경제학과", "투자자산운용사 준비", "가계부 데이터를 소비 항목별로 분류하고 월별 지출 패턴을 분석해 저축 계획을 세웠습니다.", "은행 인턴 준비, Excel, 금융상품 스터디"),
    persona("금융", "카드 상품기획", "카드사", "경영학과", "SQLD 준비", "20대 소비 데이터를 업종별로 나누어 혜택 선호도를 비교하고 카드 혜택 조합을 제안했습니다.", "SQL 기초, 데이터 리포트 작성, 핀테크 서비스 분석"),
    persona("건설·환경", "건축시공", "건설사", "건축공학과", "건설안전기사 필기", "학교 리모델링 사례를 공정 순서와 안전 점검 항목으로 나누어 발표했습니다.", "BIM 기초, 도면 해석, 현장 안전교육"),
    persona("건설·환경", "환경관리", "환경 설비 기업", "환경공학과", "수질환경기사 필기", "하천 수질 데이터를 항목별로 정리하고 측정값 이상치를 강우량과 채수 위치 기준으로 확인했습니다.", "수질 실험, Excel 시각화, 환경 법규 스터디"),
    persona("엔지니어링", "반도체 장비 엔지니어", "반도체 장비사", "전자공학과", "전기기사 필기", "센서 모듈 회로에서 측정 오차가 발생해 배선, 전원, 코드 처리 순서로 원인을 점검했습니다.", "회로 디버깅, Arduino, 계측기 사용"),
    persona("엔지니어링", "Customer Engineer", "글로벌 장비 기업", "기계공학과", "일반기계기사 필기", "3D 프린팅 시제품 제작 중 공차 문제를 발견하고 설계 치수와 출력 조건을 수정했습니다.", "CAD, 기구 설계, 장비 매뉴얼 독해"),
    persona("물류·구매", "물류관리", "이커머스 물류사", "물류학과", "물류관리사 준비", "주문 처리 시간을 입고, 피킹, 포장 단계로 나누어 지연 구간을 분석했습니다.", "WMS 기초, Excel, 창고 아르바이트"),
    persona("물류·구매", "구매관리", "제조 구매팀", "국제통상학과", "무역영어 1급 준비", "부품 공급업체 견적을 가격, 납기, 최소 주문 수량 기준으로 비교표로 만들었습니다.", "ERP 기초, 견적 비교, 공급망 리스크 조사"),
    persona("서비스", "객실승무원", "항공사", "관광경영학과", "TOEIC 820", "카페 아르바이트에서 대기 고객 불만을 응대하고 주문 동선을 조정해 혼잡을 줄였습니다.", "고객 응대, 서비스 매뉴얼 숙지, 영어 회화 연습"),
    persona("서비스", "호텔 프론트", "호텔 체인", "호텔경영학과", "호텔서비스사 준비", "체크인 문의를 유형별로 정리하고 자주 묻는 요청에 대한 안내 문구를 만들었습니다.", "예약 관리 실습, 고객 응대, 컴플레인 기록"),
    persona("미디어·콘텐츠", "예능 제작PD", "방송사", "방송영상학과", "영상편집 교육 수료", "팀 영상 프로젝트에서 섭외 일정, 촬영 콘티, 편집 피드백 반영을 맡았습니다.", "Premiere Pro, 촬영 보조, 콘텐츠 기획"),
    persona("미디어·콘텐츠", "콘텐츠 제작", "OTT 콘텐츠 기업", "문화콘텐츠학과", "GTQ 1급", "숏폼 콘텐츠 주제를 선정하고 조회 유지율이 낮은 구간을 기준으로 편집점을 수정했습니다.", "숏폼 제작, 썸네일 디자인, 채널 분석"),
    persona("의료·보건", "간호사", "종합병원", "간호학과", "BLS Provider", "시뮬레이션 실습에서 환자 상태 변화를 활력징후와 호소 증상으로 나누어 보고했습니다.", "임상실습, 환자 안전, 간호 기록"),
    persona("의료·보건", "보건행정", "건강검진센터", "보건행정학과", "병원행정사 준비", "검진 예약 데이터를 시간대별로 정리하고 접수 지연 원인을 문진표 작성 단계에서 찾았습니다.", "EMR 기초, 고객 안내, 개인정보보호 교육"),
    persona("디자인", "UX/UI 디자이너", "모바일 서비스 기업", "시각디자인학과", "GTQ 1급", "모바일 앱 온보딩 화면을 리디자인하고 사용자 인터뷰에서 발견한 이탈 지점을 화면 구조에 반영했습니다.", "Figma, 와이어프레임, 사용성 테스트"),
    persona("디자인", "브랜드 디자이너", "라이프스타일 브랜드", "산업디자인학과", "컴퓨터그래픽스운용기능사", "로컬 브랜드 아이덴티티 프로젝트에서 로고, 패키지, SNS 템플릿을 하나의 톤으로 정리했습니다.", "Illustrator, Photoshop, 무드보드 제작"),
    persona("교육", "교육운영", "직영학원", "교육학과", "컴퓨터활용능력 1급", "비대면 수업 출석과 과제 제출 현황을 정리해 미제출 학생 안내 프로세스를 만들었습니다.", "학원 조교, 학습 상담 보조, Google Sheets"),
    persona("교육", "일본어 통번역", "교육 콘텐츠 기업", "일어일문학과", "JLPT N2", "일본어 발표 자료를 번역하고 학습자가 이해하기 어려운 표현을 예문 중심으로 바꿨습니다.", "일본어 스터디 운영, 번역 검수, 교육 자료 제작"),
]


COMPANY_QUESTION_LIST = [
    "지원 분야에 본인이 적합하다고 생각하는 이유와, 해당 직무와 관련하여 역량을 키우기 위해 노력한 사례를 기술해주세요.",
    "지원한 직무와 관련하여 본인이 수행한 프로젝트 또는 경험을 구체적으로 작성해주세요.",
    "문제를 해결하기 위해 본인이 직접 한 행동과 사용한 기술 또는 방식을 설명해주세요.",
    "협업 과정에서 맡은 역할과 결과를 작성해주세요.",
    "입사 후 지원 직무에서 어떻게 기여하고 성장할 것인지 작성해주세요.",
]

COMPANY_QUESTIONS = "\n".join(COMPANY_QUESTION_LIST)


def collaboration_project_text(persona_item):
    project = persona_item["team_projects"].rstrip(".")
    job = persona_item["target_job"]
    return "; ".join(
        [
            f"팀 프로젝트에서 {project}",
            f"{job}와 연결되는 역할을 맡아 자료 조사, 실행안 정리, 결과물 검토 중 제가 담당할 범위를 먼저 나누었습니다",
            "팀원과 의견이 다른 부분은 일정, 완성도, 사용자 또는 현장 기준으로 비교해 조율했습니다",
        ]
    )


def post_prepare(persona_item):
    payload = {
        "large": persona_item["large"],
        "target_company": persona_item["target_company"],
        "target_job": persona_item["target_job"],
        "company_questions": COMPANY_QUESTIONS,
        "custom_questions": COMPANY_QUESTION_LIST,
        "structured_profile": {
            "major": persona_item["major"],
            "certificates": persona_item["certificates"],
            "team_projects": collaboration_project_text(persona_item),
            "other_specs": persona_item["other_specs"],
        },
        "top_k": 8,
        "generation": {
            "provider": "local_rag",
            "use_openai": False,
            "use_gemini": False,
        },
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    history_store.reset_history()
    saved = []
    for index, persona_item in enumerate(PERSONAS, start=1):
        output = post_prepare(persona_item)
        ids = output.get("local_learning", {}).get("saved_ids", [])
        saved.append(
            {
                "large": persona_item["large"],
                "persona": persona_item["target_job"],
                "ids": ids,
                "provider": output.get("generation_provider"),
            }
        )
        print(f"{index}. {persona_item['large']} / {persona_item['target_job']} saved={ids} provider={output.get('generation_provider')}")
    print(json.dumps(saved, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
