/**
 * js/faction_wars.js
 * ──────────────────
 * Comprehensive Faction Wars controller.
 * Powers:
 *   - Real-time active battle polling with synchronized countdown
 *   - Interactive clickable House cards & House Details/Champions Modal
 *   - Multi-tab navigation (Battle Arena, Great Houses & Lore, Season Standings, Battle Archive, Rules)
 *   - Filterable House Contribution Leaderboard (My House, House Vidyut, Agni, Vayu, Prithvi)
 *   - Quick STEM Quiz subject selector launcher
 *   - Peer Challenge integration
 *   - Real-time status banner
 */

const EklavyaXFactionWars = (() => {
  let pollTimer = null;
  let countdownTimer = null;
  let currentBattleId = null;
  let battleEndTime = null;
  let currentUser = null;
  let activeFactionFilter = "my";
  let cachedFactions = [];
  let selectedWagerCoins = 5;

  const DEFAULT_POLL_INTERVAL_MS = 5000;

  const HOUSE_ICONS = {
    "House Vidyut": "fa-bolt",
    "House Agni": "fa-fire",
    "House Vayu": "fa-wind",
    "House Prithvi": "fa-mountain",
  };

  const HOUSE_COLORS = {
    "House Vidyut": "#3B82F6",
    "House Agni": "#EF4444",
    "House Vayu": "#10B981",
    "House Prithvi": "#F59E0B",
  };

  // ── Initialize ─────────────────────────────────────────────────────────────

  async function init() {
    // Defensive check if API script is still evaluating or cached
    if (typeof window.EklavyaXAPI === "undefined" || typeof window.EklavyaXAPI.getActiveFactionBattle !== "function") {
      console.warn("EklavyaXAPI not yet ready for Faction Wars, retrying in 200ms...");
      setTimeout(init, 200);
      return;
    }

    currentUser = window.EklavyaXAPI.getUser();
    updateUserStatusStrip();

    // Fetch initial active battle data
    await fetchActiveBattle();

    // Start background polling loop
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(fetchActiveBattle, DEFAULT_POLL_INTERVAL_MS);

    // Preload factions list
    loadFactionsData();
  }

  // ── Tab Management ──

  function switchTab(tabKey) {
    const tabs = ["arena", "houses", "standings", "archive", "rules"];
    tabs.forEach((t) => {
      const btn = document.getElementById(`tabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`);
      const view = document.getElementById(`tabView${t.charAt(0).toUpperCase() + t.slice(1)}`);
      if (btn) {
        if (t === tabKey) btn.classList.add("active");
        else btn.classList.remove("active");
      }
      if (view) {
        if (t === tabKey) view.classList.add("active");
        else view.classList.remove("active");
      }
    });

    if (tabKey === "houses") {
      renderHousesShowcase();
    } else if (tabKey === "standings") {
      renderSeasonalStandings();
    } else if (tabKey === "archive") {
      renderBattleArchive();
    }
  }

  // ── User Status Strip ──

  function updateUserStatusStrip() {
    if (!currentUser) return;

    const houseNameEl = document.getElementById("userHouseName");
    const houseIconEl = document.getElementById("userHouseIcon");
    const houseRankEl = document.getElementById("userHouseRank");
    const userBattleXpEl = document.getElementById("userBattleXp");

    // Determine user house name from cached list or fallback
    const userFactionId = currentUser.faction_id || 3;
    const houseNames = {
      1: "House Vidyut",
      2: "House Agni",
      3: "House Vayu",
      4: "House Prithvi",
    };
    const name = houseNames[userFactionId] || "House Vayu";

    if (houseNameEl) houseNameEl.textContent = name;
    if (houseIconEl) {
      houseIconEl.className = `fas ${HOUSE_ICONS[name] || "fa-shield-alt"}`;
      houseIconEl.style.color = HOUSE_COLORS[name] || "var(--accent-gold)";
    }
  }

  // ── Poll Active Battle ──

  async function fetchActiveBattle() {
    try {
      const resp = await window.EklavyaXAPI.getActiveFactionBattle();

      if (resp.status === "no_active_battle" || !resp.battle_id) {
        renderNoBattle(resp);
        return;
      }

      currentBattleId = resp.battle_id;
      battleEndTime = new Date(resp.end_time);

      renderBattleArena(resp);
      startCountdown();

      // Fetch leaderboard based on active filter
      await fetchLeaderboardForCurrentFilter();
    } catch (err) {
      console.warn("Faction Wars poll error:", err.message);
    }
  }

  async function refreshLiveBattle() {
    const btn = document.getElementById("manualRefreshBtn");
    if (btn) btn.classList.add("spinning");
    await fetchActiveBattle();
    setTimeout(() => {
      if (btn) btn.classList.remove("spinning");
    }, 600);
  }

  // ── Render Battle Arena ──

  function renderBattleArena(data) {
    const activeSection = document.getElementById("activeBattleSection");
    const noBattleEl = document.getElementById("noBattleState");
    if (activeSection) activeSection.style.display = "block";
    if (noBattleEl) noBattleEl.style.display = "none";

    const titleEl = document.getElementById("battleTitle");
    if (titleEl) titleEl.textContent = data.title || "Faction Wars STEM Showdown";

    // Faction cards grid & VS Bar
    const cardsContainer = document.getElementById("factionCardsGrid");
    const vsBarContainer = document.getElementById("vsMultiBar");

    if (!cardsContainer || !vsBarContainer) return;

    cardsContainer.innerHTML = "";
    vsBarContainer.innerHTML = "";

    const totalBattleXp = data.scores.reduce((acc, s) => acc + s.total_xp, 0) || 1;
    const maxScore = Math.max(...data.scores.map((s) => s.total_xp), 1);

    data.scores.forEach((fScore) => {
      const isUserFaction = currentUser && currentUser.faction_id === fScore.faction_id;
      const color = fScore.color_hex || HOUSE_COLORS[fScore.faction_name] || "#3B82F6";
      const iconClass = HOUSE_ICONS[fScore.faction_name] || "fa-shield-alt";
      const cardPct = Math.round((fScore.total_xp / maxScore) * 100);
      const vsSegmentPct = Math.max(5, (fScore.total_xp / totalBattleXp) * 100);

      // Card Element
      const card = document.createElement("div");
      card.className = `faction-war-card ${isUserFaction ? "is-user-faction" : ""}`;
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.setAttribute("title", `Click to view ${fScore.faction_name} details & champions`);
      card.onclick = () => {
        openHouseModal(fScore.faction_id);
        filterLeaderboard(fScore.faction_id);
      };

      card.innerHTML = `
        ${isUserFaction ? '<span class="faction-card-badge">Your House</span>' : ""}
        <div class="faction-card-header">
          <div class="faction-icon-circle" style="background: ${color};">
            <i class="fas ${iconClass}"></i>
          </div>
          <div>
            <h3>${escapeHtml(fScore.faction_name)}</h3>
            <span>Click for House Lore</span>
          </div>
        </div>
        <div class="faction-score-number">
          ${fScore.total_xp.toLocaleString()} <small>XP</small>
        </div>
        <div class="faction-card-bar-bg">
          <div class="faction-card-bar-fill" style="width: ${cardPct}%; background: ${color};"></div>
        </div>
        <div class="faction-contributors-label">
          <span>Contributors</span>
          <strong>${fScore.contributor_count} Active</strong>
        </div>
        <div class="faction-card-click-hint">
          <i class="fas fa-search-plus"></i> View Champions & Lore
        </div>
      `;
      cardsContainer.appendChild(card);

      // VS multi-segment bar
      const seg = document.createElement("div");
      seg.className = "vs-bar-segment";
      seg.style.width = `${vsSegmentPct}%`;
      seg.style.background = color;
      seg.title = `${fScore.faction_name}: ${fScore.total_xp} XP (${Math.round(vsSegmentPct)}%)`;
      seg.onclick = () => {
        openHouseModal(fScore.faction_id);
      };
      vsBarContainer.appendChild(seg);
    });
  }

  // ── Timer Countdown ──

  function startCountdown() {
    if (countdownTimer) clearInterval(countdownTimer);

    function update() {
      if (!battleEndTime) return;
      const now = new Date();
      const diffMs = battleEndTime - now;

      const timerEl = document.getElementById("battleRemainingTimer");
      if (!timerEl) return;

      if (diffMs <= 0) {
        timerEl.textContent = "00:00:00";
        const statusTag = document.getElementById("battleStatusTag");
        if (statusTag) {
          statusTag.innerHTML = '<i class="fas fa-hourglass-end"></i> Concluded';
          statusTag.style.background = "rgba(100, 116, 139, 0.3)";
          statusTag.style.color = "#cbd5e1";
          statusTag.style.borderColor = "#64748b";
        }
        return;
      }

      const totalSec = Math.floor(diffMs / 1000);
      const hrs = String(Math.floor(totalSec / 3600)).padStart(2, "0");
      const mins = String(Math.floor((totalSec % 3600) / 60)).padStart(2, "0");
      const secs = String(totalSec % 60).padStart(2, "0");

      timerEl.textContent = `${hrs}:${mins}:${secs}`;
    }

    update();
    countdownTimer = setInterval(update, 1000);
  }

  // ── Leaderboard & Filtering ──

  function filterLeaderboard(factionId) {
    activeFactionFilter = factionId;

    // Update active class on filter pill buttons
    const pills = document.querySelectorAll(".fw-filter-pill");
    pills.forEach((p) => {
      const pId = p.getAttribute("data-faction-id");
      if (String(pId) === String(factionId)) {
        p.classList.add("active");
      } else {
        p.classList.remove("active");
      }
    });

    fetchLeaderboardForCurrentFilter();
  }

  async function fetchLeaderboardForCurrentFilter() {
    if (!currentBattleId) return;

    let targetId = null;
    if (activeFactionFilter !== "my" && activeFactionFilter !== null) {
      targetId = parseInt(activeFactionFilter, 10);
    } else if (currentUser && currentUser.faction_id) {
      targetId = currentUser.faction_id;
    }

    try {
      const lb = await window.EklavyaXAPI.getFactionBattleLeaderboard(currentBattleId, targetId);
      renderLeaderboard(lb);
    } catch (err) {
      console.warn("Leaderboard fetch error:", err.message);
    }
  }

  function renderLeaderboard(data) {
    const tableBody = document.getElementById("contributionTableBody");
    const houseNameEl = document.getElementById("leaderboardHouseName");

    if (houseNameEl) {
      houseNameEl.textContent = data.faction_name || "House";
    }

    if (!tableBody) return;
    tableBody.innerHTML = "";

    if (!data.entries || data.entries.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 24px;">
            No contributions recorded yet for ${escapeHtml(data.faction_name)}. Play a STEM quiz to score!
          </td>
        </tr>
      `;
      return;
    }

    data.entries.forEach((e) => {
      const isMe = currentUser && currentUser.id === e.user_id;
      const row = document.createElement("tr");
      if (isMe) {
        row.style.background = "rgba(244, 174, 37, 0.12)";
        // Update user status strip live contribution
        const userBattleXpEl = document.getElementById("userBattleXp");
        const userHouseRankEl = document.getElementById("userHouseRank");
        if (userBattleXpEl) userBattleXpEl.textContent = `+${e.xp_contributed} XP`;
        if (userHouseRankEl) userHouseRankEl.textContent = `#${e.rank} Contributor`;
      }

      let rankClass = "";
      if (e.rank === 1) rankClass = "top-1";
      else if (e.rank === 2) rankClass = "top-2";
      else if (e.rank === 3) rankClass = "top-3";

      row.innerHTML = `
        <td><span class="rank-badge ${rankClass}">#${e.rank}</span></td>
        <td>
          <strong>${escapeHtml(e.username)}</strong>
          ${isMe ? ' <span style="font-size:0.75rem; color:var(--accent-gold); font-weight:800;">(You)</span>' : ""}
        </td>
        <td style="color: #6ee7b7; font-weight: 700;">+${e.xp_contributed} XP</td>
        <td>${e.questions_answered} Qs</td>
      `;
      tableBody.appendChild(row);
    });
  }

  // ── Load Factions Data ──

  async function loadFactionsData() {
    try {
      if (window.EklavyaXAPI.listFactions) {
        cachedFactions = await window.EklavyaXAPI.listFactions();
      }
    } catch (err) {
      console.warn("Could not load factions list:", err.message);
    }
  }

  // ── Tab 2: The Great Houses Showcase ──

  async function renderHousesShowcase() {
    const grid = document.getElementById("housesShowcaseGrid");
    if (!grid) return;
    grid.innerHTML = '<div style="text-align:center; color:var(--text-muted); padding:30px; grid-column: 1/-1;"><i class="fas fa-spinner fa-spin"></i> Loading Great Houses...</div>';

    if (!cachedFactions || cachedFactions.length === 0) {
      await loadFactionsData();
    }

    grid.innerHTML = "";
    cachedFactions.forEach((f) => {
      const isMyHouse = currentUser && currentUser.faction_id === f.id;
      const color = f.color_hex || HOUSE_COLORS[f.name] || "#3B82F6";
      const icon = f.icon || HOUSE_ICONS[f.name] || "fa-shield-alt";

      const card = document.createElement("div");
      card.className = `house-showcase-card ${isMyHouse ? "is-my-house" : ""}`;

      let championsHtml = "";
      if (f.top_champions && f.top_champions.length > 0) {
        championsHtml = f.top_champions
          .map(
            (c, idx) => `
            <div class="champion-row">
              <span><strong>#${idx + 1}</strong> ${escapeHtml(c.username)}</span>
              <span style="color: var(--accent-gold); font-weight:700;">${c.xp} XP (Lvl ${c.level})</span>
            </div>
          `
          )
          .join("");
      } else {
        championsHtml = '<p style="color:var(--text-muted); font-size:0.8rem; margin:0;">No champions recorded yet.</p>';
      }

      card.innerHTML = `
        ${isMyHouse ? '<span class="faction-card-badge" style="position:absolute; top:16px; right:16px;">Your House</span>' : ""}
        <div class="house-crest-header">
          <div class="house-crest-icon" style="background: ${color};">
            <i class="fas ${icon}"></i>
          </div>
          <div class="house-crest-info">
            <h3>${escapeHtml(f.name)}</h3>
            <span class="house-element-tag">${escapeHtml(f.element || "STEM Domain")}</span>
          </div>
        </div>

        <p class="house-motto-quote">"${escapeHtml(f.motto || "Honour and intellect in learning.")}"</p>

        <div class="house-domain-badge">
          <i class="fas fa-book" style="color: ${color}; margin-right: 6px;"></i>
          <strong>Domain:</strong> ${escapeHtml(f.domain || "Physics & Computing")}
        </div>

        <div class="house-stats-row">
          <div class="house-stat-item">
            <strong>${f.score.toLocaleString()}</strong>
            <span>All-Time Points</span>
          </div>
          <div class="house-stat-item">
            <strong>${f.member_count}</strong>
            <span>Members</span>
          </div>
        </div>

        <div class="house-champions-section">
          <h4><i class="fas fa-crown" style="color: var(--accent-gold);"></i> House Champions</h4>
          ${championsHtml}
        </div>

        <div class="house-card-actions">
          <button class="quiz-btn quiz-btn-primary" onclick="EklavyaXFactionWars.openHouseModal(${f.id})" style="justify-content: center; font-size: 0.86rem;">
            <i class="fas fa-search-plus"></i> View Full Lore & Roster
          </button>
        </div>
      `;
      grid.appendChild(card);
    });
  }

  // ── Tab 3: Seasonal House Standings (Podium) ──

  async function renderSeasonalStandings() {
    const grid = document.getElementById("seasonPodiumGrid");
    if (!grid) return;
    grid.innerHTML = '<div style="text-align:center; color:var(--text-muted); padding:30px; grid-column:1/-1;"><i class="fas fa-spinner fa-spin"></i> Loading Seasonal Standings...</div>';

    if (!cachedFactions || cachedFactions.length === 0) {
      await loadFactionsData();
    }

    grid.innerHTML = "";
    cachedFactions.forEach((f, idx) => {
      const isMyHouse = currentUser && currentUser.faction_id === f.id;
      const color = f.color_hex || HOUSE_COLORS[f.name] || "#3B82F6";
      const icon = f.icon || HOUSE_ICONS[f.name] || "fa-shield-alt";

      const trophyClass = `rank-${idx + 1}`;
      const card = document.createElement("div");
      card.className = "season-standings-card";
      if (isMyHouse) {
        card.style.borderColor = "var(--accent-gold)";
        card.style.background = "linear-gradient(180deg, rgba(244,174,37,0.08) 0%, rgba(20,56,42,0.95) 100%)";
      }

      card.innerHTML = `
        <i class="fas fa-trophy season-rank-trophy ${trophyClass}"></i>
        <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; font-weight:700; margin-bottom: 4px;">
          Rank #${idx + 1}
        </div>
        <h3 style="font-size: 1.3rem; color: var(--text); margin-bottom: 8px;">
          <i class="fas ${icon}" style="color: ${color}; margin-right: 6px;"></i>
          ${escapeHtml(f.name)}
        </h3>
        <div style="font-size: 2rem; font-weight: 800; color: var(--accent-gold); margin-bottom: 12px;">
          ${f.score.toLocaleString()} <small style="font-size: 0.9rem; color: var(--text-muted);">Points</small>
        </div>
        <p style="color: var(--text-muted); font-size: 0.84rem; margin-bottom: 16px;">
          ${f.member_count} enrolled scholars • Domain: ${escapeHtml(f.domain || "STEM")}
        </p>
        <button class="quiz-btn quiz-btn-secondary" onclick="EklavyaXFactionWars.openHouseModal(${f.id})" style="width: 100%; justify-content: center; font-size: 0.84rem;">
          View House Standings
        </button>
      `;
      grid.appendChild(card);
    });
  }

  // ── Tab 4: Battle Archive ──

  async function renderBattleArchive() {
    const list = document.getElementById("battleHistoryList");
    if (!list) return;
    list.innerHTML = '<div style="text-align:center; color:var(--text-muted); padding:30px;"><i class="fas fa-spinner fa-spin"></i> Loading Battle Archive...</div>';

    try {
      const resp = await window.EklavyaXAPI.getBattleHistory();
      list.innerHTML = "";

      if (!resp.battles || resp.battles.length === 0) {
        list.innerHTML = `
          <div class="no-battle-banner" style="padding: 40px 20px;">
            <i class="fas fa-history" style="font-size: 2.2rem;"></i>
            <h3 style="color: var(--text); margin: 8px 0;">No Past Battles Archived Yet</h3>
            <p style="color: var(--text-muted); font-size: 0.9rem;">
              The current active battle is underway. Once concluded, victory standings and reward payouts will be archived here.
            </p>
          </div>
        `;
        return;
      }

      resp.battles.forEach((b) => {
        const card = document.createElement("div");
        card.className = "history-card";

        const startDate = new Date(b.start_time).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        });

        const scoresHtml = b.scores
          .map(
            (s) => `
            <div class="history-score-chip">
              <span><strong>${escapeHtml(s.faction_name)}</strong></span>
              <span style="color: ${s.color_hex || 'var(--accent-gold)'}; font-weight:700;">${s.total_xp} XP</span>
            </div>
          `
          )
          .join("");

        card.innerHTML = `
          <div class="history-card-header">
            <div>
              <h3 style="color: var(--text); font-size: 1.15rem; margin: 0 0 4px;">${escapeHtml(b.title)}</h3>
              <span style="font-size: 0.78rem; color: var(--text-muted);">Concluded on ${startDate}</span>
            </div>
            <div class="history-winner-pill">
              <i class="fas fa-crown"></i> Victor: ${escapeHtml(b.winning_faction_name || "Draw")}
            </div>
          </div>
          <div class="history-scores-preview">
            ${scoresHtml}
          </div>
        `;
        list.appendChild(card);
      });
    } catch (err) {
      list.innerHTML = `<p style="color:#ef4444; text-align:center;">Failed to load battle archive: ${escapeHtml(err.message)}</p>`;
    }
  }

  // ── House Detail Modal ──

  function openHouseModal(factionId) {
    const modal = document.getElementById("houseDetailModal");
    const titleEl = document.getElementById("modalHouseTitle");
    const bodyEl = document.getElementById("modalHouseBody");

    if (!modal || !bodyEl) return;

    const faction = cachedFactions.find((f) => f.id === factionId) || {
      id: factionId,
      name: "House Details",
      description: "Faction within EklavyaX",
      element: "STEM",
      domain: "Science & Technology",
      score: 0,
      member_count: 1,
      motto: "Knowledge is power.",
      color_hex: "#3B82F6",
      top_champions: [],
    };

    if (titleEl) {
      titleEl.innerHTML = `<i class="fas ${faction.icon || HOUSE_ICONS[faction.name] || 'fa-shield-alt'}" style="color: ${faction.color_hex || 'var(--accent-gold)'}"></i> ${escapeHtml(faction.name)}`;
    }

    let championsHtml = "";
    if (faction.top_champions && faction.top_champions.length > 0) {
      championsHtml = faction.top_champions
        .map(
          (c, idx) => `
          <div class="champion-row" style="padding: 8px 0;">
            <span><strong style="color:var(--accent-gold);">#${idx + 1}</strong> ${escapeHtml(c.username)}</span>
            <span style="color: #6ee7b7; font-weight:700;">+${c.xp} XP</span>
          </div>
        `
        )
        .join("");
    } else {
      championsHtml = '<p style="color:var(--text-muted); font-size:0.85rem;">No student champions recorded yet.</p>';
    }

    bodyEl.innerHTML = `
      <div style="margin-bottom: 18px;">
        <p style="color: var(--text); font-size: 0.95rem; line-height: 1.5; margin-bottom: 12px;">
          ${escapeHtml(faction.description || "A venerable house dedicated to mastery of STEM concepts.")}
        </p>
        <p style="font-style: italic; color: var(--accent-gold); font-size: 0.9rem; padding: 8px 12px; background: rgba(0,0,0,0.25); border-radius: 8px; border-left: 3px solid var(--accent-gold);">
          "${escapeHtml(faction.motto || "Through reason and curiosity, we triumph.")}"
        </p>
      </div>

      <div class="house-stats-row" style="margin-bottom: 18px;">
        <div class="house-stat-item">
          <strong>${faction.score.toLocaleString()}</strong>
          <span>All-Time Score</span>
        </div>
        <div class="house-stat-item">
          <strong>${faction.member_count}</strong>
          <span>Enrolled Members</span>
        </div>
      </div>

      <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; margin-bottom: 20px;">
        <h4 style="font-size: 0.82rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px;">
          <i class="fas fa-crown" style="color: var(--accent-gold);"></i> Leading House Champions
        </h4>
        ${championsHtml}
      </div>

      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <button class="quiz-btn quiz-btn-primary" onclick="EklavyaXFactionWars.closeModal('houseDetailModal'); EklavyaXFactionWars.openQuickQuizModal();" style="flex: 1; justify-content: center;">
          <i class="fas fa-bolt"></i> Compete in STEM Quiz
        </button>
        <button class="quiz-btn quiz-btn-secondary" onclick="EklavyaXFactionWars.closeModal('houseDetailModal'); EklavyaXFactionWars.switchTab('arena'); EklavyaXFactionWars.filterLeaderboard(${faction.id});" style="flex: 1; justify-content: center;">
          <i class="fas fa-list"></i> View Live Contributors
        </button>
      </div>
    `;

    modal.classList.add("active");
  }

  // ── Modals & Quick Actions ──

  function openQuickQuizModal() {
    const modal = document.getElementById("quickQuizModal");
    if (modal) modal.classList.add("active");
  }

  function startQuizForTopic(topic) {
    closeModal("quickQuizModal");
    const qs = topic ? `?topic=${encodeURIComponent(topic)}` : "";
    window.location.href = `quiz.html${qs}`;
  }

  function openPeerChallengeModal() {
    const modal = document.getElementById("peerChallengeModal");
    if (modal) modal.classList.add("active");
  }

  function selectWager(amount, el) {
    selectedWagerCoins = amount;
    const buttons = document.querySelectorAll("#wagerBtnGroup .wager-btn");
    buttons.forEach((b) => b.classList.remove("selected"));
    if (el) el.classList.add("selected");
  }

  async function createPeerChallenge() {
    const subjectEl = document.getElementById("challengeSubjectSelect");
    const subject = subjectEl ? subjectEl.value : "Physics";
    const btn = document.getElementById("createChallengeBtn");

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    }

    try {
      await window.EklavyaXAPI.createChallenge({
        opponent_id: null, // Open challenge
        subject: subject,
        wager_coins: selectedWagerCoins,
      });

      closeModal("peerChallengeModal");
      alert(`🎉 Open challenge in ${subject} created for ${selectedWagerCoins} EduCoins! When a classmate accepts, the victor earns the wager pot + House XP.`);
    } catch (err) {
      alert(`Failed to create challenge: ${err.message}`);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check-circle"></i> Create Open Challenge';
      }
    }
  }

  function openRulesModal() {
    const modal = document.getElementById("battleRulesModal");
    if (modal) modal.classList.add("active");
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove("active");
  }

  // ── Trigger / Reset Battle ──

  async function triggerNewBattle() {
    try {
      await window.EklavyaXAPI.startNewFactionBattle();
      await fetchActiveBattle();
    } catch (err) {
      alert(`Failed to start battle: ${err.message}`);
    }
  }

  // ── No Battle State ──

  function renderNoBattle(data) {
    const activeSection = document.getElementById("activeBattleSection");
    const noBattleEl = document.getElementById("noBattleState");
    if (activeSection) activeSection.style.display = "none";
    if (noBattleEl) {
      noBattleEl.style.display = "block";
      const msg = document.getElementById("noBattleMessage");
      if (msg) msg.textContent = data.message || "No Faction War battle is currently active.";
    }
  }

  // ── Helpers ──

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function destroy() {
    if (pollTimer) clearInterval(pollTimer);
    if (countdownTimer) clearInterval(countdownTimer);
  }

  return {
    init,
    destroy,
    switchTab,
    refreshLiveBattle,
    filterLeaderboard,
    openHouseModal,
    openQuickQuizModal,
    startQuizForTopic,
    openPeerChallengeModal,
    selectWager,
    createPeerChallenge,
    openRulesModal,
    closeModal,
    triggerNewBattle,
  };
})();

// Explicitly bind to global window
if (typeof window !== "undefined") {
  window.EklavyaXFactionWars = EklavyaXFactionWars;
}
