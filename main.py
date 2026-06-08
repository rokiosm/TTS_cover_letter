import argparse
import json
import mimetypes
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HOST = "0.0.0.0"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
DOCUMENTS = None
RAG_MODULE = None
INTERVIEW_MODULE = None
PROCESS_STARTED_AT = time.perf_counter()


def log_event(message):
    elapsed = time.perf_counter() - PROCESS_STARTED_AT
    print(f"[{elapsed:8.3f}s] {message}", flush=True)


def get_rag_module():
    global RAG_MODULE
    if RAG_MODULE is None:
        started_at = time.perf_counter()
        log_event("importing RAG.cover_letter_rag")
        from RAG import cover_letter_rag

        RAG_MODULE = cover_letter_rag
        log_event(f"imported RAG.cover_letter_rag in {time.perf_counter() - started_at:.3f}s")
    return RAG_MODULE


def get_interview_module():
    global INTERVIEW_MODULE
    if INTERVIEW_MODULE is None:
        started_at = time.perf_counter()
        log_event("importing RAG.interview_rag")
        from RAG import interview_rag

        INTERVIEW_MODULE = interview_rag
        log_event(f"imported RAG.interview_rag in {time.perf_counter() - started_at:.3f}s")
    return INTERVIEW_MODULE


def get_documents():
    global DOCUMENTS
    if DOCUMENTS is None:
        started_at = time.perf_counter()
        log_event("loading documents")
        DOCUMENTS = get_rag_module().load_documents()
        log_event(f"loaded {len(DOCUMENTS):,} documents in {time.perf_counter() - started_at:.3f}s")
    return DOCUMENTS


def read_frontend_file(filename):
    return (FRONTEND_DIR / filename).read_bytes()


def resolve_frontend_file(path):
    if path == "/":
        requested = FRONTEND_DIR / "index.html"
    else:
        requested = FRONTEND_DIR / path.lstrip("/")
    resolved = requested.resolve()
    if FRONTEND_DIR.resolve() not in resolved.parents and resolved != FRONTEND_DIR.resolve():
        return None
    if not resolved.is_file():
        return None
    return resolved


def content_type_for(path):
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed:
        return f"{guessed}; charset=utf-8" if guessed.startswith("text/") else guessed
    return "application/octet-stream"


def send_response(handler, status, content_type, body):
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    send_response(handler, status, "application/json; charset=utf-8", body)


class RagHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        started_at = time.perf_counter()
        path = urlparse(self.path).path
        log_event(f"GET {path}")
        frontend_file = resolve_frontend_file(path)
        if frontend_file:
            body = frontend_file.read_bytes()
            send_response(self, 200, content_type_for(frontend_file), body)
            log_event(f"GET {path} completed in {time.perf_counter() - started_at:.3f}s")
            return
        if path == "/health":
            json_response(self, 200, {"status": "ok"})
            log_event(f"GET {path} completed in {time.perf_counter() - started_at:.3f}s")
            return
        if path == "/api/categories":
            json_response(self, 200, get_rag_module().category_counts(get_documents()))
            log_event(f"GET {path} completed in {time.perf_counter() - started_at:.3f}s")
            return
        if path == "/api/interview/status":
            json_response(self, 200, get_interview_module().interview_dataset_meta())
            log_event(f"GET {path} completed in {time.perf_counter() - started_at:.3f}s")
            return
        if path == "/api/history":
            from DB import history_store

            json_response(self, 200, {"items": history_store.list_history()})
            log_event(f"GET {path} completed in {time.perf_counter() - started_at:.3f}s")
            return
        json_response(self, 404, {"error": "not_found"})
        log_event(f"GET {path} completed in {time.perf_counter() - started_at:.3f}s")

    def do_POST(self):
        started_at = time.perf_counter()
        path = urlparse(self.path).path
        log_event(f"POST {path}")
        if path not in {"/api/rag", "/api/prepare", "/api/interview/questions", "/api/interview/evaluate", "/api/history"}:
            json_response(self, 404, {"error": "not_found"})
            log_event(f"POST {path} completed in {time.perf_counter() - started_at:.3f}s")
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            json_response(self, 400, {"error": "invalid_json"})
            log_event(f"POST {path} completed in {time.perf_counter() - started_at:.3f}s")
            return

        if path == "/api/interview/questions":
            output = get_interview_module().build_interview_set(payload)
            json_response(self, 200, output)
            log_event(f"POST {path} completed in {time.perf_counter() - started_at:.3f}s")
            return

        if path == "/api/interview/evaluate":
            output = get_interview_module().score_answer(
                payload.get("question", ""),
                payload.get("answer_text", ""),
                payload.get("audio_features", {}),
            )
            json_response(self, 200, output)
            log_event(f"POST {path} completed in {time.perf_counter() - started_at:.3f}s")
            return

        if path == "/api/history":
            from DB import history_store

            row_id = history_store.add_history(payload)
            json_response(self, 200, {"id": row_id})
            log_event(f"POST {path} completed in {time.perf_counter() - started_at:.3f}s")
            return

        rag = get_rag_module()
        output = rag.run_rag(
            large=payload.get("large", ""),
            medium=payload.get("medium", ""),
            small=payload.get("small", ""),
            job_keyword=payload.get("job_keyword", ""),
            query=payload.get("query", ""),
            top_k=int(payload.get("top_k", 5)),
            target_company=payload.get("target_company", ""),
            target_job=payload.get("target_job", ""),
            user_profile=payload.get("user_profile", ""),
            structured_profile=payload.get("structured_profile", {}),
            documents=get_documents(),
        )
        json_response(self, 200, rag.serialize_rag_output(output))
        log_event(f"POST {path} completed in {time.perf_counter() - started_at:.3f}s")

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


def parse_args():
    parser = argparse.ArgumentParser(description="Cover Letter RAG web server")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    return parser.parse_args()


def main():
    args = parse_args()
    log_event("starting RAG server")
    server = ThreadingHTTPServer((args.host, args.port), RagHandler)
    log_event(f"RAG server listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
