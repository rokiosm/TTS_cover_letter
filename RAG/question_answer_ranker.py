import argparse
import csv
import json
from pathlib import Path

from RAG.draft_generator import cosine_similarity, jaccard_similarity, question_label


ROOT = Path(__file__).resolve().parents[1]
QUESTION_CONTEXT_PATH = ROOT / "Embedding" / "question_contexts.csv"
WEIGHTS_PATH = ROOT / "RAG" / "question_answer_ranker.json"

DEFAULT_WEIGHTS = {
    "question": 0.34,
    "job": 0.16,
    "category": 0.12,
    "profile": 0.20,
    "label": 0.10,
    "answer": 0.08,
}


def read_rows(path=QUESTION_CONTEXT_PATH, max_rows=0):
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    return rows[:max_rows] if max_rows else rows


def load_ranker_weights(path=WEIGHTS_PATH):
    if not path.exists():
        return DEFAULT_WEIGHTS
    try:
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
        return payload.get("weights", DEFAULT_WEIGHTS)
    except Exception:
        return DEFAULT_WEIGHTS


def save_ranker(payload, path=WEIGHTS_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def combined_similarity(left, right):
    return (cosine_similarity(left, right) * 0.65) + (jaccard_similarity(left, right) * 0.35)


def answer_embedding_text(row):
    return " ".join(
        [
            row.get("large", ""),
            row.get("medium", ""),
            row.get("small", ""),
            row.get("job", ""),
            row.get("question_label", ""),
            row.get("question_text", ""),
            row.get("spec", ""),
            row.get("context_300", ""),
            row.get("answer", ""),
            row.get("content", ""),
        ]
    )


def feature_scores(question, profile_text, target_job, document):
    question_text = document.get("question_text", "")
    answer_text = answer_embedding_text(document)
    job_text = " ".join([document.get("job", ""), document.get("large", ""), document.get("medium", ""), document.get("small", "")])
    category_text = " ".join([document.get("large", ""), document.get("medium", ""), document.get("small", ""), document.get("question_label", "")])
    spec_text = document.get("spec", "")
    label_match = 1.0 if question_label(question) == question_label(question_text or document.get("question_label", "")) else 0.0
    return {
        "question": combined_similarity(question, question_text),
        "job": combined_similarity(target_job, job_text),
        "category": combined_similarity(" ".join([target_job, question_label(question)]), category_text),
        "profile": combined_similarity(profile_text, " ".join([spec_text, answer_text[:900]])),
        "label": label_match,
        "answer": combined_similarity(question, answer_text[:1200]),
    }


def score_document(question, profile_text, target_job, document, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    features = feature_scores(question, profile_text, target_job, document)
    return sum(weights.get(name, 0) * value for name, value in features.items())


def row_score(query_row, candidate, weights):
    query_question = query_row.get("question_text", "")
    query_profile = " ".join([query_row.get("spec", ""), query_row.get("answer", "")[:400]])
    query_job = query_row.get("job", "")
    document = {
        "question_text": candidate.get("question_text", ""),
        "question_label": candidate.get("question_label", ""),
        "content": candidate.get("answer", ""),
        "answer": candidate.get("answer", ""),
        "job": candidate.get("job", ""),
        "large": candidate.get("large", ""),
        "medium": candidate.get("medium", ""),
        "small": candidate.get("small", ""),
        "spec": candidate.get("spec", ""),
        "context_300": candidate.get("context_300", ""),
    }
    return score_document(query_question, query_profile, query_job, document, weights)


def positive_candidates(row, candidates):
    positives = [
        candidate
        for candidate in candidates
        if candidate.get("source_row") == row.get("source_row")
        or (
            candidate.get("question_label") == row.get("question_label")
            and candidate.get("medium") == row.get("medium")
        )
    ]
    return positives[:8]


def normalize_weights(weights):
    cleaned = {name: max(0.0, float(value)) for name, value in weights.items()}
    total = sum(cleaned.values()) or 1.0
    return {name: round(value / total, 4) for name, value in cleaned.items()}


def train_answer_following_weights(train, learning_rate=0.08, epochs=5, negative_stride=37, margin=0.08):
    weights = dict(DEFAULT_WEIGHTS)
    feature_names = list(DEFAULT_WEIGHTS)
    updates = 0
    for epoch in range(epochs):
        for index, row in enumerate(train):
            positives = positive_candidates(row, train)
            positives = [candidate for candidate in positives if candidate.get("question_id") != row.get("question_id")]
            if not positives:
                continue
            positive = positives[0]
            negative = train[(index + (epoch + 1) * negative_stride) % len(train)]
            if negative in positives:
                continue
            query_question = row.get("question_text", "")
            query_profile = " ".join([row.get("spec", ""), row.get("answer", "")[:500]])
            query_job = row.get("job", "")
            pos_features = feature_scores(query_question, query_profile, query_job, positive)
            neg_features = feature_scores(query_question, query_profile, query_job, negative)
            pos_score = sum(weights.get(name, 0) * pos_features[name] for name in feature_names)
            neg_score = sum(weights.get(name, 0) * neg_features[name] for name in feature_names)
            if pos_score <= neg_score + margin:
                for name in feature_names:
                    weights[name] = weights.get(name, 0) + learning_rate * (pos_features[name] - neg_features[name])
                weights = normalize_weights(weights)
                updates += 1
    return normalize_weights(weights), updates


def split_train_validation(rows, validation_ratio=0.2):
    train = []
    validation = []
    interval = max(2, round(1 / validation_ratio))
    for index, row in enumerate(rows):
        if index % interval == 0:
            validation.append(row)
        else:
            train.append(row)
    return train, validation


def evaluate_weights(train, validation, weights, negative_stride=37, top_k=5):
    if not train or not validation:
        return {"top1": 0, "top5": 0, "mean_rank_score": 0, "count": 0}
    top1 = 0
    top5 = 0
    rank_score = 0.0
    for index, row in enumerate(validation):
        positives = positive_candidates(row, train)
        negatives = [train[(index + offset * negative_stride) % len(train)] for offset in range(1, 80)]
        candidates = positives + negatives
        scored = sorted(((row_score(row, candidate, weights), candidate) for candidate in candidates), reverse=True, key=lambda item: item[0])
        ranked_positive = [rank for rank, (_, candidate) in enumerate(scored, start=1) if candidate in positives]
        if ranked_positive:
            best_rank = min(ranked_positive)
            top1 += int(best_rank == 1)
            top5 += int(best_rank <= top_k)
            rank_score += 1 / best_rank
    count = len(validation)
    return {
        "top1": round(top1 / count, 4),
        "top5": round(top5 / count, 4),
        "mean_rank_score": round(rank_score / count, 4),
        "count": count,
    }


def candidate_weights():
    return [
        DEFAULT_WEIGHTS,
        {"question": 0.28, "job": 0.14, "category": 0.14, "profile": 0.24, "label": 0.10, "answer": 0.10},
        {"question": 0.30, "job": 0.20, "category": 0.16, "profile": 0.18, "label": 0.08, "answer": 0.08},
        {"question": 0.24, "job": 0.18, "category": 0.18, "profile": 0.20, "label": 0.08, "answer": 0.12},
    ]


def train_ranker(max_rows=6000, patience=2, learning_rate=0.08, epochs=5):
    rows = read_rows(max_rows=max_rows)
    train, validation = split_train_validation(rows)
    learned_weights, updates = train_answer_following_weights(train, learning_rate=learning_rate, epochs=epochs)
    best_payload = None
    stale = 0
    for epoch, weights in enumerate([learned_weights] + candidate_weights(), start=1):
        metrics = evaluate_weights(train, validation, weights)
        payload = {
            "epoch": epoch,
            "weights": weights,
            "metrics": metrics,
            "learning_rate": learning_rate,
            "learning_epochs": epochs,
            "updates": updates if epoch == 1 else 0,
            "embedding_text": "large + medium + small + job + question_label + question_text + spec + context_300 + answer",
            "train_rows": len(train),
            "validation_rows": len(validation),
            "source": str(QUESTION_CONTEXT_PATH),
        }
        if best_payload is None or metrics["mean_rank_score"] > best_payload["metrics"]["mean_rank_score"]:
            best_payload = payload
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                break
    save_ranker(best_payload)
    return best_payload


def main():
    parser = argparse.ArgumentParser(description="질문-답변 랭커 가중치를 train/validation으로 검증해 저장합니다.")
    parser.add_argument("--max-rows", type=int, default=6000)
    parser.add_argument("--patience", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--epochs", type=int, default=5)
    args = parser.parse_args()
    payload = train_ranker(args.max_rows, args.patience, args.learning_rate, args.epochs)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
