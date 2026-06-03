import argparse
import csv
import hashlib
import json
import math
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTION_CSV = ROOT / "Embedding" / "question_contexts.csv"
DB_PATH = ROOT / "Embedding" / "embedding_store.sqlite"
DEFAULT_POSTGRES_URL = "postgresql://rag:rag_password@127.0.0.1:5432/cover_letter_rag"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9가-힣+#.]+")


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def tokenize(text):
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token) > 1]


def split_sentences(text):
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []
    sentences = []
    start = 0
    for match in re.finditer(r"(?:[.!?。]|다\.|요\.|니다\.)\s+", normalized):
        end = match.end()
        sentence = normalized[start:end].strip()
        if len(sentence) >= 20:
            sentences.append(sentence)
        start = end
    tail = normalized[start:].strip()
    if len(tail) >= 20:
        sentences.append(tail)
    return sentences


def hashed_sparse_vector(text, dimensions):
    counts = Counter()
    for token in tokenize(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, "little") % dimensions
        counts[index] += 1.0
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {str(index): round(value / norm, 6) for index, value in counts.items()}


def connect_sqlite(db_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS embedding_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL,
            source_row INTEGER,
            unit_type TEXT NOT NULL,
            unit_index INTEGER NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            company TEXT,
            job TEXT,
            large TEXT,
            medium TEXT,
            question_label TEXT,
            question_text TEXT,
            text TEXT NOT NULL,
            vector_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_embedding_unit ON embedding_items(unit_type, model)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_embedding_question ON embedding_items(question_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_embedding_label ON embedding_items(question_label)")
    return connection


def connect_postgres(database_url):
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg[binary] is required for PostgreSQL storage.") from exc

    connection = psycopg.connect(database_url)
    connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS embedding_items (
            id BIGSERIAL PRIMARY KEY,
            question_id TEXT NOT NULL,
            source_row INTEGER,
            unit_type TEXT NOT NULL,
            unit_index INTEGER NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            company TEXT,
            job TEXT,
            large TEXT,
            medium TEXT,
            question_label TEXT,
            question_text TEXT,
            text TEXT NOT NULL,
            vector_json JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_embedding_unit ON embedding_items(unit_type, model)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_embedding_question ON embedding_items(question_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_embedding_label ON embedding_items(question_label)")
    return connection


def insert_item(connection, row, unit_type, unit_index, text, dimensions, backend):
    vector = hashed_sparse_vector(text, dimensions)
    values = (
        row["question_id"],
        int(row.get("source_row") or 0),
        unit_type,
        unit_index,
        "hashed-token-v1",
        dimensions,
        row.get("company", ""),
        row.get("job", ""),
        row.get("large", ""),
        row.get("medium", ""),
        row.get("question_label", ""),
        row.get("question_text", ""),
        text,
        json.dumps(vector, ensure_ascii=False, separators=(",", ":")),
    )
    placeholder = "%s" if backend == "postgres" else "?"
    placeholders = ", ".join([placeholder] * len(values))
    connection.execute(
        f"""
        INSERT INTO embedding_items (
            question_id, source_row, unit_type, unit_index, model, dimensions,
            company, job, large, medium, question_label, question_text, text, vector_json
        )
        VALUES ({placeholders})
        """,
        values,
    )


def rebuild_store(
    question_csv=QUESTION_CSV,
    db_path=DB_PATH,
    database_url=None,
    dimensions=4096,
    units=None,
    max_rows=0,
):
    rows = read_csv(question_csv)
    if max_rows:
        rows = rows[:max_rows]
    units = set(units or ["sentence", "context"])
    backend = "postgres" if database_url else "sqlite"
    connection = connect_postgres(database_url) if database_url else connect_sqlite(db_path)
    connection.execute("DELETE FROM embedding_items")

    inserted = Counter()
    for row in rows:
        if "word" in units:
            words = sorted(set(tokenize(" ".join([row.get("question_text", ""), row.get("answer", "")]))))
            for index, word in enumerate(words):
                insert_item(connection, row, "word", index, word, dimensions, backend)
                inserted["word"] += 1

        if "sentence" in units:
            for index, sentence in enumerate(split_sentences(row.get("answer", ""))):
                insert_item(connection, row, "sentence", index, sentence, dimensions, backend)
                inserted["sentence"] += 1

        if "context" in units:
            context = row.get("context_600") or " ".join([row.get("question_text", ""), row.get("answer", "")])
            insert_item(connection, row, "context", 0, context, dimensions, backend)
            inserted["context"] += 1

    connection.commit()
    connection.close()
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Build a local SQLite embedding store.")
    parser.add_argument("--input", type=Path, default=QUESTION_CSV)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--postgres", action="store_true", help="Store vectors in PostgreSQL instead of SQLite.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", DEFAULT_POSTGRES_URL))
    parser.add_argument("--dimensions", type=int, default=4096)
    parser.add_argument("--units", default="sentence,context", help="Comma-separated units: word,sentence,context")
    parser.add_argument("--max-rows", type=int, default=0, help="Limit question rows for quick tests. 0 means all rows.")
    args = parser.parse_args()

    database_url = args.database_url if args.postgres else None
    units = [unit.strip() for unit in args.units.split(",") if unit.strip()]
    inserted = rebuild_store(args.input, args.db, database_url, args.dimensions, units, args.max_rows)
    print(f"wrote={database_url or args.db}")
    for unit_type, count in inserted.items():
        print(f"{unit_type}: {count:,}")


if __name__ == "__main__":
    main()
