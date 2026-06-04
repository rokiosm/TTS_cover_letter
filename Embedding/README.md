# Embedding Experiments

이 디렉토리는 `linkareer_1to740.csv`를 바로 RAG에 넣기 전에, 자기소개서 `내용`을 질문 단위로 나누고 문맥 길이별 검색 품질을 비교하기 위한 실험 공간입니다.

## 1. 질문 단위 데이터셋 생성

```bash
.venv/bin/python -m Embedding.question_dataset
```

생성 파일:

- `Embedding/question_contexts.csv`
- `Embedding/question_answer_groups.json`

주요 컬럼:

- `question_text`: 추출된 질문
- `answer`: 해당 질문의 답변 본문
- `question_label`: 지원동기, 직무역량, 경험/성과 등 규칙 기반 라벨
- `context_300`, `context_600`, `context_1000`: 검색 실험용 문맥 길이

JSON은 질문 하나에 여러 답변을 묶기 위한 계층형 파일입니다.

```text
large > medium > normalized_question > answers[]
```

이 구조가 RAG에는 더 자연스럽습니다. 같은 질문이라도 직무 중분류가 다르면 답변 맥락이 달라지므로, `large`, `medium`, `question_key`를 함께 묶습니다. CSV는 실험과 테이블 로딩용으로 유지하고, 실제 질문-답변 관계를 볼 때는 JSON을 우선 사용합니다.

## 2. 문맥 길이 실험

```bash
.venv/bin/python -m Embedding.experiment_contexts --sample-size 500 --max-docs 5000
```

생성 파일:

- `Embedding/experiment_results.csv`

실험 방식:

- `token_unigram`: 단어 단위 벡터
- `token_bigram`: 단어와 인접 단어쌍을 함께 쓰는 벡터
- `char_3_5`: 3~5글자 character n-gram 벡터. 느리므로 `--include-char-ngrams`를 줄 때만 실행

점수는 query 벡터와 context 벡터의 cosine similarity입니다. 현재 구현은 외부 모델 없이 빠르게 비교하기 위한 hashed sparse vector 방식입니다. 실제 의미 임베딩 모델을 붙이면 같은 CSV를 입력으로 sentence-transformers, OpenAI embeddings, FAISS 실험으로 확장할 수 있습니다.

## 3. 임베딩 DB 생성

```bash
.venv/bin/python -m Embedding.vector_store
```

생성 파일:

- `Embedding/embedding_store.sqlite`

PostgreSQL에 저장:

```bash
docker compose up -d postgres
.venv/bin/python -m Embedding.vector_store --postgres
```

단어 단위까지 포함해서 저장:

```bash
.venv/bin/python -m Embedding.vector_store --units word,sentence,context --max-rows 1000
```

기본 접속 정보:

- DB: `cover_letter_rag`
- User: `rag`
- Password: `rag_password`
- URL: `postgresql://rag:rag_password@127.0.0.1:5432/cover_letter_rag`

저장 단위:

- `word`: 질문/답변에서 나온 단어별 벡터. row 수가 매우 많아지므로 샘플 실험 후 전체 저장 권장
- `sentence`: 답변을 문장으로 나눈 문장별 벡터
- `context`: 질문 + 답변 일부를 합친 context 벡터

현재 점수는 sparse vector cosine similarity로 계산합니다. 단어 일치 기반 BM25보다 문맥을 조금 더 보려면 `sentence` 또는 `context` 단위가 유리하고, 실제 semantic embedding은 이 SQLite 스키마의 `model`, `dimensions`, `vector_json`만 교체해서 붙이면 됩니다.

Docker Compose는 `pgvector/pgvector:pg16`을 사용합니다. 지금은 설명 가능한 sparse vector를 `jsonb`에 저장하고, 이후 OpenAI 또는 sentence-transformers 임베딩을 붙일 때 `vector` 컬럼을 추가하면 됩니다.
