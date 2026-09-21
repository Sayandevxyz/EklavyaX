/**
 * js/api.js
 * ─────────
 * Shared helper for talking to the GRAVITY (FastAPI) backend and for
 * managing the logged-in session in localStorage. Loaded by every page
 * that needs auth or live data (login pages, dashboards).
 *
 * The backend serves this frontend itself (see backend/app/main.py), so
 * API_BASE is left empty — requests are same-origin, no CORS needed.
 **/
// In unified deployments (Render), API_BASE is empty for same-origin requests.
// In split deployments (Vercel frontend + Render backend), set window.EKLAVYAX_API_BASE or localStorage.
const API_BASE =
  window.EKLAVYAX_API_BASE ||
  localStorage.getItem("eklavya_api_base") ||
  (window.location.hostname.includes("vercel.app")
    ? "https://eklavyax.onrender.com"
    : (window.location.port && window.location.port !== "8000" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
      ? `http://${window.location.hostname}:8000`
      : ""));


const EklavyaXAPI = (() => {
  const TOKEN_KEY = "EklavyaX_token";
  const USER_KEY = "EklavyaX_user";

  // ── Session storage ──────────────────────────────────────────────────────

  function saveSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function isLoggedIn() {
    return !!getToken();
  }

  /**
   * Guard a dashboard page: redirect to the right login screen if the user
   * isn't authenticated, or isn't the expected role.
   * @param {"student"|"teacher"} expectedRole
   * @param {string} loginUrl relative path to that role's login page
   */
  function requireAuth(expectedRole, loginUrl) {
    const user = getUser();
    if (!isLoggedIn() || !user || user.role !== expectedRole) {
      window.location.href = loginUrl;
      return null;
    }
    return user;
  }

  function logout(redirectUrl) {
    clearSession();
    window.location.href = redirectUrl || "../index.html";
  }

  // ── Core request wrapper ─────────────────────────────────────────────────

  async function request(path, { method = "GET", body, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth) {
      const token = getToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }

    let res;
    try {
      res = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (networkErr) {
      throw new Error(
        "Couldn't reach the EklavyaX server. Make sure the backend is running (uvicorn app.main:app)."
      );
    }

    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      /* no JSON body (e.g. 204) */
    }

    if (!res.ok) {
      const detail =
        (data && (data.detail || data.message)) || `Request failed (${res.status})`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }

    return data;
  }

  // ── Auth endpoints ───────────────────────────────────────────────────────

  function register({ username, email, password, role, gender, avatar_url }) {
    return request("/auth/register", {
      method: "POST",
      auth: false,
      body: { username, email, password, role, gender, avatar_url },
    });
  }

  function login({ username, password }) {
    return request("/auth/login", {
      method: "POST",
      auth: false,
      body: { username, password },
    });
  }

  function me() {
    return request("/auth/me");
  }

  function updateProfile(userData) {
    return request("/auth/me", {
      method: "PUT",
      body: userData,
    });
  }

  function changePassword({ current_password, new_password }) {
    return request("/auth/change-password", {
      method: "POST",
      body: { current_password, new_password },
    });
  }

  function myStreak() {
    return request("/auth/me/streak");
  }

  function recordActivity() {
    return request("/auth/me/activity", { method: "POST" });
  }

  // ── Economy endpoints ────────────────────────────────────────────────────

  function wallet() {
    return request("/economy/wallet");
  }

  function classLeaderboard() {
    return request("/leaderboard/class");
  }

  function factionLeaderboard() {
    return request("/leaderboard/faction");
  }

  // ── Bounty board ─────────────────────────────────────────────────────────

  function listBounties() {
    return request("/bounties");

  }

  // ── GRAVITY AI Tutor ─────────────────────────────────────────────────────

  /**
   * Ask the AI tutor to explain highlighted text.
   * Costs AI_EXPLAIN_COST EduCoins (default: 10).
   * @param {string} highlightedText  The text to explain
   * @param {string} [targetLanguage] Optional language (e.g. "Hindi")
   */
  function tutorExplain(highlightedText, targetLanguage = "English") {
    return request("/tutor/explain", {
      method: "POST",
      body: { highlighted_text: highlightedText, target_language: targetLanguage },
    });
  }

  /**
   * Submit answer feedback after an AI explanation.
   * Correct answers earn a partial coin refund.
   * @param {number} explanationLogId  ID returned by tutorExplain()
   * @param {boolean} correct          Whether the student answered correctly
   */
  function tutorFeedback(explanationLogId, correct) {
    return request("/tutor/answer-feedback", {
      method: "POST",
      body: { explanation_log_id: explanationLogId, correct },
    });
  }

  function tutorHistory(skip = 0, limit = 20) {
    return request(`/tutor/history?skip=${skip}&limit=${limit}`);
  }

  function tutorClearHistory() {
    return request("/tutor/history", { method: "DELETE" });
  }

  /**
   * Transcribe recorded audio with Groq Cloud Whisper API.
   * @param {Blob} audioBlob
   * @param {string} [language]
   */
  function tutorTranscribe(audioBlob, language = "English") {
    const formData = new FormData();
    formData.append("file", audioBlob, "recording.webm");
    if (language) formData.append("language", language);

    const token = getToken();
    return fetch(`${BASE_URL}/tutor/transcribe`, {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Audio transcription failed");
      }
      return res.json();
    });
  }

  // ── Peer Challenges ──────────────────────────────────────────────────────

  function listChallenges(statusFilter = null) {
    const qs = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
    return request(`/challenges${qs}`);
  }

  function createChallenge({ opponent_id, subject, wager_coins }) {
    return request("/challenges", {
      method: "POST",
      body: { opponent_id, subject, wager_coins },
    });
  }

  function acceptChallenge(challengeId) {
    return request(`/challenges/${challengeId}/accept`, {
      method: "POST",
    });
  }

  function submitChallengeResult(challengeId, result) {
    return request(`/challenges/${challengeId}/submit`, {
      method: "POST",
      body: result,
    });
  }

  // ── Quiz System ──────────────────────────────────────────────────────────

  function startQuiz(opts = {}) {
    return request("/quiz/start", {
      method: "POST",
      body: {
        topic: opts.topic || null,
        num_questions: opts.numQuestions || null,
      },
    });
  }

  function submitQuizAnswer({ sessionId, selectedOptionIndex }) {
    return request("/quiz/submit", {
      method: "POST",
      body: {
        session_id: sessionId,
        selected_option_index: selectedOptionIndex,
      },
    });
  }

  function getNextQuizQuestion(quizRunId, questionIndex) {
    return request(`/quiz/${quizRunId}/next/${questionIndex}`);
  }

  function getQuizSummary(quizRunId) {
    return request(`/quiz/summary/${quizRunId}`);
  }

  function generateAIQuiz({ topic = "Physics", numQuestions = 5 } = {}) {
    return request(`/quiz/generate-ai?topic=${encodeURIComponent(topic)}&num_questions=${numQuestions}`, {
      method: "POST",
    });
  }

  // ── Faction Wars Battle Engine ───────────────────────────────────────────

  function getActiveFactionBattle() {
    return request("/faction-wars/battle/active");
  }

  function getFactionBattleLeaderboard(battleId, factionId = null) {
    const qs = factionId ? `?faction_id=${factionId}` : "";
    return request(`/faction-wars/battle/${battleId}/leaderboard${qs}`);
  }

  function finalizeFactionBattle(battleId) {
    return request(`/faction-wars/battle/${battleId}/finalize`, {
      method: "POST",
    });
  }

  function listFactions() {
    return request("/faction-wars/factions");
  }

  function getBattleHistory() {
    return request("/faction-wars/history");
  }

  function startNewFactionBattle() {
    return request("/faction-wars/battle/start-new", {
      method: "POST",
    });
  }

  // ── Derived / display helpers ────────────────────────────────────────────

  /** Simple XP → level curve for the UI (100 XP per level). */
  function levelFromXp(xp) {
    return Math.max(1, Math.floor((xp || 0) / 100) + 1);
  }

  /** Turn "first.last" / "first_last" style usernames into a display name. */
  function displayName(user) {
    if (!user) return "";
    if (!user.username) return "";
    if (user.username.includes(" ")) return user.username;
    return user.username
      .split(/[._-]/)
      .filter(Boolean)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }

  /** Resolve the appropriate avatar URL for student/teacher boy/girl or custom uploaded avatar */
  function getAvatarUrl(user, relativePrefix) {
    const isSubfolder =
      window.location.pathname.includes("/student/") ||
      window.location.pathname.includes("/teacher/") ||
      window.location.pathname.includes("\\student\\") ||
      window.location.pathname.includes("\\teacher\\");
    const prefix = relativePrefix !== undefined ? relativePrefix : (isSubfolder ? ".." : ".");

    if (!user) {
      return `${prefix}/assets/img/student_boy.jpg`;
    }

    if (user.avatar_url) {
      if (user.avatar_url.startsWith("http://") || user.avatar_url.startsWith("https://") || user.avatar_url.startsWith("data:")) {
        return user.avatar_url;
      }
      const parts = user.avatar_url.replace(/\\/g, "/").split("/");
      const filename = parts.pop();
      if (filename && (filename.endsWith(".jpg") || filename.endsWith(".png") || filename.endsWith(".jpeg") || filename.endsWith(".svg"))) {
        return `${prefix}/assets/img/${filename}`;
      }
    }

    const isTeacher = user.role === "teacher";
    const isFemale = (user.gender === "female" || user.gender === "girl");

    if (isTeacher) {
      return `${prefix}/assets/img/${isFemale ? "teacher_female.jpg" : "teacher_male.jpg"}`;
    } else {
      return `${prefix}/assets/img/${isFemale ? "student_girl.jpg" : "student_boy.jpg"}`;
    }
  }

  /** Dynamically apply avatar to profile images on the page */
  function applyUserAvatar(user, context = document) {
    if (!user) return;
    const avatarUrl = getAvatarUrl(user);
    const imgs = context.querySelectorAll(
      ".profile img, .profile-section img, .profile-avatar img, img.profile-img, img[alt*='profile' i], #userAvatarImg, #welcomeAvatarImg, .user-avatar-img"
    );
    imgs.forEach((img) => {
      img.src = avatarUrl;
    });
  }

  // ── Extended Features API ───────────────────────────────────────────────
  const getLeaderboardGlobal = (period = "all_time", sortBy = "xp") =>
    request(`/api/leaderboard/global?period=${period}&sort_by=${sortBy}`);
  const getLeaderboardFactions = () => request("/api/leaderboard/factions");
  const getMyLeaderboardRank = () => request("/api/leaderboard/me");

  const getNotifications = () => request("/api/notifications");
  const markNotificationRead = (id) => request(`/api/notifications/${id}/read`, { method: "POST" });
  const markAllNotificationsRead = () => request("/api/notifications/read-all", { method: "POST" });
  const triggerNotificationReminders = () => request("/api/notifications/trigger-reminders", { method: "POST" });

  const getTeacherProfile = () => request("/auth/teacher-profile");
  const updateTeacherProfile = (data) =>
    request("/auth/teacher-profile", { method: "PUT", body: data });

  const getTeacherOverview = () => request("/api/analytics/overview");
  const getTeacherWeakTopics = () => request("/api/analytics/weak-topics");
  const getTeacherEngagement = () => request("/api/analytics/engagement");

  const getMyStudyGroups = () => request("/api/study-groups/my");
  const createStudyGroup = (name, description, subject) =>
    request("/api/study-groups/create", { method: "POST", body: { name, description, subject } });
  const joinStudyGroup = (join_code) =>
    request("/api/study-groups/join", { method: "POST", body: { join_code } });
  const getGroupNotes = (groupId) => request(`/api/study-groups/${groupId}/notes`);
  const addGroupNote = (groupId, title, content) =>
    request(`/api/study-groups/${groupId}/notes`, { method: "POST", body: { title, content } });

  const getAchievements = () => request("/api/achievements");
  const checkAchievements = () => request("/api/achievements/check", { method: "POST" });

  const getDueFlashcards = () => request("/api/flashcards/due");
  const reviewFlashcard = (card_id, rating) =>
    request("/api/flashcards/review", { method: "POST", body: { card_id, rating } });
  const syncQuizMistakes = () => request("/api/flashcards/sync-mistakes", { method: "POST" });

  const getChatThreads = (topic, status) => {
    let q = "";
    if (topic) q += `topic=${encodeURIComponent(topic)}&`;
    if (status) q += `status_filter=${encodeURIComponent(status)}&`;
    return request(`/api/chat-threads${q ? "?" + q : ""}`);
  };
  const createChatThread = (title, topic, initial_message) =>
    request("/api/chat-threads", { method: "POST", body: { title, topic, initial_message } });
  const getThreadDetails = (id) => request(`/api/chat-threads/${id}`);
  const sendThreadMessage = (id, message) =>
    request(`/api/chat-threads/${id}/messages`, { method: "POST", body: { message } });
  const updateThreadStatus = (id, status) =>
    request(`/api/chat-threads/${id}/status`, { method: "PATCH", body: { status } });

  const getMyReferralCode = () => request("/api/referrals/my-code");
  const applyReferralCode = (referral_code) =>
    request("/api/referrals/apply", { method: "POST", body: { referral_code } });

  const getStudyPlan = () => request("/api/study-planner/plan");
  const setupStudyPlan = (target_exam, target_date) =>
    request("/api/study-planner/setup", { method: "POST", body: { target_exam, target_date } });
  const toggleStudyPlanTask = (id) =>
    request(`/api/study-planner/tasks/${id}/toggle`, { method: "POST" });

  const submitReport = (target_type, target_id, reason, description) =>
    request("/api/reports", { method: "POST", body: { target_type, target_id, reason, description } });

  const getMyCertificates = () => request("/api/certificates/my");
  const claimCertificate = (course_name, score_percent) =>
    request("/api/certificates/claim", { method: "POST", body: { course_name, score_percent } });

  const createTeacherQuiz = (quizData) =>
    request("/quiz/custom/create", { method: "POST", body: quizData });
  const listTeacherQuizzes = () => request("/quiz/custom/list");
  const deleteTeacherQuiz = (id) => request(`/quiz/custom/${id}`, { method: "DELETE" });
  const getPublishedTeacherQuizzes = () => request("/quiz/teacher/published-list");
  const startTeacherQuiz = (quizId) => request(`/quiz/teacher/${quizId}/start`);
  const submitTeacherQuiz = (quizId, answers) =>
    request(`/quiz/teacher/${quizId}/submit`, { method: "POST", body: { answers } });

  // ── Pedagogical Mastery & Analytics Suite ──
  const getTeacherDoubtHeatmap = (subject) =>
    request(`/api/pedagogy/teacher/doubt-heatmap${subject ? `?subject=${encodeURIComponent(subject)}` : ""}`);
  const getPrerequisites = (topic) =>
    request(`/api/pedagogy/student/prerequisites/${encodeURIComponent(topic)}`);
  const getRevisionRadar = () => request("/api/pedagogy/student/revision-radar");
  const completeRevisionRadar = (schedule_id, checkpoint) =>
    request("/api/pedagogy/student/revision-radar/complete", { method: "POST", body: { schedule_id, checkpoint } });
  const getWeakAreas = () => request("/api/pedagogy/student/weak-areas");
  const retryWeakArea = (flag_id, answers) =>
    request(`/api/pedagogy/student/weak-areas/${flag_id}/retry`, { method: "POST", body: { answers } });
  const getPYQs = (exam_type, year, subject) => {
    const params = new URLSearchParams();
    if (exam_type) params.append("exam_type", exam_type);
    if (year) params.append("year", year);
    if (subject) params.append("subject", subject);
    return request(`/api/pedagogy/pyqs?${params.toString()}`);
  };
  const submitPYQ = (payload) =>
    request("/api/pedagogy/pyqs/submit", { method: "POST", body: payload });
  const getSilentStruggles = () => request("/api/pedagogy/student/silent-struggles");
  const getBookmarks = () => request("/api/pedagogy/bookmarks");
  const toggleBookmark = (payload) =>
    request("/api/pedagogy/bookmarks/toggle", { method: "POST", body: payload });
  const getMindMap = (subject) =>
    request(`/api/pedagogy/mindmaps/${encodeURIComponent(subject)}`);

  return {
    saveSession,
    getToken,
    getUser,
    clearSession,
    isLoggedIn,
    requireAuth,
    logout,
    register,
    login,
    me,
    updateProfile,
    changePassword,
    myStreak,
    recordActivity,
    wallet,
    classLeaderboard,
    factionLeaderboard,
    listBounties,
    tutorExplain,
    tutorFeedback,
    tutorHistory,
    tutorClearHistory,
    tutorTranscribe,
    listChallenges,
    createChallenge,
    acceptChallenge,
    submitChallengeResult,
    startQuiz,
    submitQuizAnswer,
    getNextQuizQuestion,
    getQuizSummary,
    generateAIQuiz,
    getActiveFactionBattle,
    getFactionBattleLeaderboard,
    finalizeFactionBattle,
    listFactions,
    getBattleHistory,
    startNewFactionBattle,
    levelFromXp,
    displayName,
    getAvatarUrl,
    applyUserAvatar,
    // Extensions
    getLeaderboardGlobal,
    getLeaderboardFactions,
    getMyLeaderboardRank,
    getNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    triggerNotificationReminders,
    getTeacherProfile,
    updateTeacherProfile,
    getTeacherOverview,
    getTeacherWeakTopics,
    getTeacherEngagement,
    getMyStudyGroups,
    createStudyGroup,
    joinStudyGroup,
    getGroupNotes,
    addGroupNote,
    getAchievements,
    checkAchievements,
    getDueFlashcards,
    reviewFlashcard,
    syncQuizMistakes,
    getChatThreads,
    createChatThread,
    getThreadDetails,
    sendThreadMessage,
    updateThreadStatus,
    getMyReferralCode,
    applyReferralCode,
    getStudyPlan,
    setupStudyPlan,
    toggleStudyPlanTask,
    submitReport,
    getMyCertificates,
    claimCertificate,
    createTeacherQuiz,
    listTeacherQuizzes,
    deleteTeacherQuiz,
    getPublishedTeacherQuizzes,
    startTeacherQuiz,
    submitTeacherQuiz,
    // Pedagogy & Analytics Suite
    getTeacherDoubtHeatmap,
    getPrerequisites,
    getRevisionRadar,
    completeRevisionRadar,
    getWeakAreas,
    retryWeakArea,
    getPYQs,
    submitPYQ,
    getSilentStruggles,
    getBookmarks,
    toggleBookmark,
    getMindMap,
  };
})();


// Explicitly bind to global window
if (typeof window !== "undefined") {
  window.EklavyaXAPI = EklavyaXAPI;
}


