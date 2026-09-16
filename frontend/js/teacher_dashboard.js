function toggleSidebar() {
  document.querySelector('.sidebar').classList.toggle('active');
}

// ── Auth guard + live profile data from the GRAVITY backend ────────────────
(async function initTeacherDashboard() {
  const user = EklavyaXAPI.requireAuth("teacher", "login.html");
  if (!user) return; // already redirecting to login

  const firstName = EklavyaXAPI.displayName(user).split(" ")[0] || user.username;

  const nameEl = document.getElementById("profileName");
  const welcomeEl = document.getElementById("welcomeName");
  if (nameEl) nameEl.textContent = EklavyaXAPI.displayName(user);
  if (welcomeEl) welcomeEl.textContent = `Mr./Ms. ${firstName}`;
  if (EklavyaXAPI.applyUserAvatar) EklavyaXAPI.applyUserAvatar(user);

  if (EklavyaXAPI.isLoggedIn() && EklavyaXAPI.me) {
    EklavyaXAPI.me().then((freshUser) => {
      if (freshUser) {
        EklavyaXAPI.saveSession(EklavyaXAPI.getToken(), freshUser);
        if (nameEl) nameEl.textContent = EklavyaXAPI.displayName(freshUser);
        if (welcomeEl) welcomeEl.textContent = `Mr./Ms. ${EklavyaXAPI.displayName(freshUser).split(" ")[0] || freshUser.username}`;
        if (EklavyaXAPI.applyUserAvatar) EklavyaXAPI.applyUserAvatar(freshUser);
      }
    }).catch(() => { });
  }

  const logoutEl = document.getElementById("profileAction");
  if (logoutEl) {
    logoutEl.textContent = "Log out";
    logoutEl.style.cursor = "pointer";
    logoutEl.addEventListener("click", (e) => {
      e.stopPropagation();
      EklavyaXAPI.logout("login.html");
    });
  }

  // ── Live real-time synced leaderboard ────────────────────────────────
  try {
    if (window.LeaderboardSync) {
      window.LeaderboardSync.renderLeaderboardWidget("teacherLeaderboardList", 5);
      window.LeaderboardSync.subscribe(() => {
        window.LeaderboardSync.renderLeaderboardWidget("teacherLeaderboardList", 5);
      });
    } else {
      const lb = await EklavyaXAPI.classLeaderboard();
      renderLeaderboard(lb.entries);
    }
  } catch (err) {
    console.warn("EklavyaX: couldn't load leaderboard —", err.message);
    if (window.LeaderboardSync) {
      window.LeaderboardSync.renderLeaderboardWidget("teacherLeaderboardList", 5);
    }
  }

  // ── Live bounties ─────────────────────────────────────────────────────
  try {
    const bounties = await EklavyaXAPI.listBounties();
    renderBountyCount(bounties);
  } catch (err) {
    console.warn("EklavyaX: couldn't load bounties —", err.message);
  }
})();

// ── Leaderboard renderer ───────────────────────────────────────────────────
function renderLeaderboard(entries) {
  const container = document.getElementById("teacherLeaderboardList") || document.querySelector(".leaderboard");
  if (!container || !entries || entries.length === 0) return;

  const medals = ["gold", "silver", "bronze"];

  const items = entries.slice(0, 5).map((e, i) => {
    const icon = i < 3
      ? `<div class="icon-wrapper medal ${medals[i]}" aria-hidden="true"><i class="fas fa-medal"></i></div>`
      : `<div class="icon-wrapper" aria-hidden="true"><i class="fas fa-user"></i></div>`;
    const starIcon = i < 3 ? `<i class="fas fa-star" style="color:#f4ae25;"></i>` : `<i class="far fa-star"></i>`;
    return `
      <div class="leaderboard-item" tabindex="0">
        ${icon}
        <div class="name">${e.username}</div>
        <div class="points" style="color:#f4ae25; font-weight:700;">🪙 ${e.coins || 0} • ${e.xp} XP <span class="star">${starIcon}</span></div>
      </div>`;
  }).join("");

  if (document.getElementById("teacherLeaderboardList")) {
    container.innerHTML = items;
  } else {
    const heading = container.querySelector("h3");
    container.innerHTML = (heading ? heading.outerHTML : "<h3>Leaderboard</h3>") + items;
  }
}

// ── Bounty count badge ─────────────────────────────────────────────────────
function renderBountyCount(bounties) {
  // Update "Assignments Due" stat box with active bounty count if element exists
  const assignmentVal = document.querySelector(".stat-box:last-child .value");
  if (assignmentVal && bounties) {
    assignmentVal.textContent = bounties.length;
    const label = document.querySelector(".stat-box:last-child .label");
    if (label) label.textContent = "Active Bounties";
  }
}

// ── Class performance canvas chart ─────────────────────────────────────────
const canvas = document.getElementById('classPerformanceChart');
if (canvas) {
  const ctx = canvas.getContext('2d');
  const points = [
    { x: 10, y: 60 }, { x: 40, y: 45 }, { x: 70, y: 65 },
    { x: 100, y: 40 }, { x: 130, y: 50 }, { x: 160, y: 35 },
    { x: 190, y: 45 }, { x: 200, y: 40 },
  ];
  const lineColor = '#ffffffff';
  const fillColor = 'rgba(255, 255, 255, 0.28)';

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
  ctx.strokeStyle = lineColor;
  ctx.lineWidth = 3;
  ctx.stroke();

  ctx.lineTo(points[points.length - 1].x, canvas.height);
  ctx.lineTo(points[0].x, canvas.height);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();
}