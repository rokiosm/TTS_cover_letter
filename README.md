# TTS Cover Letter Dataset

링커리어 합격 자기소개서 데이터를 정리하고, 직무/스펙 카테고리 분류와 시각화까지 생성하는 작업 공간입니다. 최종 원본 데이터는 `linkareer_1to740.csv`이며, 중복 링크와 중복 cover-letter ID를 제거한 상태입니다.

## Root

- `linkareer_1to740.csv`는 최종 정제본 CSV입니다.
- 컬럼은 `기간, 회사, 직무, 유형, 스펙, 내용, 링크` 순서입니다.
- 현재 기준 데이터는 14,774행이며, 링크/ID/전체 행 중복을 제거했습니다.

## crawler/

- `crawler/crawling.py`는 링커리어 검색/상세 페이지를 수집하고 CSV로 저장하는 크롤러입니다.
- 기존 CSV의 링크를 다시 방문해 본문을 보정하거나, 검색 페이지 범위에서 새 링크를 수집할 수 있습니다.
- 요청 간 delay/jitter, append, workers 옵션을 지원합니다.

## category/

- `category/build_category_csvs.py`는 최종 CSV에서 직무/스펙 분류용 CSV를 생성합니다.
- `category/job_taxonomy.json`은 직무 대분류/중분류/소분류를 계층형 JSON으로 저장한 taxonomy입니다.
- `category/visualize_categories.py`는 카테고리별 요약 CSV와 SVG 차트를 생성합니다.

## categories/

- `categories/직무_카테고리.csv`는 각 행의 직무를 taxonomy 기준으로 1차 자동 분류한 파일입니다.
- `categories/스펙_카테고리.csv`는 스펙을 학교/학과/어학자격증/기타자격증/인턴/기타로 펼친 파일입니다.
- `categories/visualizations/`에는 열별 분포 요약 CSV, SVG 차트, 한 번에 볼 수 있는 `index.html`이 있습니다.

## Web/RAG Server

`main.py`는 로컬 웹 화면과 RAG API를 함께 제공하는 HTTP 서버입니다.

- `/`: 브라우저에서 사용하는 검색 화면입니다.
- `/health`: 서버 상태 확인용 엔드포인트입니다.
- `/api/categories`: 직무 대분류/중분류/소분류별 데이터 개수를 반환합니다.
- `/api/rag`: 검색 조건을 받아 자기소개서 질문 Top 5, 참고 context, 생성 프롬프트를 반환합니다.

현재 서버는 `linkareer_1to740.csv`, `categories/직무_카테고리.csv`, `Embedding/question_contexts.csv`를 읽어서 동작합니다. `Embedding/question_contexts.csv`가 있으면 질문 단위 데이터셋을 우선 사용하고, 없으면 원본 CSV와 직무 카테고리 CSV를 조합해서 문서 단위로 검색합니다.

공통 질문 Top 5와 생성 프롬프트는 지원자 정보가 입력된 경우에만 생성됩니다. 지원자 정보가 비어 있으면 화면과 API 모두 공통 질문을 만들지 않고 입력 안내만 반환합니다.

검색 결과의 `score`는 BM25 기반 관련도 점수입니다. 고정된 만점이 있는 점수가 아니라 같은 검색 결과 안에서 상대적으로 높을수록 더 유사하다는 뜻입니다.

### Local Run

프로젝트 루트에서 실행합니다.

```bash
python3 main.py --host 127.0.0.1 --port 8000
```

브라우저에서 아래 주소로 접속합니다.

```text
http://127.0.0.1:8000
```

다른 기기에서 같은 네트워크로 접속해야 한다면 서버를 `0.0.0.0`으로 열고, 접속하는 쪽에서는 서버 컴퓨터의 IP를 사용합니다.

```bash
python3 main.py --host 0.0.0.0 --port 8000
```

예를 들어 서버 컴퓨터 IP가 `192.168.0.25`라면 다른 기기 브라우저에서 `http://192.168.0.25:8000`으로 접속합니다. macOS 방화벽이나 회사/학교 네트워크 정책이 있으면 8000번 포트 접속이 막힐 수 있습니다.

서버 상태만 빠르게 확인할 때는 아래 명령을 사용합니다.

```bash
curl http://127.0.0.1:8000/health
```

정상 응답 예시는 다음과 같습니다.

```json
{"status": "ok"}
```

### API Example

```bash
curl -X POST http://127.0.0.1:8000/api/rag \
  -H 'Content-Type: application/json' \
  -d '{
    "large": "마케팅·광고",
    "medium": "브랜드 마케팅",
    "target_company": "아모레퍼시픽",
    "target_job": "브랜드 마케팅",
    "user_profile": "콘텐츠 캠페인 운영 경험과 데이터 분석 경험이 있습니다.",
    "top_k": 5
  }'
```

## Data Processing Usage

```bash
python category/build_category_csvs.py
python category/visualize_categories.py
```
