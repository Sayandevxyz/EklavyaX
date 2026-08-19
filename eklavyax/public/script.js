// EklavyaX — shared interactions
(function () {
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- reveal-on-scroll ---- */
  var revealEls = document.querySelectorAll(".reveal");
  if (revealEls.length) {
    if (reduceMotion || !("IntersectionObserver" in window)) {
      revealEls.forEach(function (el) { el.classList.add("in"); });
    } else {
      var io = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              entry.target.classList.add("in");
              io.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.15 }
      );
      revealEls.forEach(function (el) { io.observe(el); });
    }
  }

  /* ---- animated bars (panel + progress) ---- */
  document.querySelectorAll("[data-fill]").forEach(function (el) {
    var target = el.getAttribute("data-fill");
    requestAnimationFrame(function () {
      setTimeout(function () { el.style.width = target + "%"; }, 250);
    });
  });

  /* ---- count-up stats ---- */
  var counters = document.querySelectorAll("[data-count]");
  if (counters.length) {
    var animateCounter = function (el) {
      var target = parseFloat(el.getAttribute("data-count"));
      var suffix = el.getAttribute("data-suffix") || "";
      var isDecimal = target % 1 !== 0;
      var duration = 1200;
      var start = null;

      function step(ts) {
        if (!start) start = ts;
        var progress = Math.min((ts - start) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        var value = target * eased;
        el.textContent = (isDecimal ? value.toFixed(1) : Math.round(value)) + suffix;
        if (progress < 1) requestAnimationFrame(step);
      }
      if (reduceMotion) {
        el.textContent = (isDecimal ? target.toFixed(1) : target) + suffix;
      } else {
        requestAnimationFrame(step);
      }
    };

    if ("IntersectionObserver" in window) {
      var statIo = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              animateCounter(entry.target);
              statIo.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.4 }
      );
      counters.forEach(function (el) { statIo.observe(el); });
    } else {
      counters.forEach(animateCounter);
    }
  }

  /* ---- login page: role toggle ---- */
  var roleButtons = document.querySelectorAll(".role-toggle button");
  roleButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      roleButtons.forEach(function (b) {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
    });
  });

  /* ---- login page: show/hide password ---- */
  var toggleShow = document.getElementById("toggleShow");
  var passwordInput = document.getElementById("password");
  if (toggleShow && passwordInput) {
    toggleShow.addEventListener("click", function () {
      var isHidden = passwordInput.type === "password";
      passwordInput.type = isHidden ? "text" : "password";
      toggleShow.textContent = isHidden ? "Hide" : "Show";
    });
  }

  /* ---- API base + token helpers ---- */
  var API_BASE = "/api";

  function getToken() { return localStorage.getItem("EklavyaX_token"); }
  function getUser() {
    try { return JSON.parse(localStorage.getItem("EklavyaX_user") || "null"); }
    catch (e) { return null; }
  }
  function setSession(token, user) {
    localStorage.setItem("EklavyaX_token", token);
    localStorage.setItem("EklavyaX_user", JSON.stringify(user));
  }
  function clearSession() {
    localStorage.removeItem("EklavyaX_token");
    localStorage.removeItem("EklavyaX_user");
  }

  /* ---- login page: real submit against the backend ---- */
  var loginForm = document.getElementById("loginForm");
  if (loginForm) {
    var errorEl = document.getElementById("authError");
    var activeRoleBtn = document.querySelector(".role-toggle button.active");

    loginForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = loginForm.querySelector("button[type=submit]");
      var original = btn.textContent;
      var email = document.getElementById("email").value.trim();
      var password = document.getElementById("password").value;
      var role = (document.querySelector(".role-toggle button.active") || {}).dataset
        ? document.querySelector(".role-toggle button.active").dataset.role
        : "student";

      if (errorEl) { errorEl.hidden = true; errorEl.textContent = ""; }
      btn.textContent = "Signing in…";
      btn.disabled = true;

      fetch(API_BASE + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, password: password, role: role }),
      })
        .then(function (res) {
          return res.json().then(function (data) { return { ok: res.ok, data: data }; });
        })
        .then(function (result) {
          if (!result.ok) throw new Error(result.data.error || "Sign in failed.");
          setSession(result.data.token, result.data.user);
          window.location.href = "index.html";
        })
        .catch(function (err) {
          if (errorEl) {
            errorEl.textContent = err.message;
            errorEl.hidden = false;
          }
          btn.textContent = original;
          btn.disabled = false;
        });
    });
  }

  /* ---- index page: reflect logged-in state in the nav ---- */
  var navActions = document.getElementById("navActions");
  if (navActions) {
    var user = getUser();
    if (user) {
      navActions.innerHTML =
        '<span class="nav-login">Hi, ' + user.name.split(" ")[0] + '</span>' +
        '<button type="button" class="btn btn-primary" id="logoutBtn">Logout</button>';
      var logoutBtn = document.getElementById("logoutBtn");
      logoutBtn.addEventListener("click", function () {
        clearSession();
        window.location.reload();
      });
    }
  }

  /* ---- index page: hydrate the dashboard preview with real data ---- */
  var dashPanel = document.getElementById("dashPanel");
  if (dashPanel) {
    var loggedInUser = getUser();
    var token = getToken();

    if (loggedInUser && token && loggedInUser.role === "student") {
      fetch(API_BASE + "/dashboard/me", {
        headers: { Authorization: "Bearer " + token },
      })
        .then(function (res) {
          if (!res.ok) throw new Error("Could not load dashboard.");
          return res.json();
        })
        .then(function (u) {
          var hour = new Date().getHours();
          var greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

          document.getElementById("dashGreeting").textContent = greeting;
          document.getElementById("dashName").textContent = u.name + " 👋";
          document.getElementById("dashCoins").textContent = "🪙 " + u.coins.toLocaleString();
          document.getElementById("dashStreak").textContent = "🔥 " + u.streak;
          document.getElementById("dashLevel").textContent = u.level;
          document.getElementById("dashLevelTitle").textContent = "Level · " + u.levelTitle;
          document.getElementById("dashXp").textContent = u.xp.toLocaleString();
          document.getElementById("dashXpNext").textContent = "XP · Next: " + u.xpNext.toLocaleString();
          document.getElementById("dashAccuracy").textContent = u.accuracy + "%";

          var xpPct = Math.round((u.xp / u.xpNext) * 100);
          document.getElementById("dashXpBar").setAttribute("data-fill", xpPct);
          document.getElementById("dashXpBar").style.width = xpPct + "%";
          document.getElementById("dashAccuracyBar").setAttribute("data-fill", u.accuracy);
          document.getElementById("dashAccuracyBar").style.width = u.accuracy + "%";

          if (u.continueLesson) {
            document.getElementById("dashLessonTitle").textContent = u.continueLesson.title;
            document.getElementById("dashLessonPct").textContent = u.continueLesson.progress + "%";
            document.getElementById("dashLessonBar").setAttribute("data-fill", u.continueLesson.progress);
            document.getElementById("dashLessonBar").style.width = u.continueLesson.progress + "%";
          }

          document.getElementById("dashTip").textContent = u.tip || "";
        })
        .catch(function () { /* fall back silently to the static preview */ });
    }
  }
})();
