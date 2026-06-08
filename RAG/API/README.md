# RAG API JSON Input

이 디렉토리는 웹 화면 대신 JSON 파일로 RAG 입력을 테스트하기 위한 공간입니다.

## Files

- `input_template.json`: 사용자가 직접 수정하는 입력 템플릿입니다.
- `run_json.py`: JSON을 읽어서 현재 RAG 파이프라인을 실행합니다.
- `openai_generator.py`: `generation.use_openai`가 `true`일 때 OpenAI API로 초안을 다시 생성합니다.

## Run

```bash
python3 RAG/API/run_json.py --input RAG/API/input_template.json --summary
```

전체 결과를 파일로 저장하려면:

```bash
python3 RAG/API/run_json.py \
  --input RAG/API/input_template.json \
  --output RAG/API/output_example.json
```

## OpenAI API Key

API 키는 JSON 파일에 넣지 않습니다. 프로젝트 루트에 `.env` 파일을 만들고 아래처럼 저장합니다.

```bash
OPENAI_API_KEY=sk-...
```

`.env`는 `.gitignore`에 포함되어 있어서 Git에 올라가지 않습니다. 공유용 예시는 프로젝트 루트의 `.env.example`을 기준으로 보면 됩니다.

OpenAI API까지 연결하려면 `input_template.json`에서 아래 값만 바꾸면 됩니다.

```json
{
  "generation": {
    "use_openai": true,
    "model": "gpt-5.2",
    "output_style": "자기소개서 문체",
    "paragraphs": 3,
    "min_chars": 1000,
    "max_chars": 1500
  }
}
```

이때 실행 명령은 동일합니다.

```bash
python3 RAG/API/run_json.py --input RAG/API/input_template.json --summary
```

## Input Shape

- `target_job`: 갖고 싶은 직무/직업
- `target_company`: 지원 회사
- `structured_profile.major`: 학과/전공
- `structured_profile.certificates`: 자격증
- `structured_profile.team_projects`: 팀프로젝트 작업
- `structured_profile.other_specs`: 기타 스펙, 수업, 기술, 수상, 인턴
- `structured_profile.age`: 면접 데이터셋 비교용 선택 값
- `structured_profile.gender`: 면접 데이터셋 비교용 선택 값
- `generation.use_openai`: `true`이면 RAG 검색 결과와 로컬 초안을 OpenAI API에 보내 최종 자기소개서 문체로 다시 생성합니다. 기본값은 `false`입니다.
