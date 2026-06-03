import argparse
import csv
import hashlib
import math
import random
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTION_CSV = ROOT / "Embedding" / "question_contexts.csv"
RESULT_CSV = ROOT / "Embedding" / "experiment_results.csv"


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def tokenize(text):
    return [token for token in (text or "").lower().split() if len(token) > 1]


def char_ngrams(text, low=3, high=5):
    compact = "".join((text or "").lower().split())
    grams = []
    for n in range(low, high + 1):
        grams.extend(compact[index : index + n] for index in range(max(0, len(compact) - n + 1)))
    return grams


def token_bigrams(text):
    tokens = tokenize(text)
    return tokens + [f"{tokens[index]}_{tokens[index + 1]}" for index in range(len(tokens) - 1)]


def feature_terms(text, mode):
    if mode == "token_unigram":
        return tokenize(text)
    if mode == "token_bigram":
        return token_bigrams(text)
    if mode == "char_3_5":
        return char_ngrams(text)
    raise ValueError(f"unknown mode: {mode}")


def hashed_vector(text, mode, dimensions):
    counts = Counter()
    for term in feature_terms(text, mode):
        digest = hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, "little") % dimensions
        counts[index] += 1.0
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {index: value / norm for index, value in counts.items()}


def cosine(left, right):
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(index, 0.0) for index, value in left.items())


def build_query(row):
    return " ".join(
        [
            row.get("job", ""),
            row.get("large", ""),
            row.get("medium", ""),
            row.get("question_label", ""),
            row.get("question_text", ""),
        ]
    )


def evaluate(rows, context_field, mode, dimensions, sample_size):
    sample = rows[:]
    random.Random(42).shuffle(sample)
    sample = sample[: min(sample_size, len(sample))]
    doc_vectors = [hashed_vector(row[context_field], mode, dimensions) for row in rows]

    label_hits = 0
    source_hits = 0
    mrr_total = 0.0
    examples = []
    for query_row in sample:
        query_vector = hashed_vector(build_query(query_row), mode, dimensions)
        scored = []
        for doc_index, document in enumerate(rows):
            if document["question_id"] == query_row["question_id"]:
                continue
            scored.append((cosine(query_vector, doc_vectors[doc_index]), document))
        scored.sort(key=lambda item: item[0], reverse=True)
        top5 = scored[:5]
        if any(doc["question_label"] == query_row["question_label"] for _, doc in top5):
            label_hits += 1
        if any(doc["source_row"] == query_row["source_row"] for _, doc in top5):
            source_hits += 1
        reciprocal = 0.0
        for rank, (_, doc) in enumerate(scored[:20], start=1):
            if doc["question_label"] == query_row["question_label"]:
                reciprocal = 1.0 / rank
                break
        mrr_total += reciprocal
        if len(examples) < 3 and top5:
            examples.append(
                {
                    "query": query_row["question_text"][:80],
                    "expected_label": query_row["question_label"],
                    "top_label": top5[0][1]["question_label"],
                    "top_score": round(top5[0][0], 4),
                }
            )
    total = len(sample) or 1
    return {
        "context_field": context_field,
        "mode": mode,
        "dimensions": dimensions,
        "sample_size": len(sample),
        "label_hit_at_5": round(label_hits / total, 4),
        "same_source_hit_at_5": round(source_hits / total, 4),
        "label_mrr_at_20": round(mrr_total / total, 4),
        "examples": examples,
    }


def write_results(results, output_csv):
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "context_field",
                "mode",
                "dimensions",
                "sample_size",
                "label_hit_at_5",
                "same_source_hit_at_5",
                "label_mrr_at_20",
                "examples",
            ],
        )
        writer.writeheader()
        writer.writerows(results)


def main():
    parser = argparse.ArgumentParser(description="Run context-length embedding retrieval experiments.")
    parser.add_argument("--input", type=Path, default=QUESTION_CSV)
    parser.add_argument("--output", type=Path, default=RESULT_CSV)
    parser.add_argument("--sample-size", type=int, default=500)
    parser.add_argument("--max-docs", type=int, default=5000)
    parser.add_argument("--dimensions", type=int, default=4096)
    parser.add_argument("--include-char-ngrams", action="store_true")
    args = parser.parse_args()

    rows = read_csv(args.input)
    random.Random(7).shuffle(rows)
    rows = rows[: min(args.max_docs, len(rows))]
    experiments = []
    modes = ["token_unigram", "token_bigram"]
    if args.include_char_ngrams:
        modes.append("char_3_5")
    for context_field in ["context_300", "context_600", "context_1000"]:
        for mode in modes:
            print(f"running context={context_field} mode={mode}", flush=True)
            result = evaluate(rows, context_field, mode, args.dimensions, args.sample_size)
            experiments.append(result)
            print(result, flush=True)
    write_results(experiments, args.output)
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
