const stateKey = "ttsCoverLetterPrep";
let categories = [];
let interviewState = {
  activeTab: "basic",
  questions: {
    basic: [],
    personalized: [],
    dataset: [],
  },
  selectedQuestion: "",
  startedAt: 0,
  mediaRecorder: null,
  recognition: null,
  recordedChunks: [],
  lastScore: null,
};
let historyState = {
  items: [],
  selectedIndex: 0,
  page: 1,
  pageSize: 5,
};

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function unique(values) {
  return [...new Set(values.filter(Boolean))].sort();
}

function option(value, label) {
  const item = document.createElement("option");
  item.value = value;
  item.textContent = label || value || "전체";
  return item;
}

function saveState(data) {
  sessionStorage.setItem(stateKey, JSON.stringify(data));
}

function loadState() {
  try {
    return JSON.parse(sessionStorage.getItem(stateKey) || "{}");
  } catch {
    return {};
  }
}

function generationPayload() {
  const apiKey = $("gemini-api-key")?.value.trim() || "";
  if (!apiKey) return null;
  return {
    provider: "gemini",
    use_gemini: true,
    api_key: apiKey,
    model: "gemini-2.5-flash",
    output_style: "자기소개서 문체",
    paragraphs: 3,
    min_chars: 1000,
    max_chars: 1500,
    temperature: Number($("gemini-temperature")?.value || 0.2),
    max_tokens: Number($("gemini-max-tokens")?.value || 4096),
    timeout: 120,
    retries: 2,
  };
}

function withoutApiKey(payload) {
  const copy = JSON.parse(JSON.stringify(payload || {}));
  if (copy.generation?.api_key) {
    copy.generation.api_key = "";
    copy.generation.api_key_provided = true;
  }
  return copy;
}

function fillLarge() {
  const large = $("large");
  if (!large) return;
  large.innerHTML = "";
  large.appendChild(option("", "전체"));
  unique(categories.map((item) => item.large)).forEach((value) => large.appendChild(option(value)));
  fillMedium();
}

function fillMedium() {
  const large = $("large");
  const medium = $("medium");
  if (!large || !medium) return;
  medium.innerHTML = "";
  medium.appendChild(option("", "전체"));
  unique(categories.filter((item) => !large.value || item.large === large.value).map((item) => item.medium))
    .forEach((value) => medium.appendChild(option(value)));
}

async function loadCategories() {
  const large = $("large");
  if (!large) return;
  const response = await fetch("/api/categories");
  categories = await response.json();
  fillLarge();
}

function renderQuestions(questions = []) {
  if (!questions.length) {
    return `<div class="empty-state">공통 질문이 없습니다.</div>`;
  }
  return questions.slice(0, 5).map((item, index) => `
    <div class="list-item">
      <strong>${index + 1}. ${escapeHtml(item.question)}</strong>
      <span class="meta">${escapeHtml(item.count)}회 · 예시 회사 ${escapeHtml((item.example_companies || []).join(", ") || "없음")}</span>
    </div>
  `).join("");
}

function renderKeywords(plan = {}) {
  const values = plan.focus_areas || ["직무 역량", "협업", "문제 해결"];
  return values.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
}

function renderResults(results = []) {
  if (!results.length) {
    return `<div class="empty-state">조건에 맞는 참고 context가 없습니다.</div>`;
  }
  return results.map((item, index) => `
    <div class="list-item">
      <strong>${index + 1}. ${escapeHtml(item.company)} / ${escapeHtml(item.job)}</strong>
      <span class="meta">score ${escapeHtml(item.score)} · ${escapeHtml(item.source_type || "question_context")} · ${escapeHtml(item.question_label || "질문")}</span>
      <p>${escapeHtml(item.preview)}</p>
    </div>
  `).join("");
}

function renderDrafts(drafts = []) {
  if (!drafts.length) {
    return `<div class="empty-state">홈에서 준비 결과를 먼저 생성하세요.</div>`;
  }
  return drafts.map((item) => `
    <article class="draft-block">
      <strong>${escapeHtml(item.index)}. ${escapeHtml(item.question)}</strong>
      <span class="meta">${escapeHtml(item.label)} · 참고 ${escapeHtml(item.source_count)}회 · ${escapeHtml(item.draft_chars || 0)}자 · ${item.gemini_generated ? "Gemini 생성" : "기존 방식 생성"} · ${item.evidence_status === "matched" ? "문항 적합 스펙 사용" : "추가 경험 필요"}</span>
      ${item.gemini_error ? `<p class="error-line">${escapeHtml(item.gemini_error)}</p>` : ""}
      ${(item.evidence_items || []).length ? `<div class="evidence-list">${item.evidence_items.map((evidence) => {
        const label = typeof evidence === "object" ? evidence.field_label : "스펙";
        const text = typeof evidence === "object" ? evidence.text : evidence;
        return `<span>${escapeHtml(label)} · ${escapeHtml(text)}</span>`;
      }).join("")}</div>` : ""}
      <div class="draft-body">${escapeHtml(item.draft)}</div>
      ${(item.reference_examples || []).length ? `
        <div class="reference-box">
          <strong>Top-K 참고 흐름</strong>
          ${(item.reference_examples || []).slice(0, 2).map((ref) => `
            <p>${escapeHtml(ref.company || "참고 사례")} · ${escapeHtml(ref.usable_pattern || "")}<br>${escapeHtml(ref.preview || "")}</p>
          `).join("")}
        </div>
      ` : ""}
      <ul class="notes-list">
        ${(item.edit_notes || []).map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
      </ul>
    </article>
  `).join("");
}

function renderInterview(plan = {}) {
  const questions = plan.questions || [];
  if (!questions.length) {
    return `<div class="empty-state">홈에서 준비 결과를 먼저 생성하세요.</div>`;
  }
  return questions.map((question, index) => `
    <div class="list-item">
      <strong>${index + 1}. ${escapeHtml(question)}</strong>
    </div>
  `).join("");
}

function renderInterviewCards(items = []) {
  if (!items.length) {
    return `<div class="empty-state">질문을 불러오지 못했습니다. 스펙을 입력한 뒤 다시 시도하세요.</div>`;
  }
  return items.map((item, index) => {
    const question = item.question || item;
    const meta = [
      item.category,
      item.occupation_label,
      item.intent_category,
      item.emotion_category,
    ].filter(Boolean).join(" · ");
    const tip = item.answer_tip || item.summary || item.answer_preview || "";
    return `
      <button class="interview-question" type="button" data-question="${escapeHtml(question)}">
        <strong>${index + 1}. ${escapeHtml(question)}</strong>
        ${meta ? `<span class="meta">${escapeHtml(meta)}</span>` : ""}
        ${tip ? `<p>${escapeHtml(tip)}</p>` : ""}
      </button>
    `;
  }).join("");
}

function setInterviewTab(tab) {
  interviewState.activeTab = tab;
  document.querySelectorAll("[data-interview-tab]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.interviewTab === tab);
  });
  $("interview") && ($("interview").innerHTML = renderInterviewCards(interviewState.questions[tab] || []));
}

function savedInterviewPayload() {
  const data = loadState();
  return {
    large: data.input?.large || "",
    medium: data.input?.medium || "",
    target_company: data.input?.target_company || "",
    target_job: data.input?.target_job || "",
    user_profile: data.input?.user_profile || "",
    structured_profile: data.input?.structured_profile || {},
  };
}

async function loadInterviewQuestions() {
  const status = $("interview-status");
  status && (status.textContent = "AI Hub 면접 데이터셋에서 질문을 불러오는 중입니다.");
  try {
    const response = await fetch("/api/interview/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(savedInterviewPayload()),
    });
    const output = await response.json();
    interviewState.questions = {
      basic: output.basic_questions || [],
      personalized: output.personalized_questions || [],
      dataset: output.dataset_questions || [],
    };
    const zipCount = output.dataset?.status?.zip_count || 0;
    const rowCount = output.dataset?.row_count || 0;
    status && (status.textContent = `라벨 ZIP ${zipCount}개, 면접 Q&A ${rowCount.toLocaleString()}개를 기준으로 준비했습니다.`);
    setInterviewTab(interviewState.activeTab);
  } catch {
    status && (status.textContent = "면접 질문을 불러오지 못했습니다. 서버와 데이터셋 경로를 확인하세요.");
    setInterviewTab(interviewState.activeTab);
  }
}

function selectPracticeQuestion(question) {
  interviewState.selectedQuestion = question;
  $("practice-question") && ($("practice-question").textContent = question);
  document.querySelectorAll(".interview-question").forEach((button) => {
    button.classList.toggle("is-selected", button.dataset.question === question);
  });
}

function speechRecognitionFactory() {
  return window.SpeechRecognition || window.webkitSpeechRecognition;
}

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia) {
    $("record-status").textContent = "이 브라우저에서는 마이크 녹음을 사용할 수 없습니다.";
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  interviewState.recordedChunks = [];
  interviewState.startedAt = performance.now();
  interviewState.mediaRecorder = new MediaRecorder(stream);
  interviewState.mediaRecorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) interviewState.recordedChunks.push(event.data);
  });
  interviewState.mediaRecorder.addEventListener("stop", () => {
    stream.getTracks().forEach((track) => track.stop());
  });
  interviewState.mediaRecorder.start();

  const Recognition = speechRecognitionFactory();
  if (Recognition) {
    const recognition = new Recognition();
    recognition.lang = "ko-KR";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      let transcript = "";
      for (let index = 0; index < event.results.length; index += 1) {
        transcript += event.results[index][0].transcript;
      }
      $("spoken-answer").value = transcript.trim();
    };
    recognition.onerror = () => {
      $("record-status").textContent = "음성 인식이 중단되었습니다. 녹음은 계속될 수 있으니 답변을 직접 수정해도 됩니다.";
    };
    recognition.start();
    interviewState.recognition = recognition;
  }

  $("record-toggle").textContent = "마이크 중지";
  $("record-status").textContent = "녹음 중입니다. 답변을 마치면 마이크 중지를 누르세요.";
}

function stopRecording() {
  if (interviewState.mediaRecorder?.state === "recording") {
    interviewState.mediaRecorder.stop();
  }
  if (interviewState.recognition) {
    interviewState.recognition.stop();
  }
  $("record-toggle").textContent = "마이크 시작";
  $("record-status").textContent = "녹음이 끝났습니다. 인식된 답변을 확인하고 점수를 볼 수 있습니다.";
}

async function toggleRecording() {
  if (interviewState.mediaRecorder?.state === "recording") {
    stopRecording();
    return;
  }
  try {
    await startRecording();
  } catch {
    $("record-status").textContent = "마이크 권한을 가져오지 못했습니다. 브라우저 권한을 확인해주세요.";
  }
}

async function evaluateAnswer() {
  const question = interviewState.selectedQuestion || $("practice-question")?.textContent || "";
  const answerText = $("spoken-answer")?.value.trim() || "";
  if (!question || !answerText) {
    $("interview-score-note").textContent = "질문을 선택하고 답변을 입력한 뒤 평가하세요.";
    return;
  }
  const duration = interviewState.startedAt ? Math.max(0, (performance.now() - interviewState.startedAt) / 1000) : 0;
  const response = await fetch("/api/interview/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      answer_text: answerText,
      audio_features: {
        duration_seconds: duration,
      },
    }),
  });
  const output = await response.json();
  interviewState.lastScore = output;
  $("interview-score").textContent = output.total ?? "--";
  $("interview-score-title").textContent = output.total >= 80 ? "좋은 답변" : output.total >= 65 ? "보완 필요" : "연습 필요";
  $("interview-score-note").textContent = (output.feedback || []).join(" ");
  $("rubric").innerHTML = (output.rubric || []).map((item) => `
    <div class="list-item">
      <strong>${escapeHtml(item.label)} ${escapeHtml(item.score)} / ${escapeHtml(item.max)}</strong>
      <div class="meter"><span style="width: ${Math.min(100, Math.round(item.score / item.max * 100))}%"></span></div>
    </div>
  `).join("");
}

async function saveInterviewHistory() {
  const data = loadState();
  const answerText = $("spoken-answer")?.value.trim() || "";
  const score = interviewState.lastScore?.total || Number($("interview-score")?.textContent) || 0;
  if (!interviewState.selectedQuestion || !answerText) {
    $("record-status").textContent = "질문과 답변이 있어야 히스토리에 저장할 수 있습니다.";
    return;
  }
  const payload = {
    occupation_label: data.input?.large || "Custom",
    target_job: data.input?.target_job || "",
    structured_profile: data.input?.structured_profile || {},
    question: interviewState.selectedQuestion,
    answer_text: answerText,
    cover_letter: (data.output?.drafts || []).map((draft) => draft.draft).filter(Boolean).join("\n\n"),
    related_questions: data.output?.interview_plan?.questions || [],
    score,
    evaluation: interviewState.lastScore || {},
  };
  const response = await fetch("/api/history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (response.ok) {
    $("record-status").textContent = "히스토리에 저장했습니다.";
  } else {
    $("record-status").textContent = "히스토리 저장에 실패했습니다.";
  }
}

function renderHistory(items = []) {
  if (!items.length) {
    return `<div class="empty-state">저장된 히스토리가 없습니다.</div>`;
  }
  const start = (historyState.page - 1) * historyState.pageSize;
  const pageItems = items.slice(start, start + historyState.pageSize);
  return pageItems.map((item, index) => {
    const globalIndex = start + index;
    return `
    <button class="history-card ${globalIndex === historyState.selectedIndex ? "is-selected" : ""}" type="button" data-history-index="${globalIndex}">
      <div class="history-score">${escapeHtml(item.score)}</div>
      <div>
        <div class="history-meta">
          <span>${escapeHtml(item.occupation_label)}</span>
          <span>${escapeHtml(item.target_job)}</span>
          <span>${escapeHtml(item.created_at)}</span>
        </div>
        <h3>${escapeHtml(item.question)}</h3>
        <p>${escapeHtml(item.answer_text)}</p>
        <div class="evidence-list">
          <span>전공 · ${escapeHtml(item.major || "없음")}</span>
          <span>자격증 · ${escapeHtml(item.certificates || "없음")}</span>
          <span>팀프로젝트 · ${escapeHtml(item.team_projects || "없음")}</span>
          <span>기타 · ${escapeHtml(item.other_specs || "없음")}</span>
        </div>
      </div>
    </button>
  `;
  }).join("");
}

function renderHistoryPagination() {
  const totalPages = Math.max(1, Math.ceil(historyState.items.length / historyState.pageSize));
  if (totalPages <= 1) return "";
  return Array.from({ length: totalPages }, (_, index) => {
    const page = index + 1;
    return `<button class="page-button ${page === historyState.page ? "is-active" : ""}" type="button" data-history-page="${page}">${page}</button>`;
  }).join("");
}

function renderHistoryDetail(item) {
  if (!item) {
    return `<div class="empty-state">왼쪽 샘플을 클릭하면 자소서와 관련 면접 질문을 확인할 수 있습니다.</div>`;
  }
  const relatedQuestions = item.related_questions || [];
  return `
    <div class="detail-heading">
      <div>
        <p class="card-label">${escapeHtml(item.occupation_label)}</p>
        <h2>${escapeHtml(item.target_job)}</h2>
      </div>
      <div class="history-score large-score">${escapeHtml(item.score)}</div>
    </div>
    <div class="evidence-list">
      <span>전공 · ${escapeHtml(item.major || "없음")}</span>
      <span>자격증 · ${escapeHtml(item.certificates || "없음")}</span>
      <span>팀프로젝트 · ${escapeHtml(item.team_projects || "없음")}</span>
      <span>기타 · ${escapeHtml(item.other_specs || "없음")}</span>
    </div>
    <section class="detail-section">
      <p class="card-label">자소서 Sample</p>
      <div class="draft-body">${escapeHtml(item.cover_letter || "저장된 자소서 본문이 없습니다.")}</div>
    </section>
    <section class="detail-section">
      <p class="card-label">관련 면접 질문</p>
      <div class="stack-list">
        ${relatedQuestions.map((question, index) => `
          <div class="list-item">
            <strong>${index + 1}. ${escapeHtml(question)}</strong>
          </div>
        `).join("") || `<div class="empty-state">관련 질문이 없습니다.</div>`}
      </div>
    </section>
    <section class="detail-section">
      <p class="card-label">샘플 답변</p>
      <p class="detail-answer">${escapeHtml(item.answer_text)}</p>
    </section>
  `;
}

function selectHistory(index) {
  historyState.selectedIndex = Number(index) || 0;
  historyState.page = Math.floor(historyState.selectedIndex / historyState.pageSize) + 1;
  $("history-list") && ($("history-list").innerHTML = renderHistory(historyState.items));
  $("history-pagination") && ($("history-pagination").innerHTML = renderHistoryPagination());
  $("history-detail") && ($("history-detail").innerHTML = renderHistoryDetail(historyState.items[historyState.selectedIndex]));
}

function selectHistoryPage(page) {
  historyState.page = Number(page) || 1;
  const start = (historyState.page - 1) * historyState.pageSize;
  historyState.selectedIndex = Math.min(start, Math.max(0, historyState.items.length - 1));
  $("history-list") && ($("history-list").innerHTML = renderHistory(historyState.items));
  $("history-pagination") && ($("history-pagination").innerHTML = renderHistoryPagination());
  $("history-detail") && ($("history-detail").innerHTML = renderHistoryDetail(historyState.items[historyState.selectedIndex]));
}

async function loadHistory() {
  const summary = $("history-summary");
  const list = $("history-list");
  try {
    const response = await fetch("/api/history");
    const output = await response.json();
    const items = output.items || [];
    historyState.items = items;
    historyState.selectedIndex = 0;
    historyState.page = 1;
    summary && (summary.textContent = `SQLite DB에서 ${items.length.toLocaleString()}개의 샘플 자소서와 관련 면접 질문을 불러왔습니다.`);
    list && (list.innerHTML = renderHistory(items));
    $("history-pagination") && ($("history-pagination").innerHTML = renderHistoryPagination());
    $("history-detail") && ($("history-detail").innerHTML = renderHistoryDetail(items[0]));
  } catch {
    summary && (summary.textContent = "히스토리를 불러오지 못했습니다.");
    list && (list.innerHTML = `<div class="empty-state">서버 상태를 확인하세요.</div>`);
  }
}

function hydrateHome(data) {
  if (!data.output) return;
  const gemini = data.output.gemini;
  let geminiText = "";
  if (gemini?.fallback_to_local) {
    geminiText = ` ${gemini.fallback_reason || "Gemini 대신 기존 방식으로 생성했습니다."}`;
  } else if (gemini?.enabled) {
    geminiText = ` Gemini ${gemini.success_count || 0}/${gemini.attempted_count || (data.output.drafts || []).length}개 재생성.`;
  }
  $("summary").textContent = `직무 후보 ${data.output.filtered_count.toLocaleString()}건을 참고해 공통 질문 ${data.output.questions.length}개와 면접 질문을 만들었습니다.${geminiText}`;
  $("score-value").textContent = "87";
  $("score-title").textContent = "상위 15%";
  $("score-note").textContent = "입력한 스펙을 기준으로 자소서와 면접 준비 흐름을 구성했습니다.";
  $("questions").innerHTML = renderQuestions(data.output.questions);
  $("keywords").innerHTML = renderKeywords(data.output.interview_plan);
  $("results").innerHTML = renderResults(data.output.results);
  $("api-seed").textContent = JSON.stringify(data.output.interview_api_seed || {}, null, 2);
  $("prompt").textContent = data.output.prompt || "";
}

async function runPrep(event) {
  event.preventDefault();
  const button = $("run");
  const payload = {
    large: $("large").value,
    medium: $("medium").value,
    target_company: $("company").value.trim(),
    target_job: $("job").value.trim(),
    user_profile: $("profile").value.trim(),
    structured_profile: {
      major: $("major").value.trim(),
      certificates: $("certificates").value.trim(),
      team_projects: $("team-projects").value.trim(),
      other_specs: $("other-specs").value.trim(),
      age: $("age").value,
      gender: $("gender").value,
    },
    top_k: 8,
  };
  const generation = generationPayload();
  if (generation) payload.generation = generation;

  const hasProfile = payload.user_profile || Object.entries(payload.structured_profile)
    .some(([key, value]) => !["age", "gender"].includes(key) && value);
  if (!payload.target_job || !hasProfile) {
    $("summary").textContent = "갖고 싶은 직무/직업과 학과, 자격증, 팀프로젝트, 기타 스펙 중 하나 이상을 입력해주세요.";
    return;
  }

  button.disabled = true;
  button.textContent = "생성 중...";
  try {
    const response = await fetch("/api/prepare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const output = await response.json();
    const data = { input: withoutApiKey(payload), output };
    saveState(data);
    hydrateHome(data);
  } catch {
    $("summary").textContent = "생성 중 오류가 발생했습니다. 서버 상태를 확인한 뒤 다시 시도하세요.";
  } finally {
    button.disabled = false;
    button.textContent = "준비 결과 생성";
  }
}

function initHome() {
  const saved = loadState();
  if (saved.input) {
    $("company").value = saved.input.target_company || "";
    $("job").value = saved.input.target_job || "";
    $("profile").value = saved.input.user_profile || "";
    $("major").value = saved.input.structured_profile?.major || "";
    $("certificates").value = saved.input.structured_profile?.certificates || "";
    $("team-projects").value = saved.input.structured_profile?.team_projects || "";
    $("other-specs").value = saved.input.structured_profile?.other_specs || "";
    $("age").value = saved.input.structured_profile?.age || "";
    $("gender").value = saved.input.structured_profile?.gender || "";
  }
  hydrateHome(saved);
  $("large")?.addEventListener("change", fillMedium);
  $("prep-form")?.addEventListener("submit", runPrep);
  loadCategories().then(() => {
    if (saved.input) {
      $("large").value = saved.input.large || "";
      fillMedium();
      $("medium").value = saved.input.medium || "";
    }
  });
}

function initCoverLetterPage() {
  const data = loadState();
  $("drafts") && ($("drafts").innerHTML = renderDrafts(data.output?.drafts || []));
  $("draft-meta") && ($("draft-meta").textContent = data.input?.target_job ? `${data.input.target_company || "지원 회사"} · ${data.input.target_job}` : "저장된 준비 결과가 없습니다.");
}

function initInterviewPage() {
  const data = loadState();
  $("answer-rule") && ($("answer-rule").textContent = data.output?.interview_plan?.answer_rule || "홈에서 준비 결과를 먼저 생성하세요.");
  $("focus-areas") && ($("focus-areas").innerHTML = renderKeywords(data.output?.interview_plan || {}));
  $("refresh-interview")?.addEventListener("click", loadInterviewQuestions);
  $("interview")?.addEventListener("click", (event) => {
    const button = event.target.closest(".interview-question");
    if (button) selectPracticeQuestion(button.dataset.question);
  });
  document.querySelectorAll("[data-interview-tab]").forEach((button) => {
    button.addEventListener("click", () => setInterviewTab(button.dataset.interviewTab));
  });
  $("record-toggle")?.addEventListener("click", toggleRecording);
  $("clear-answer")?.addEventListener("click", () => {
    $("spoken-answer").value = "";
    $("record-status").textContent = "답변을 지웠습니다.";
  });
  $("evaluate-answer")?.addEventListener("click", evaluateAnswer);
  $("save-history")?.addEventListener("click", saveInterviewHistory);
  if (data.output?.interview_plan?.questions?.length) {
    interviewState.questions.basic = data.output.interview_plan.questions.map((question) => ({
      type: "basic",
      category: "기존 준비 질문",
      question,
      answer_tip: data.output.interview_plan.answer_rule || "",
    }));
    setInterviewTab("basic");
  }
  loadInterviewQuestions();
}

function initHistoryPage() {
  $("refresh-history")?.addEventListener("click", loadHistory);
  $("history-list")?.addEventListener("click", (event) => {
    const card = event.target.closest("[data-history-index]");
    if (card) selectHistory(card.dataset.historyIndex);
  });
  $("history-pagination")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-history-page]");
    if (button) selectHistoryPage(button.dataset.historyPage);
  });
  loadHistory();
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "home") initHome();
  if (page === "cover-letter") initCoverLetterPage();
  if (page === "interview") initInterviewPage();
  if (page === "history") initHistoryPage();
});
