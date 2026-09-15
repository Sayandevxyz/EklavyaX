/**
 * js/quiz.js
 * ──────────
 * Client controller for the Standalone Quiz UI in EklavyaX.
 * Gated by server-side anti-gaming safeguards:
 *   - Synchronized visual timer tied to server-recorded question_shown_at
 *   - Server-driven correctness feedback (no client-side guessing)
 *   - Visible preview vs. confirmed reward badges
 *   - Transparent summary breakdown
 */

const EklavyaXQuiz = (() => {
  let currentRunId = null;
  let currentSessionId = null;
  let currentQuestionIndex = 0;
  let totalQuestions = 10;
  let questionShownAt = null;
  let selectedOptionIndex = null;
  let timerInterval = null;
  let currentStreak = 0;
  let isSubmitting = false;

  // Max timer display (default 30 seconds per question for visual progress)
  const QUESTION_TIME_LIMIT_SEC = 30;

  let initRetries = 0;
  const MAX_INIT_RETRIES = 15;

  async function init(topic = null) {
    showLoading();

    // Support topic passed in URL query param (?topic=Physics)
    if (!topic && typeof window !== "undefined" && window.location.search) {
      const urlParams = new URLSearchParams(window.location.search);
      topic = urlParams.get("topic") || null;
    }

    // Defensive check if API script is still evaluating or cached
    if (typeof window.EklavyaXAPI === "undefined" || typeof window.EklavyaXAPI.startQuiz !== "function") {
      initRetries++;
      if (initRetries <= MAX_INIT_RETRIES) {
        console.warn(`EklavyaXAPI not yet ready (attempt ${initRetries}/${MAX_INIT_RETRIES}), retrying in 200ms...`);
        setTimeout(() => init(topic), 200);
        return;
      }
      showError("Could not initialize connection to EklavyaX services. Please refresh the page or check if the server is running.");
      return;
    }

    initRetries = 0;

    try {
      const resp = await window.EklavyaXAPI.startQuiz({ topic, numQuestions: 10 });
      currentRunId = resp.quiz_run_id;
      totalQuestions = resp.total_questions;
      currentQuestionIndex = 0;
      currentStreak = 0;
      renderQuestion(resp.question);
    } catch (err) {
      showError(err.message || "Failed to start quiz.");
    }
  }

  let currentQuestion = null;

  function renderQuestion(q) {
    currentQuestion = q;
    currentSessionId = q.session_id;
    currentQuestionIndex = q.question_index;
    selectedOptionIndex = null;
    isSubmitting = false;

    // Reset EklavyaALERT banner
    const alertBanner = document.getElementById("eklavyaAlertBanner");
    if (alertBanner) alertBanner.style.display = "none";

    // Server-recorded timestamp
    questionShownAt = new Date(q.question_shown_at);

    // Update Progress
    const progressEl = document.getElementById("quizProgress");
    if (progressEl) {
      progressEl.textContent = `Question ${q.question_index + 1} of ${q.total_questions}`;
    }

    // Topic Tag
    const topicEl = document.getElementById("quizTopic");
    if (topicEl) {
      topicEl.textContent = `${q.topic} • ${q.difficulty}`;
    }

    // Streak
    updateStreakDisplay();

    // Reward Preview
    const previewCoinsEl = document.getElementById("previewCoins");
    const previewXpEl = document.getElementById("previewXp");
    if (previewCoinsEl) previewCoinsEl.textContent = `+${q.preview_coins} Coins`;
    if (previewXpEl) previewXpEl.textContent = `+${q.preview_xp} XP`;

    // Question Prompt
    const promptEl = document.getElementById("questionPrompt");
    if (promptEl) {
      promptEl.textContent = q.prompt;
    }

    // Options Grid
    const optionsContainer = document.getElementById("quizOptionsContainer");
    if (optionsContainer) {
      optionsContainer.innerHTML = "";
      const letters = ["A", "B", "C", "D"];

      q.options.forEach((optText, idx) => {
        const btn = document.createElement("button");
        btn.className = "quiz-option-btn";
        btn.setAttribute("data-option-idx", idx);
        btn.onclick = () => selectOption(idx);

        btn.innerHTML = `
          <span class="quiz-option-letter">${letters[idx] || idx + 1}</span>
          <span class="quiz-option-text">${escapeHtml(optText)}</span>
        `;
        optionsContainer.appendChild(btn);
      });
    }

    // Reset feedback banner
    const banner = document.getElementById("quizFeedbackBanner");
    if (banner) {
      banner.style.display = "none";
      banner.className = "quiz-feedback-banner";
      banner.innerHTML = "";
    }

    // Submit button state
    const submitBtn = document.getElementById("submitAnswerBtn");
    const nextBtn = document.getElementById("nextQuestionBtn");
    if (submitBtn) {
      submitBtn.style.display = "inline-flex";
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Submit Answer';
    }
    if (nextBtn) {
      nextBtn.style.display = "none";
    }

    // Start Server-Synced Visual Countdown
    startTimer();
    showCard();
  }

  // ── Option Selection ──

  function selectOption(index) {
    if (isSubmitting) return;

    selectedOptionIndex = index;
    const buttons = document.querySelectorAll(".quiz-option-btn");
    buttons.forEach((btn, idx) => {
      if (idx === index) {
        btn.classList.add("selected");
      } else {
        btn.classList.remove("selected");
      }
    });

    const submitBtn = document.getElementById("submitAnswerBtn");
    if (submitBtn) submitBtn.disabled = false;
  }

  // ── Timer Bar (Synchronized with Server question_shown_at) ──

  function startTimer() {
    if (timerInterval) clearInterval(timerInterval);

    const timerBar = document.getElementById("quizTimerBar");
    const timerText = document.getElementById("quizTimerText");

    function update() {
      const now = new Date();
      const elapsedSec = (now - questionShownAt) / 1000;
      const remainingSec = Math.max(0, QUESTION_TIME_LIMIT_SEC - elapsedSec);
      const pct = Math.max(0, (remainingSec / QUESTION_TIME_LIMIT_SEC) * 100);

      if (timerBar) {
        timerBar.style.width = `${pct}%`;
        if (pct < 25) {
          timerBar.style.background = "#ef4444";
        } else if (pct < 50) {
          timerBar.style.background = "#f4ae25";
        } else {
          timerBar.style.background = "#10b981";
        }
      }

      if (timerText) {
        timerText.textContent = `${Math.ceil(remainingSec)}s`;
      }
    }

    update();
    timerInterval = setInterval(update, 200);
  }

  function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
  }

  // ── Submit Answer ──

  async function submitAnswer() {
    if (selectedOptionIndex === null || isSubmitting) return;
    isSubmitting = true;
    stopTimer();

    const submitBtn = document.getElementById("submitAnswerBtn");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Validating...';
    }

    try {
      const result = await EklavyaXAPI.submitQuizAnswer({
        sessionId: currentSessionId,
        selectedOptionIndex: selectedOptionIndex,
      });

      handleServerFeedback(result);
    } catch (err) {
      showError(err.message || "Failed to submit answer.");
      isSubmitting = false;
    }
  }

  // ── Handle Server Feedback (No client guessing) ──

  function handleServerFeedback(result) {
    const buttons = document.querySelectorAll(".quiz-option-btn");
    buttons.forEach((btn, idx) => {
      btn.disabled = true;
      if (idx === result.correct_option_index) {
        btn.classList.add("correct");
      }
      if (idx === selectedOptionIndex && !result.is_correct) {
        btn.classList.add("incorrect");
      }
    });

    currentStreak = result.streak || 0;
    updateStreakDisplay();

    // Feedback banner
    const banner = document.getElementById("quizFeedbackBanner");
    if (banner) {
      banner.style.display = "flex";
      banner.className = `quiz-feedback-banner ${result.is_correct ? "correct" : "incorrect"}`;

      const optionLetters = ["A", "B", "C", "D"];
      const correctLetter = optionLetters[result.correct_option_index] || "";
      const correctText = result.correct_option_text || "";
      const explanation = result.explanation || "";

      let contentHtml = "";

      if (result.is_correct) {
        let statusSubtext = "";
        if (result.rejection_reason === "cooldown_violation") {
          statusSubtext = '<span style="color: #fcd34d;">Submitted too quickly (&lt; 2s cooldown) — no rewards credited.</span>';
        } else if (result.rejection_reason === "cap_exceeded") {
          statusSubtext = '<span style="color: #fcd34d;">Daily earn cap reached — 0 reward granted.</span>';
        } else {
          const coinDiff = result.coins_awarded !== result.preview_coins ? ` (Cap adjusted from ${result.preview_coins})` : "";
          statusSubtext = `
            <div class="quiz-feedback-reward">
              <span>+${result.coins_awarded} EduCoins${coinDiff}</span>
              <span>+${result.xp_awarded} XP</span>
            </div>
          `;
        }

        contentHtml = `
          <div class="quiz-feedback-content">
            <div class="quiz-feedback-status">
              <i class="fas fa-check-circle" style="color: #10b981; font-size: 1.3rem;"></i>
              <div>
                <strong style="color: #6ee7b7; font-size: 1.05rem;">Correct Answer! 🎉</strong>
                ${statusSubtext}
              </div>
            </div>
            ${explanation ? `
              <div class="quiz-explanation-box is-correct-exp">
                <div class="quiz-explanation-header">
                  <i class="fas fa-lightbulb" style="color: var(--accent-gold, #f4ae25);"></i>
                  <strong>Key Concept & Explanation:</strong>
                </div>
                <div class="quiz-explanation-text">
                  ${escapeHtml(explanation)}
                </div>
              </div>
            ` : ""}
          </div>
        `;
      } else {
        contentHtml = `
          <div class="quiz-feedback-content">
            <div class="quiz-feedback-status">
              <i class="fas fa-times-circle" style="color: #ef4444; font-size: 1.3rem;"></i>
              <div>
                <strong style="color: #fca5a5; font-size: 1.05rem;">Incorrect Answer</strong>
                <div class="quiz-correct-option-callout">
                  Correct Answer: <strong style="color: #6ee7b7;">Option ${correctLetter}${correctText ? ': ' + escapeHtml(correctText) : ''}</strong>
                </div>
              </div>
            </div>
            ${explanation ? `
              <div class="quiz-explanation-box">
                <div class="quiz-explanation-header">
                  <i class="fas fa-lightbulb" style="color: var(--accent-gold, #f4ae25);"></i>
                  <strong>Explanation & Solution:</strong>
                </div>
                <div class="quiz-explanation-text">
                  ${escapeHtml(explanation)}
                </div>
              </div>
            ` : ""}
          </div>
        `;
      }

      banner.innerHTML = contentHtml;
    }

    // EklavyaALERT check for foundational prerequisite gaps
    if (!result.is_correct && currentQuestion && currentQuestion.topic) {
      checkPrerequisitesAndAlert(currentQuestion.topic);
    }

    // Toggle button to Next Question
    const submitBtn = document.getElementById("submitAnswerBtn");
    const nextBtn = document.getElementById("nextQuestionBtn");
    if (submitBtn) submitBtn.style.display = "none";
    if (nextBtn) {
      nextBtn.style.display = "inline-flex";
      if (currentQuestionIndex + 1 >= totalQuestions) {
        nextBtn.innerHTML = '<i class="fas fa-flag-checkered"></i> View Summary';
      } else {
        nextBtn.innerHTML = '<i class="fas fa-arrow-right"></i> Next Question';
      }
    }
  }

  // ── Next Question / Finish ──

  async function nextQuestion() {
    const nextIdx = currentQuestionIndex + 1;
    if (nextIdx >= totalQuestions) {
      await loadSummary();
      return;
    }

    showLoading();
    try {
      const resp = await EklavyaXAPI.getNextQuizQuestion(currentRunId, nextIdx);
      if (resp.finished || !resp.question) {
        await loadSummary();
      } else {
        renderQuestion(resp.question);
      }
    } catch (err) {
      showError(err.message || "Failed to load next question.");
    }
  }

  // ── Summary Screen ──

  async function loadSummary() {
    showLoading();
    stopTimer();

    try {
      const summary = await EklavyaXAPI.getQuizSummary(currentRunId);
      renderSummary(summary);
    } catch (err) {
      showError(err.message || "Failed to load quiz summary.");
    }
  }

  function renderSummary(summary) {
    const card = document.getElementById("quizActiveCard");
    const summaryCard = document.getElementById("quizSummaryCard");
    const hud = document.getElementById("quizHud");
    const timerContainer = document.getElementById("quizTimerContainer");

    if (card) card.style.display = "none";
    if (hud) hud.style.display = "none";
    if (timerContainer) timerContainer.style.display = "none";
    if (summaryCard) summaryCard.style.display = "block";

    document.getElementById("sumAccuracy").textContent = `${summary.accuracy_pct}%`;
    document.getElementById("sumCoins").textContent = `+${summary.total_coins}`;
    document.getElementById("sumXp").textContent = `+${summary.total_xp}`;

    // Transparency notices
    const noticeBox = document.getElementById("quizTransparencyBox");
    const noticeList = document.getElementById("quizTransparencyList");
    if (noticeBox && noticeList) {
      if (summary.transparency_notices && summary.transparency_notices.length > 0) {
        noticeBox.style.display = "block";
        noticeList.innerHTML = summary.transparency_notices
          .map((n) => `<li>${escapeHtml(n)}</li>`)
          .join("");
      } else {
        noticeBox.style.display = "none";
      }
    }
  }

  // ── Helpers ──

  function updateStreakDisplay() {
    const badge = document.getElementById("quizStreakBadge");
    const countEl = document.getElementById("quizStreakCount");
    if (countEl) countEl.textContent = `${currentStreak}x`;
    if (badge) {
      if (currentStreak > 1) {
        badge.classList.add("active-streak");
      } else {
        badge.classList.remove("active-streak");
      }
    }
  }

  function showLoading() {
    const l = document.getElementById("quizLoading");
    const c = document.getElementById("quizActiveCard");
    if (l) l.style.display = "block";
    if (c) c.style.display = "none";
  }

  function showCard() {
    const l = document.getElementById("quizLoading");
    const c = document.getElementById("quizActiveCard");
    const s = document.getElementById("quizSummaryCard");
    const h = document.getElementById("quizHud");
    const t = document.getElementById("quizTimerContainer");
    if (l) l.style.display = "none";
    if (c) c.style.display = "block";
    if (s) s.style.display = "none";
    if (h) h.style.display = "flex";
    if (t) t.style.display = "block";
  }

  function showError(msg) {
    const l = document.getElementById("quizLoading");
    if (l) {
      l.innerHTML = `
        <div style="color:#ef4444; padding:20px; text-align:center;">
          <i class="fas fa-exclamation-triangle" style="font-size:2rem; margin-bottom:10px;"></i>
          <p>${escapeHtml(msg)}</p>
          <button class="quiz-btn quiz-btn-secondary" onclick="window.location.reload()" style="margin-top:14px;">Retry</button>
        </div>
      `;
      l.style.display = "block";
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function downloadQuizPdf() {
    if (!currentRunId) {
      alert("No quiz session found to download.");
      return;
    }
    const token = localStorage.getItem("EklavyaX_token");
    window.open(`/quiz/${currentRunId}/download-pdf${token ? '?token=' + token : ''}`, '_blank');
  }

  function viewQuizPdf() {
    if (!currentRunId) {
      alert("No quiz session found to view.");
      return;
    }
    const token = localStorage.getItem("EklavyaX_token");
    window.open(`/quiz/${currentRunId}/download-pdf?view=true${token ? '&token=' + token : ''}`, '_blank');
  }

  async function checkPrerequisitesAndAlert(topic) {
    try {
      const alertEl = document.getElementById("eklavyaAlertBanner");
      const alertText = document.getElementById("eklavyaAlertText");
      if (!alertEl || !alertText) return;

      const prereqData = await EklavyaXAPI.getPrerequisites(topic);
      if (prereqData && prereqData.prerequisites && prereqData.prerequisites.length > 0) {
        alertText.innerHTML = `This topic (<strong>${escapeHtml(topic)}</strong>) directly depends on foundational knowledge: <strong>${escapeHtml(prereqData.prerequisites.join(", "))}</strong>. ${escapeHtml(prereqData.confidence_boost)}`;
        alertEl.style.display = "block";
      }
    } catch (e) {
      console.warn("Prerequisite check skipped:", e);
    }
  }

  return {
    init,
    selectOption,
    submitAnswer,
    nextQuestion,
    downloadQuizPdf,
    viewQuizPdf,
    getCurrentRunId: () => currentRunId,
    getCurrentQuestion: () => currentQuestion,
  };
})();


// Explicitly bind to global window
if (typeof window !== "undefined") {
  window.EklavyaXQuiz = EklavyaXQuiz;
}

