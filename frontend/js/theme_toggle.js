/**
 * theme_toggle.js — EklavyaX Multi-Theme Engine & Service Worker Registration
 * ─────────────────────────────────────────────────────────────────────────────
 * Controls theme switching (Forest, Cyberpunk, Nebula, Light)
 * and initializes PWA / Service Worker support.
 */

(function () {
  const THEME_KEY = "eklavyax_theme";
  const THEMES = [
    { id: "default", name: "🌲 Forest", label: "Eklavya Forest" },
    { id: "cyberpunk", name: "⚡ Cyberpunk", label: "Neon Dark" },
    { id: "nebula", name: "🌌 Nebula", label: "Cosmic Indigo" },
    { id: "light", name: "☀️ Vedic Sun", label: "Clean Light" },
  ];

  function getSavedTheme() {
    return localStorage.getItem(THEME_KEY) || "default";
  }

  function applyTheme(themeId) {
    if (themeId === "default") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", themeId);
    }
    localStorage.setItem(THEME_KEY, themeId);

    // Update active state on any theme buttons
    document.querySelectorAll(".theme-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-theme-id") === themeId);
    });
  }

  // Apply immediately to prevent flash of wrong theme
  applyTheme(getSavedTheme());

  // Mount theme selector widget when DOM loads
  window.addEventListener("DOMContentLoaded", () => {
    // 1. Inject Theme Switcher as a fixed bottom-right floating pill — 
    // never breaks page layout regardless of which page is open
    if (!document.getElementById("eklavya-theme-widget")) {
      const widget = document.createElement("div");
      widget.id = "eklavya-theme-widget";
      widget.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9990;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 6px 10px;
        border-radius: 24px;
        background: rgba(15, 25, 20, 0.92);
        border: 1px solid rgba(255,255,255,0.14);
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 28px rgba(0,0,0,0.45);
      `;

      const currentTheme = getSavedTheme();

      THEMES.forEach((t) => {
        const btn = document.createElement("button");
        btn.className = "theme-btn" + (t.id === currentTheme ? " active" : "");
        btn.setAttribute("data-theme-id", t.id);
        btn.title = t.label;
        btn.innerText = t.name;
        btn.style.cssText = `
          background: ${t.id === currentTheme ? "var(--accent-gold, #f4ae25)" : "transparent"};
          color: ${t.id === currentTheme ? "#0b281d" : "#e2e8f0"};
          border: none;
          border-radius: 14px;
          padding: 4px 9px;
          font-size: 11px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          white-space: nowrap;
        `;

        btn.addEventListener("click", () => {
          applyTheme(t.id);
          widget.querySelectorAll(".theme-btn").forEach((b) => {
            const isActive = b.getAttribute("data-theme-id") === t.id;
            b.style.background = isActive ? "var(--accent-gold, #f4ae25)" : "transparent";
            b.style.color = isActive ? "#0b281d" : "#e2e8f0";
          });
        });

        widget.appendChild(btn);
      });

      document.body.appendChild(widget);
    }


    // 2. Register Service Worker for offline mode
    if ("serviceWorker" in navigator && !window.location.protocol.startsWith("file")) {
      navigator.serviceWorker
        .register("/service_worker.js")
        .then((reg) => {
          console.log("[EklavyaX PWA] Service Worker registered with scope:", reg.scope);
        })
        .catch((err) => {
          console.warn("[EklavyaX PWA] Service Worker registration skipped:", err);
        });
    }

    // 3. Connectivity status listener
    window.addEventListener("online", () => {
      showConnectivityToast("🟢 Back Online! Synchronizing your progress...", "success");
    });
    window.addEventListener("offline", () => {
      showConnectivityToast("📡 Offline Mode: Quizzes & Labs are cached locally.", "warning");
    });
  });

  function showConnectivityToast(msg, type) {
    let toast = document.getElementById("eklavya-network-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "eklavya-network-toast";
      toast.style.position = "fixed";
      toast.style.bottom = "20px";
      toast.style.right = "20px";
      toast.style.padding = "10px 18px";
      toast.style.borderRadius = "10px";
      toast.style.fontSize = "13px";
      toast.style.fontWeight = "600";
      toast.style.zIndex = "9999";
      toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.3)";
      toast.style.transition = "all 0.3s ease";
      document.body.appendChild(toast);
    }
    toast.style.background = type === "success" ? "#10b981" : "#f59e0b";
    toast.style.color = "#ffffff";
    toast.innerText = msg;
    toast.style.display = "block";
    setTimeout(() => {
      if (toast) toast.style.display = "none";
    }, 4500);
  }

  // Export globally
  window.EklavyaTheme = {
    applyTheme,
    getSavedTheme,
    THEMES,
  };
})();
