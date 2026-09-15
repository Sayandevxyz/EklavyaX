// ── Auth guard + live data from the Synapse backend ──────────────────────
(async function initStudentDashboard() {
  const user = EklavyaXAPI.requireAuth("student", "student_login.html");
  if (!user) return; // already redirecting to login

  const firstName = EklavyaXAPI.displayName(user).split(" ")[0] || user.username;

  const nameEl = document.getElementById("profileName");
  const welcomeEl = document.getElementById("welcomeName");
  if (nameEl) nameEl.textContent = EklavyaXAPI.displayName(user);
  if (welcomeEl) welcomeEl.textContent = firstName;
  if (EklavyaXAPI.applyUserAvatar) EklavyaXAPI.applyUserAvatar(user);

  if (EklavyaXAPI.isLoggedIn() && EklavyaXAPI.me) {
    EklavyaXAPI.me().then((freshUser) => {
      if (freshUser) {
        EklavyaXAPI.saveSession(EklavyaXAPI.getToken(), freshUser);
        if (nameEl) nameEl.textContent = EklavyaXAPI.displayName(freshUser);
        if (welcomeEl) welcomeEl.textContent = EklavyaXAPI.displayName(freshUser).split(" ")[0] || freshUser.username;
        if (EklavyaXAPI.applyUserAvatar) EklavyaXAPI.applyUserAvatar(freshUser);
      }
    }).catch(() => {});
  }

  const logoutEl = document.getElementById("profileAction");
  if (logoutEl) {
    logoutEl.textContent = "Log out";
    logoutEl.style.cursor = "pointer";
    logoutEl.addEventListener("click", (e) => {
      e.stopPropagation();
      EklavyaXAPI.logout("student_login.html");
    });
  }

  // ── Live wallet / streak ───────────────────────────────────────────────
  try {
    const [wallet, streak] = await Promise.all([
      EklavyaXAPI.wallet(),
      EklavyaXAPI.myStreak(),
    ]);

    const pointsEl = document.getElementById("statPoints");
    const levelEl = document.getElementById("statLevel");
    const streakEl = document.getElementById("statStreak");
    const streakBadge = document.getElementById("streakBadge");

    if (pointsEl) pointsEl.textContent = wallet.balance.toLocaleString();
    if (levelEl) levelEl.textContent = `Level ${EklavyaXAPI.levelFromXp(wallet.xp)
      }`;
    if (streakEl) streakEl.textContent = `${streak.current_streak} Day${streak.current_streak === 1 ? "" : "s"} `;
    if (streakBadge) {
      streakBadge.textContent = streak.current_streak > 0
        ? `🔥 ${streak.current_streak} -Day Streak`
        : "🔥 Start your streak today";
    }

    // ── XP-based progress chart ──────────────────────────────────────────
    const level = EklavyaXAPI.levelFromXp(wallet.xp);
    const xpIntoLevel = (wallet.xp || 0) % 100;
    const progressPct = xpIntoLevel; // 0-99 within current level
    renderProgressChart(progressPct, level);

  } catch (err) {
    console.warn("EklavyaX: couldn't load live wallet/streak data —", err.message);
    renderProgressChart(0, 1);
  }

  // ── Live class leaderboard ─────────────────────────────────────────────
  try {
    const lb = await EklavyaXAPI.classLeaderboard();
    renderLeaderboard(lb.entries, user.id);
  } catch (err) {
    console.warn("EklavyaX: couldn't load leaderboard —", err.message);
  }

  // ── Live bounty board ─────────────────────────────────────────────────
  try {
    const bounties = await EklavyaXAPI.listBounties();
    renderBounties(bounties);
  } catch (err) {
    console.warn("EklavyaX: couldn't load bounties —", err.message);
  }

  // Record today's activity (updates streak)
  EklavyaXAPI.recordActivity().catch(() => { });
})();

// ── XP progress doughnut chart ──────────────────────────────────────────────
function renderProgressChart(pct, level) {
  const canvas = document.getElementById("progressChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  new Chart(ctx, {
    type: "doughnut",
    data: {
      datasets: [{
        data: [pct, 100 - pct],
        backgroundColor: ["#5A77DF", "#CCD4DE"],
        borderWidth: 0,
      }],
    },
    options: {
      cutout: "70%",
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      },
    },
    plugins: [{
      id: "textCenter",
      beforeDraw(chart) {
        const { width, height, ctx } = chart;
        ctx.restore();
        const fontSize = (height / 6).toFixed(2);
        ctx.font = `bold ${fontSize}px Arial`;
        ctx.textBaseline = "middle";
        ctx.fillStyle = "#333";
        const text = `${pct}% `;
        const textX = Math.round((width - ctx.measureText(text).width) / 2);
        ctx.fillText(text, textX, height / 2);
        // small label
        ctx.font = `${(height / 9).toFixed(2)}px Arial`;
        ctx.fillStyle = "#888";
        const sub = `Lvl ${level} `;
        const subX = Math.round((width - ctx.measureText(sub).width) / 2);
        ctx.fillText(sub, subX, height / 2 + parseInt(fontSize) + 2);
        ctx.save();
      },
    }],
  });
}

// ── Leaderboard renderer ───────────────────────────────────────────────────
function renderLeaderboard(entries, currentUserId) {
  const container = document.getElementById("leaderboardList");
  if (!container || !entries || entries.length === 0) return;

  const medals = ["🥇", "🥈", "🥉"];
  container.innerHTML = entries.slice(0, 5).map((e, i) => {
    const isMe = e.user_id === currentUserId;
    return `
    < div class="leaderboard-item${isMe ? " is - me" : ""}" tabindex = "0" >
        <span class="lb-rank">${medals[i] || `#${i + 1}`}</span>
        <span class="lb-name">${e.username}${isMe ? " (You)" : ""}</span>
        <span class="lb-pts">${e.xp} XP</span>
      </div > `;
  }).join("");
}

// ── Bounty board renderer ──────────────────────────────────────────────────
function renderBounties(bounties) {
  const container = document.getElementById("bountyList");
  if (!container) return;

  if (!bounties || bounties.length === 0) {
    container.innerHTML = `< p class="no-data" > No active bounties right now.Check back soon!</p > `;
    return;
  }

  container.innerHTML = bounties.slice(0, 4).map(b => {
    const deadline = new Date(b.deadline).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
    return `
    < div class="bounty-item" tabindex = "0" >
        <div class="bounty-title">${b.title}</div>
        <div class="bounty-meta">
          <span class="bounty-reward">🪙 ${b.reward_coins} coins</span>
          <span class="bounty-deadline">⏰ ${deadline}</span>
        </div>
        ${b.topic ? `<span class="bounty-topic">${b.topic}</span>` : ""}
      </div > `;
  }).join("");
}

// ── Toggle Section ─────────────────────────────────────────────────────────
function showSection(id, btn) {
  let sections = document.querySelectorAll('.lab-cards');
  sections.forEach(sec => sec.style.display = "none");
  document.getElementById(id).style.display = "grid";
  let buttons = document.querySelectorAll('.tabs button');
  buttons.forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

function openLab(url) {
  document.getElementById("labFrame").src = url;
  document.getElementById("labModal").style.display = "block";
}
function closeLab() {
  document.getElementById("labModal").style.display = "none";
  document.getElementById("labFrame").src = "";
}
window.onclick = function (event) {
  let modal = document.getElementById("labModal");
  if (event.target == modal) {
    closeLab();
  }
};
