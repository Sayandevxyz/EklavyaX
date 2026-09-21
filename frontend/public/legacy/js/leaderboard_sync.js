/**
 * js/leaderboard_sync.js
 * ──────────────────────
 * Real-Time Synchronization & Leaderboard Engine for EklavyaX.
 *
 * Ensures:
 * 1. Students with MORE COINS & HIGHER PERFORMANCE rank at the top of the leaderboard.
 * 2. Real-time broadcast and sync across all tabs (BroadcastChannel + storage events).
 * 3. Dynamic rendering for Student Progress Hub, Teacher Dashboard, and Student Leaderboards.
 */

(function (window) {
  const STORAGE_KEY = "eklavyax_students_realtime_db_v2";
  const CHANNEL_NAME = "eklavyax_realtime_leaderboard_sync";

  function getEducoinBadgeTier(coins) {
    if (coins >= 750) {
      return {
        badge_tier: "Heroic",
        badge_icon: "👑",
        badge_color: "#f43f5e",
        badge_bg: "rgba(244, 63, 94, 0.2)",
        tier_score: 4
      };
    } else if (coins >= 500) {
      return {
        badge_tier: "Diamond",
        badge_icon: "💎",
        badge_color: "#38bdf8",
        badge_bg: "rgba(56, 189, 248, 0.2)",
        tier_score: 3
      };
    } else if (coins >= 200) {
      return {
        badge_tier: "Gold",
        badge_icon: "🥇",
        badge_color: "#f59e0b",
        badge_bg: "rgba(245, 158, 11, 0.2)",
        tier_score: 2
      };
    } else if (coins >= 100) {
      return {
        badge_tier: "Silver",
        badge_icon: "🥈",
        badge_color: "#94a3b8",
        badge_bg: "rgba(148, 163, 184, 0.2)",
        tier_score: 1
      };
    } else {
      return {
        badge_tier: "Bronze",
        badge_icon: "🥉",
        badge_color: "#cd7f32",
        badge_bg: "rgba(205, 127, 50, 0.2)",
        tier_score: 0
      };
    }
  }

  function getActiveStudentName() {
    try {
      if (typeof window !== "undefined" && window.EklavyaXAPI && window.EklavyaXAPI.getUser) {
        const u = window.EklavyaXAPI.getUser();
        if (u) {
          const dn = window.EklavyaXAPI.displayName(u);
          if (dn) return dn;
          if (u.full_name) return u.full_name;
          if (u.name) return u.name;
          if (u.username) return u.username;
        }
      }
      const raw = typeof localStorage !== "undefined" ? localStorage.getItem("EklavyaX_user") : null;
      if (raw) {
        const u = JSON.parse(raw);
        if (u.full_name) return u.full_name;
        if (u.name) return u.name;
        if (u.username) {
          if (u.username.includes(" ")) return u.username;
          return u.username.split(/[._-]/).filter(Boolean).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
        }
      }
    } catch (_) {}
    return "Sayan Mondal";
  }

  const DEFAULT_STUDENTS = {
    ishita: {
      id: "ishita",
      name: "Ishita Singh",
      roll: "EK-103",
      exam: "CBSE & JEE Advanced",
      house: "Jal House",
      faction_name: "Jal Faction",
      faction_color: "#38bdf8",
      avatar_url: "https://api.dicebear.com/7.x/bottts/svg?seed=Ishita",
      coins: 680,
      streak: 18,
      overall: 96,
      attendance: 98,
      assignments: 96,
      participation: 94,
      scores: [98, 92, 98, 95, 98, 95],
      attendanceTrend: [96, 98, 97, 98],
      note: "Top rank in class. Nominated for Inter-School Physics Olympiad."
    },
    sayan: {
      id: "sayan",
      name: getActiveStudentName(),
      roll: "EK-101",
      exam: "CBSE & JEE 2026",
      house: "Agni House",
      faction_name: "Agni Faction",
      faction_color: "#ef4444",
      avatar_url: "../assets/img/student_boy.jpg",
      coins: 620,
      streak: 15,
      overall: 94,
      attendance: 96,
      assignments: 92,
      participation: 90,
      scores: [95, 88, 94, 90, 98, 92],
      attendanceTrend: [94, 96, 95, 96],
      note: "Excellent conceptual grasp in Physics mechanics and coding labs. High consistency."
    },
    prachi: {
      id: "prachi",
      name: "Prachi Mondal",
      roll: "EK-104",
      exam: "JEE Main",
      house: "Prithvi House",
      faction_name: "Prithvi Faction",
      faction_color: "#10b981",
      avatar_url: "https://api.dicebear.com/7.x/bottts/svg?seed=Prachi",
      coins: 540,
      streak: 12,
      overall: 89,
      attendance: 94,
      assignments: 88,
      participation: 85,
      scores: [88, 85, 90, 84, 92, 88],
      attendanceTrend: [90, 92, 94, 94],
      note: "Very regular in doubt sessions and daily quizzes. Star performer."
    },
    anchal: {
      id: "anchal",
      name: "Anchal Vishwakarma",
      roll: "EK-106",
      exam: "CBSE Boards",
      house: "Vayu House",
      faction_name: "Vayu Faction",
      faction_color: "#a855f7",
      avatar_url: "https://api.dicebear.com/7.x/bottts/svg?seed=Anchal",
      coins: 490,
      streak: 10,
      overall: 87,
      attendance: 92,
      assignments: 85,
      participation: 84,
      scores: [85, 82, 88, 84, 90, 86],
      attendanceTrend: [90, 91, 93, 92],
      note: "Strong performance in laboratory simulations and weekly assignments."
    },
    aditya: {
      id: "aditya",
      name: "Aditya Mishra",
      roll: "EK-102",
      exam: "NEET / Medical",
      house: "Vayu House",
      faction_name: "Vayu Faction",
      faction_color: "#a855f7",
      avatar_url: "https://api.dicebear.com/7.x/bottts/svg?seed=Aditya",
      coins: 310,
      streak: 5,
      overall: 76,
      attendance: 80,
      assignments: 74,
      participation: 72,
      scores: [72, 70, 75, 85, 82, 78],
      attendanceTrend: [82, 80, 78, 80],
      note: "Good biological sciences grasp. Advised extra practice in numerical calculations."
    },
    harsh: {
      id: "harsh",
      name: "Harsh Yadav",
      roll: "EK-107",
      exam: "CBSE & NDA",
      house: "Agni House",
      faction_name: "Agni Faction",
      faction_color: "#ef4444",
      avatar_url: "https://api.dicebear.com/7.x/bottts/svg?seed=Harsh",
      coins: 210,
      streak: 3,
      overall: 68,
      attendance: 75,
      assignments: 65,
      participation: 64,
      scores: [68, 62, 70, 65, 72, 69],
      attendanceTrend: [74, 76, 73, 75],
      note: "Active participant in faction events. Recommended regular daily quiz completion."
    },
    rahul: {
      id: "rahul",
      name: "Rahul Verma",
      roll: "EK-105",
      exam: "CBSE Boards",
      house: "Agni House",
      faction_name: "Agni Faction",
      faction_color: "#ef4444",
      avatar_url: "https://api.dicebear.com/7.x/bottts/svg?seed=Rahul",
      coins: 95,
      streak: 1,
      overall: 54,
      attendance: 64,
      assignments: 45,
      participation: 40,
      scores: [48, 52, 50, 60, 58, 62],
      attendanceTrend: [70, 66, 62, 64],
      note: "Attendance has fallen below 75% threshold. Guardian alert dispatched."
    }
  };

  const listeners = new Set();
  let channel = null;

  try {
    if (typeof BroadcastChannel !== "undefined") {
      channel = new BroadcastChannel(CHANNEL_NAME);
      channel.onmessage = () => {
        notifyListeners();
      };
    }
  } catch (_) {}

  if (typeof window !== "undefined" && window.addEventListener) {
    window.addEventListener("storage", (e) => {
      if (e.key === STORAGE_KEY) {
        notifyListeners();
      }
    });
  }

  function getDatabase() {
    const studentName = getActiveStudentName();
    const defaults = { ...DEFAULT_STUDENTS };
    if (defaults.sayan) {
      defaults.sayan = { ...defaults.sayan, name: studentName };
    }
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        const merged = { ...defaults, ...parsed };
        if (merged.sayan) {
          if (!merged.sayan.name || merged.sayan.name === "RISHABH RAJ" || merged.sayan.name === "Student") {
            merged.sayan.name = studentName;
          }
        }
        return merged;
      }
    } catch (_) {}
    return defaults;
  }

  function saveDatabase(db) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
      if (channel) {
        channel.postMessage({ type: "SYNC", timestamp: Date.now() });
      }
    } catch (_) {}
    notifyListeners();
  }

  function notifyListeners() {
    const students = getSortedStudents();
    listeners.forEach((fn) => {
      try {
        fn(students);
      } catch (err) {
        console.error("LeaderboardSync listener error:", err);
      }
    });
  }

  /**
   * Sort logic: Those who have MORE COINS and HIGHER PERFORMANCE rank at the top!
   */
  function getSortedStudents(sortBy = "coins") {
    const db = getDatabase();
    const list = Object.values(db);

    list.sort((a, b) => {
      if (sortBy === "xp") {
        const xpA = a.xp || ((a.overall || 0) * 15 + (a.coins || 0) * 2);
        const xpB = b.xp || ((b.overall || 0) * 15 + (b.coins || 0) * 2);
        if (xpB !== xpA) return xpB - xpA;
        return (b.coins || 0) - (a.coins || 0);
      } else if (sortBy === "streak") {
        if ((b.streak || 0) !== (a.streak || 0)) {
          return (b.streak || 0) - (a.streak || 0);
        }
        return (b.coins || 0) - (a.coins || 0);
      } else {
        // 1. Highest EduCoins first!
        if ((b.coins || 0) !== (a.coins || 0)) {
          return (b.coins || 0) - (a.coins || 0);
        }
        // 2. Highest Performance score % first!
        if ((b.overall || 0) !== (a.overall || 0)) {
          return (b.overall || 0) - (a.overall || 0);
        }
        // 3. Highest Streak first
        return (b.streak || 0) - (a.streak || 0);
      }
    });

    return list.map((st, idx) => {
      const rank = idx + 1;
      let risk = "safe";
      let riskLabel = "Healthy Progress";
      if (st.overall >= 90) {
        risk = "safe";
        riskLabel = "Top Performer";
      } else if (st.overall >= 75) {
        risk = "safe";
        riskLabel = "Good Standing";
      } else if (st.overall >= 60) {
        risk = "med";
        riskLabel = "Moderate Risk";
      } else {
        risk = "high";
        riskLabel = "Critical Risk (<60%)";
      }

      const bTier = getEducoinBadgeTier(st.coins || 0);
      const computedXp = st.xp || ((st.overall || 0) * 15 + (st.coins || 0) * 2);

      return {
        ...st,
        user_id: st.id,
        username: st.name,
        rank,
        risk,
        riskLabel,
        xp: computedXp,
        ...bTier
      };
    });
  }

  function getStudentById(id) {
    const sorted = getSortedStudents();
    return sorted.find((s) => s.id === id) || sorted[0];
  }

  /**
   * Award coins in real-time and boost rank!
   */
  function awardCoins(studentId, amount, reason) {
    const db = getDatabase();
    const targetKey = db[studentId] ? studentId : "sayan";
    const st = db[targetKey];
    if (st) {
      st.coins = (st.coins || 0) + Number(amount);
      if (st.coins < 0) st.coins = 0;
      saveDatabase(db);
      return st;
    }
    return null;
  }

  /**
   * Update student performance (e.g. after quiz or assessment)
   */
  function updatePerformance(studentId, { scorePct, coinsEarned, streakDelta = 0 }) {
    const db = getDatabase();
    const targetKey = db[studentId] ? studentId : "sayan";
    const st = db[targetKey];
    if (st) {
      if (scorePct !== undefined) {
        st.overall = Math.round((st.overall * 0.7) + (scorePct * 0.3));
        if (!st.scores) st.scores = [90, 85, 90, 88, 92, 90];
        st.scores.unshift(scorePct);
        st.scores = st.scores.slice(0, 6);
      }
      if (coinsEarned) {
        st.coins = (st.coins || 0) + Number(coinsEarned);
      }
      if (streakDelta) {
        st.streak = Math.max(1, (st.streak || 1) + streakDelta);
      }
      saveDatabase(db);
      return st;
    }
    return null;
  }

  /**
   * Render Leaderboard Widget (used by Teacher & Student Dashboards)
   */
  function renderLeaderboardWidget(containerId, maxItems = 5) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const students = getSortedStudents("coins").slice(0, maxItems);

    container.innerHTML = students.map((st) => {
      let medalHtml = "";
      if (st.rank === 1) {
        medalHtml = '<div class="icon-wrapper medal gold" aria-hidden="true"><i class="fas fa-medal"></i></div>';
      } else if (st.rank === 2) {
        medalHtml = '<div class="icon-wrapper medal silver" aria-hidden="true"><i class="fas fa-medal"></i></div>';
      } else if (st.rank === 3) {
        medalHtml = '<div class="icon-wrapper medal bronze" aria-hidden="true"><i class="fas fa-medal"></i></div>';
      } else {
        medalHtml = '<div class="icon-wrapper" aria-hidden="true"><i class="fas fa-user"></i></div>';
      }

      const isMe = st.id === "sayan";

      return `
        <div class="leaderboard-item ${isMe ? 'is-me' : ''}" tabindex="0" title="Rank #${st.rank}: ${st.coins} EduCoins | ${st.overall}% Performance">
          ${medalHtml}
          <div class="name">
            <strong>${st.name} ${isMe ? '<span style="color:#10b981; font-size:11px;">(You)</span>' : ''}</strong>
            <span style="font-size: 11px; color: #94a3b8; margin-left: 6px;">(${st.overall}% Avg)</span>
          </div>
          <div class="points" style="font-weight:700; color: #f4ae25; display:flex; align-items:center; gap:5px;">
            <span>🪙 ${st.coins.toLocaleString()}</span>
            <span aria-label="Starred user" role="img" class="star" style="margin-left: 2px;">
              <i class="${st.rank <= 3 ? 'fas' : 'far'} fa-star" style="color: ${st.rank <= 3 ? '#f4ae25' : '#94a3b8'};"></i>
            </span>
          </div>
        </div>
      `;
    }).join("");
  }

  /**
   * Directly update a student's attributes (coins, eduCoins, overallScore, etc.)
   */
  function updateStudent(studentId, updates) {
    const db = getDatabase();
    const targetKey = db[studentId] ? studentId : "sayan";
    const st = db[targetKey];
    if (st && updates) {
      if (updates.coins !== undefined) st.coins = Number(updates.coins);
      if (updates.eduCoins !== undefined) st.coins = Number(updates.eduCoins);
      if (updates.overallScore !== undefined) st.overall = Number(updates.overallScore);
      if (updates.overall !== undefined) st.overall = Number(updates.overall);
      if (updates.streak !== undefined) st.streak = Number(updates.streak);
      if (updates.name) st.name = updates.name;
      saveDatabase(db);
      return st;
    }
    return null;
  }

  // Export API globally
  window.LeaderboardSync = {
    getDatabase,
    saveDatabase,
    getSortedStudents,
    getStudentById,
    getEducoinBadgeTier,
    awardCoins,
    updatePerformance,
    updateStudent,
    renderLeaderboardWidget,
    onSync(callback) {
      listeners.add(callback);
      return () => listeners.delete(callback);
    },
    subscribe(callback) {
      listeners.add(callback);
      return () => listeners.delete(callback);
    }
  };
})(window);
