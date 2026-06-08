import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "DB"
DB_PATH = DB_DIR / "interview_history.sqlite3"


def build_cover_letter(occupation, target_job, major, certificates, team_projects, other_specs):
    templates = {
        "Management": [
            f"저는 {target_job}에서 가장 중요한 힘이 복잡한 상황을 숫자와 흐름으로 정리하는 능력이라고 생각합니다. {major}에서 배운 경영 지식은 문제를 넓게 보는 기반이 되었고, {team_projects}를 하며 실제 의사결정에는 자료의 양보다 기준의 선명함이 더 중요하다는 점을 배웠습니다.",
            f"{certificates}와 {other_specs} 경험은 제 판단을 더 구체적으로 만드는 도구였습니다. 단순히 자료를 모으는 데서 그치지 않고, 어떤 지표를 먼저 봐야 하는지, 팀원이 이해할 수 있는 형태로 어떻게 정리해야 하는지를 계속 고민했습니다.",
            f"입사 후에는 {target_job} 담당자로서 실행 전에 목적과 제약을 분명히 확인하고, 실행 후에는 근거가 남는 방식으로 일하고 싶습니다. 작은 분석이라도 다음 의사결정에 도움이 되는 자료로 남기는 사람이 되겠습니다.",
        ],
        "SalesMarketing": [
            f"{target_job}는 사람의 반응을 읽고 그 반응을 다음 실행으로 바꾸는 일이라고 생각합니다. 저는 {major}에서 커뮤니케이션의 기본을 배우고, {team_projects}를 통해 메시지 하나가 고객의 행동을 어떻게 바꾸는지 관찰했습니다.",
            f"{other_specs} 경험을 하면서 조회수나 노출 같은 표면 지표보다 왜 반응했는지 설명할 수 있는 근거가 더 중요하다는 점을 배웠습니다. {certificates} 준비 역시 캠페인을 감으로만 판단하지 않고 데이터와 채널 구조로 이해하는 데 도움이 되었습니다.",
            f"앞으로 {target_job} 업무를 맡게 된다면 고객 반응을 빠르게 확인하고, 실패한 콘텐츠나 제안도 개선 기준이 남도록 정리하겠습니다. 결과가 좋을 때보다 반응이 낮을 때 더 많이 배우는 마케터가 되고 싶습니다.",
        ],
        "PublicService": [
            f"제가 {target_job}에 관심을 가진 이유는 행정과 서비스가 결국 사람의 불편을 줄이는 일이라고 느꼈기 때문입니다. {major}에서 배운 이론은 제도와 현장을 함께 보는 관점을 주었고, {team_projects}를 통해 작은 안내 방식 하나도 이용자 경험을 바꿀 수 있다는 점을 배웠습니다.",
            f"{certificates}와 {other_specs} 경험은 공공 업무에서 필요한 정확성과 책임감을 기르는 과정이었습니다. 특히 여러 사람의 요청을 다룰 때는 친절함만큼이나 기준을 일관되게 설명하는 태도가 중요하다고 생각합니다.",
            f"입사 후에는 {target_job} 업무에서 규정과 민원 사이의 균형을 지키는 사람이 되고 싶습니다. 빠른 처리보다 신뢰할 수 있는 설명, 그리고 다시 같은 문제가 반복되지 않도록 기록을 남기는 방식을 중요하게 여기겠습니다.",
        ],
        "RND": [
            f"{target_job} 분야에서 제가 가장 흥미를 느끼는 지점은 가설을 세우고 검증하는 과정입니다. {major}에서 배운 전공 지식은 실험과 설계를 이해하는 기반이 되었고, {team_projects}를 통해 결과가 예상과 다를 때 원인을 끝까지 추적하는 태도를 익혔습니다.",
            f"{other_specs} 경험은 연구 데이터를 더 명확하게 보고 기록하는 데 도움이 되었습니다. {certificates} 준비 과정에서도 절차를 암기하는 것보다 왜 그 조건이 필요한지 이해하려고 했고, 그 습관이 반복 실험과 분석에 연결되었습니다.",
            f"입사 후에는 {target_job}로서 정확한 기록과 꾸준한 검증을 강점으로 만들고 싶습니다. 눈에 띄는 성과 이전에 재현 가능한 과정과 팀이 믿을 수 있는 데이터를 남기는 구성원이 되겠습니다.",
        ],
        "ICT": [
            f"저는 {target_job}를 단순히 코드를 작성하는 역할보다 문제를 동작하는 구조로 바꾸는 일이라고 생각합니다. {major}에서 기본기를 쌓고, {team_projects}를 진행하면서 요구사항을 API, 데이터, 화면 흐름으로 나누어 생각하는 법을 배웠습니다.",
            f"{other_specs}를 활용하며 기능 구현보다 중요한 것은 왜 이 방식이 필요한지 설명할 수 있는 코드와 구조라는 점을 느꼈습니다. {certificates} 준비는 부족한 CS와 데이터베이스 지식을 다시 정리하는 계기가 되었습니다.",
            f"입사 후에는 {target_job}로서 빠르게 만드는 것에만 집중하지 않고, 장애가 났을 때 원인을 추적할 수 있는 구조와 팀원이 이어받기 쉬운 기록을 남기겠습니다. 작은 기능도 안정적으로 운영되는 경험으로 연결하고 싶습니다.",
        ],
        "Design": [
            f"{target_job}에서 제가 중요하게 보는 것은 보기 좋은 결과물보다 사용자가 왜 그렇게 행동하는지 이해하는 과정입니다. {major}에서 시각적 완성도를 배우고, {team_projects}를 통해 문제 정의와 시안 검증이 디자인의 설득력을 만든다는 점을 경험했습니다.",
            f"{other_specs} 경험은 제 디자인을 감각이 아니라 근거로 설명하는 연습이었습니다. {certificates} 역시 도구 사용 능력을 보완해 주었지만, 최종적으로는 사용자의 불편을 어떻게 발견하고 화면에 반영했는지가 더 중요하다고 생각합니다.",
            f"입사 후에는 {target_job}로서 팀이 논의할 수 있는 디자인을 만들고 싶습니다. 시안을 예쁘게 완성하는 데서 멈추지 않고, 왜 이 흐름이 필요한지와 어떤 피드백을 반영했는지를 함께 제시하겠습니다.",
        ],
        "ProductionManufacturing": [
            f"{target_job} 업무는 현장의 작은 변화가 품질과 납기에 직접 연결되는 일이라고 생각합니다. {major}에서 공정과 시스템을 배우고, {team_projects}를 통해 문제를 감으로 판단하지 않고 데이터와 조건으로 나누어 보는 습관을 익혔습니다.",
            f"{certificates}와 {other_specs} 경험은 품질과 생산 흐름을 더 체계적으로 이해하는 데 도움이 되었습니다. 특히 반복되는 문제를 볼 때는 한 번의 조치보다 원인이 다시 발생하지 않도록 기준을 만드는 일이 중요하다고 느꼈습니다.",
            f"입사 후에는 {target_job} 담당자로서 현장과 데이터를 함께 보는 사람이 되고 싶습니다. 작업자의 관찰과 수치 데이터를 연결해 개선점을 찾고, 작은 불량이나 지연도 다음 개선으로 이어지게 만들겠습니다.",
        ],
    }
    return "\n\n".join(templates.get(occupation, templates["Management"]))


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
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = []
    for sample in SAMPLE_HISTORIES:
        occupation, target_job, major, certificates, team_projects, other_specs, question, answer_text, score = sample
        cover_letter = build_cover_letter(occupation, target_job, major, certificates, team_projects, other_specs)
        related_questions = build_related_questions(target_job, question)
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
                now,
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
                "public job-prep guidance inspired synthetic sample",
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
    if history_count(connection) == 0:
        seed_samples(connection)
    return connection


def list_history(limit=50, occupation_label=""):
    connection = ensure_db()
    query = "SELECT * FROM interview_history"
    params = []
    if occupation_label:
        query += " WHERE occupation_label = ?"
        params.append(occupation_label)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = []
    for row in connection.execute(query, params):
        item = dict(row)
        try:
            item["related_questions"] = json.loads(item.get("related_questions_json") or "[]")
        except json.JSONDecodeError:
            item["related_questions"] = []
        rows.append(item)
    connection.close()
    return rows


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
            "user practice history",
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    connection.commit()
    row_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    connection.close()
    return row_id


if __name__ == "__main__":
    conn = connect()
    inserted = seed_samples(conn, force=True)
    conn.close()
    print(f"seeded={inserted} db={DB_PATH}")
