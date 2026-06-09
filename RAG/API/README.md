# RAG API JSON Input

이 디렉토리는 웹 화면 대신 JSON 파일로 RAG 입력을 테스트하기 위한 공간입니다.

## Files

- `input_template.json`: 사용자가 직접 수정하는 입력 템플릿입니다.
- `run_json.py`: JSON을 읽어서 현재 RAG 파이프라인을 실행합니다.
- `openai_generator.py`: `generation.use_openai`가 `true`일 때 OpenAI API로 초안을 다시 생성합니다.
- `vllm_generator.py`: `generation.provider`가 `vllm`이거나 `generation.use_vllm`이 `true`일 때 vLLM OpenAI-compatible API로 초안을 다시 생성합니다.

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

## LLM Provider

RAG 검색은 로컬 데이터로 수행하고, 최종 문장 생성은 Gemini, OpenAI, vLLM 중 하나를 선택할 수 있습니다.

### Gemini

Gemini API key는 JSON 파일에 넣지 않고 `.env`에 저장합니다.

```bash
GEMINI_API_KEY=AIza...
```

`input_template.json` 예시는 아래처럼 둡니다.

```json
{
  "generation": {
    "provider": "gemini",
    "use_gemini": true,
    "model": "gemini-2.5-flash",
    "output_style": "자기소개서 문체",
    "paragraphs": 3,
    "min_chars": 1000,
    "max_chars": 1500,
    "temperature": 0.2,
    "max_tokens": 4096
  }
}
```

temperature/max_tokens 조합 실험은 아래 명령으로 실행합니다.

```bash
python3 RAG/API/generation_experiment.py \
  --input RAG/API/input_template.json \
  --output RAG/API/generation_experiment_output.json \
  --temperatures 0.1,0.2,0.5 \
  --max-tokens 2048,4096
```

### vLLM

vLLM 서버가 OpenAI-compatible API로 떠 있으면 `ChatOpenAI`를 그대로 사용할 수 있습니다. vLLM은 API key를 실제로 쓰지 않으므로 `EMPTY`를 넣어도 됩니다.

```bash
VLLM_API_BASE=http://127.0.0.1:8001/v1
VLLM_API_KEY=EMPTY
```

`input_template.json` 예시는 아래처럼 둡니다.

```json
{
  "generation": {
    "provider": "vllm",
    "use_vllm": true,
    "model": "Qwen/Qwen3-14B",
    "base_url": "http://127.0.0.1:8001/v1",
    "output_style": "자기소개서 문체",
    "paragraphs": 3,
    "min_chars": 1000,
    "max_chars": 1500,
    "temperature": 0.2,
    "max_tokens": 4096
  }
}
```

### OpenAI

API 키는 JSON 파일에 넣지 않습니다. 프로젝트 루트에 `.env` 파일을 만들고 아래처럼 저장합니다.

```bash
OPENAI_API_KEY=sk-...
```

`.env`는 `.gitignore`에 포함되어 있어서 Git에 올라가지 않습니다. 공유용 예시는 프로젝트 루트의 `.env.example`을 기준으로 보면 됩니다.

OpenAI API로 연결하려면 `input_template.json`에서 아래 값만 바꾸면 됩니다.

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
- `generation.provider`: `gemini`이면 Gemini, `vllm`이면 vLLM, 값이 없고 `use_openai`가 `true`이면 OpenAI를 사용합니다.
- `generation.use_gemini`: `true`이면 RAG 검색 결과와 로컬 초안을 Gemini API에 보내 최종 자기소개서 문체로 다시 생성합니다.
- `generation.use_vllm`: `true`이면 RAG 검색 결과와 로컬 초안을 vLLM API에 보내 최종 자기소개서 문체로 다시 생성합니다.
- `generation.use_openai`: `true`이면 RAG 검색 결과와 로컬 초안을 OpenAI API에 보내 최종 자기소개서 문체로 다시 생성합니다. 기본값은 `false`입니다.
