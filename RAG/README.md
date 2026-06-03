# Cover Letter RAG

`main.py`는 웹/서버 연동용 HTTP 엔트리포인트입니다. 브라우저 테스트 페이지(`/`)와 JSON API(`/api/categories`, `/api/rag`, `/health`)를 제공합니다.

## Local Run

```bash
python main.py --host 127.0.0.1 --port 8000
```

브라우저에서 `http://127.0.0.1:8000`을 열면 직무 선택, 회사/직무/키워드 입력, topK 검색 결과와 생성 프롬프트를 확인할 수 있습니다.

## Docker

```bash
docker compose up --build
```

Docker 이미지는 코드만 포함하고, 대용량 CSV와 `categories/`는 compose 볼륨으로 읽기 전용 마운트합니다.

## API

```bash
curl http://127.0.0.1:8000/api/categories
curl -X POST http://127.0.0.1:8000/api/rag \
  -H 'Content-Type: application/json' \
  -d '{"large":"마케팅·광고","target_company":"아모레퍼시픽","target_job":"브랜드 마케팅","query":"브랜드 캠페인 콘텐츠 성과","top_k":3}'
```
