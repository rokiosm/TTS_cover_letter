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

## Usage

```bash
python category/build_category_csvs.py
python category/visualize_categories.py
```
