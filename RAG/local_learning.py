def profile_value(profile, *keys):
    for key in keys:
        value = (profile or {}).get(key)
        if value:
            return value
    return ""


def save_generated_drafts(serialized, provider):
    try:
        from DB import history_store
    except Exception:
        return []

    api_input = serialized.get("api_input", {})
    structured_profile = api_input.get("structured_profile") or {}
    normalized_profile = {
        "major": profile_value(structured_profile, "major", "education"),
        "certificates": profile_value(structured_profile, "certificates"),
        "team_projects": profile_value(structured_profile, "team_projects", "projects"),
        "other_specs": profile_value(structured_profile, "other_specs", "other", "skills", "experience"),
    }
    plan_questions = serialized.get("interview_plan", {}).get("questions", [])
    generated_drafts = [
        item
        for item in serialized.get("drafts", [])
        if item.get("draft_type") != "needs_input"
        and item.get("evidence_status") == "matched"
        and (provider == "local_rag" or item.get(f"{provider}_generated"))
        and item.get("draft", "").strip()
    ]
    if not generated_drafts:
        serialized["local_learning"] = {
            "enabled": True,
            "provider": provider,
            "saved_count": 0,
            "saved_ids": [],
        }
        return []

    cover_letter = "\n\n".join(
        [
            f"[{index}. {item.get('question', '자소서 문항')}]\n{item.get('draft', '').strip()}"
            for index, item in enumerate(generated_drafts, start=1)
        ]
    )
    draft_questions = [item.get("question", "") for item in generated_drafts if item.get("question")]
    related_questions = []
    for question in draft_questions + plan_questions:
        if question and question not in related_questions:
            related_questions.append(question)

    payload = {
        "occupation_label": "Generated cover letter",
        "large": api_input.get("large", ""),
        "medium": api_input.get("medium", ""),
        "target_company": api_input.get("target_company", ""),
        "target_job": api_input.get("target_job", ""),
        "structured_profile": normalized_profile,
        "question": " / ".join(draft_questions[:3]) or "문항별 자기소개서 생성 결과",
        "answer_text": "생성된 자기소개서 문항을 기준으로 본인이 직접 한 행동, 사용한 기술/방식, 결과 확인 과정을 면접에서 설명할 수 있어야 합니다.",
        "cover_letter": cover_letter,
        "related_questions": related_questions,
        "score": 0,
        "source_note": f"{provider} generated full result",
        "generation_provider": provider,
        "full_generation_result": {
            "drafts": generated_drafts,
            "questions": serialized.get("questions", []),
            "interview_plan": serialized.get("interview_plan", {}),
            "generation_provider": provider,
        },
    }
    saved_ids = [history_store.add_history(payload)]
    serialized["local_learning"] = {
        "enabled": True,
        "provider": provider,
        "saved_count": len(saved_ids),
        "saved_ids": saved_ids,
    }
    return saved_ids
