# Docker Usage

Docker로 실행하면 Python 설치 상태와 상관없이 같은 방식으로 서버를 열 수 있습니다. 다른 컴퓨터에서 사용할 때는 Docker Desktop 또는 Docker Engine과 Docker Compose가 먼저 설치되어 있어야 합니다.

## 1. 프로젝트 파일 준비

다른 컴퓨터에서 이 저장소를 받은 뒤 프로젝트 루트로 이동합니다.

```bash
git clone <repository-url>
cd TTS_cover_letter
```

이 서버는 코드만 있으면 되는 앱이 아니라 데이터 파일을 함께 읽습니다. 아래 파일/폴더가 같은 위치에 있어야 합니다.

```text
linkareer_1to740.csv
categories/
Embedding/
RAG/
frontend/
main.py
Dockerfile
docker-compose.yml
```

특히 `docker-compose.yml`은 아래 데이터를 컨테이너 안으로 마운트합니다.

- `./linkareer_1to740.csv` -> `/app/linkareer_1to740.csv`
- `./categories` -> `/app/categories`
- `./Embedding` -> `/app/Embedding`

따라서 다른 컴퓨터로 옮길 때 CSV와 `categories/`, `Embedding/` 폴더가 빠지면 카테고리 로딩 또는 RAG 검색이 실패할 수 있습니다.

## 2. Docker Compose로 서버 실행

프로젝트 루트에서 실행합니다.

```bash
docker compose up --build
```

처음 실행할 때는 `pgvector/pgvector:pg16` 이미지와 Python 서버 이미지를 내려받고 빌드하므로 시간이 걸릴 수 있습니다. 빌드가 끝나면 로컬 브라우저에서 접속합니다.

```text
http://127.0.0.1:8000
```

백그라운드로 실행하려면 `-d` 옵션을 붙입니다.

```bash
docker compose up --build -d
```

로그 확인:

```bash
docker compose logs -f rag-server
```

서버 중지:

```bash
docker compose down
```

PostgreSQL 데이터 볼륨까지 완전히 지우려면 아래 명령을 사용합니다. 임베딩 DB를 다시 만들 수 있을 때만 실행하세요.

```bash
docker compose down -v
```

## 3. Docker 구성 설명

`docker-compose.yml`은 두 서비스를 실행합니다.

- `postgres`: `pgvector/pgvector:pg16` 기반 PostgreSQL입니다. `Embedding/vector_store.py --postgres` 같은 임베딩 DB 실험에 사용할 수 있습니다.
- `rag-server`: `main.py`를 실행하는 웹/RAG 서버입니다. 외부에서는 `8000:8000` 포트 매핑으로 접속합니다.

현재 웹/RAG 서버는 기본적으로 CSV와 `Embedding/question_contexts.csv`를 읽는 파일 기반 검색으로 동작합니다. `DATABASE_URL` 환경변수와 PostgreSQL 서비스는 임베딩 저장/확장 실험을 위해 함께 둔 구성입니다.

## 4. Docker 실행 문제 해결

포트가 이미 사용 중이면 `docker-compose.yml`의 포트 매핑을 바꿉니다.

```yaml
ports:
  - "8001:8000"
```

이 경우 브라우저에서는 `http://127.0.0.1:8001`로 접속합니다.

데이터 파일을 찾지 못하는 오류가 나면 프로젝트 루트에서 실행했는지, `linkareer_1to740.csv`, `categories/`, `Embedding/`이 실제로 있는지 확인합니다.

Docker 빌드 캐시가 꼬였거나 파일 변경이 반영되지 않으면 다시 빌드합니다.

```bash
docker compose build --no-cache
docker compose up
```
