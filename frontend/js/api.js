/**
 * js/api.js
 * ─────────
 * Shared helper for talking to the Synapse (FastAPI) backend and for
 * managing the logged-in session in localStorage. Loaded by every page
 * that needs auth or live data (login pages, dashboards).
 *
 * The backend serves this frontend itself (see backend/app/main.py), so
 * API_BASE is left empty — requests are same-origin, no CORS needed.
 **/
// In unified deployments (Render), API_BASE is empty for same-origin requests.
// In split deployments (Vercel frontend + Render backend), set window.EKLAVYAX_API_BASE or localStorage.
const API_BASE = window.EKLAVYAX_API_BASE || localStorage.getItem("eklavya_api_base") || "";

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
    return request("/bounties/");
  }

  // ── Synapse AI Tutor ─────────────────────────────────────────────────────

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

  // ── Peer Challenges ──────────────────────────────────────────────────────

  function listChallenges(statusFilter) {
    const qs = statusFilter ? `?status_filter=${statusFilter}` : "";
    return request(`/challenges${qs}`);
  }

  function createChallenge({ opponentId, topic, wagerCoins = 0 }) {
    return request("/challenges", {
      method: "POST",
      body: { opponent_id: opponentId, topic, wager_coins: wagerCoins },
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
    listChallenges,
    createChallenge,
    levelFromXp,
    displayName,
    getAvatarUrl,
    applyUserAvatar,
  };
})();

