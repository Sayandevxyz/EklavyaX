/**
 * js/auth.js
 * ──────────
 * Drives both the login/signup "blade" toggle animation and the real
 * calls to the Synapse backend for the student & teacher login pages.
 * The page just needs a #authRoot element with data-role + data-redirect.
 */
(function () {
  const root = document.getElementById("authRoot");
  if (!root) return;

  const role = root.dataset.role; // "student" | "teacher"
  const redirectUrl = root.dataset.redirect;

  const card = root.querySelector(".auth-card");
  const loginForm = root.querySelector("#loginForm");
  const signupForm = root.querySelector("#signupForm");
  const errorBox = root.querySelector("#authError");

  const bladeLoginTitle = root.querySelector("[data-blade-title-login]");
  const bladeSignupTitle = root.querySelector("[data-blade-title-signup]");
  const bladeLoginSub = root.querySelector("[data-blade-sub-login]");
  const bladeSignupSub = root.querySelector("[data-blade-sub-signup]");
  const bladeLoginBtn = root.querySelector("[data-blade-btn-login]");
  const bladeSignupBtn = root.querySelector("[data-blade-btn-signup]");

  function showError(message) {
    if (!errorBox) return;
    errorBox.textContent = message;
    errorBox.classList.add("is-visible");
  }

  function clearError() {
    if (!errorBox) return;
    errorBox.textContent = "";
    errorBox.classList.remove("is-visible");
  }

  function setMode(mode) {
    card.dataset.mode = mode;
    clearError();

    if (mode === "signup") {
      loginForm.classList.remove("is-active");
      signupForm.classList.add("is-active");
      if (bladeLoginTitle) bladeLoginTitle.style.display = "none";
      if (bladeSignupTitle) bladeSignupTitle.style.display = "";
      if (bladeLoginSub) bladeLoginSub.style.display = "none";
      if (bladeSignupSub) bladeSignupSub.style.display = "";
      if (bladeLoginBtn) bladeLoginBtn.style.display = "none";
      if (bladeSignupBtn) bladeSignupBtn.style.display = "inline-flex";
    } else {
      signupForm.classList.remove("is-active");
      loginForm.classList.add("is-active");
      if (bladeSignupTitle) bladeSignupTitle.style.display = "none";
      if (bladeLoginTitle) bladeLoginTitle.style.display = "";
      if (bladeSignupSub) bladeSignupSub.style.display = "none";
      if (bladeLoginSub) bladeLoginSub.style.display = "";
      if (bladeSignupBtn) bladeSignupBtn.style.display = "none";
      if (bladeLoginBtn) bladeLoginBtn.style.display = "inline-flex";
    }
  }

  root.querySelectorAll("[data-switch-to]").forEach((btn) => {
    btn.addEventListener("click", () => setMode(btn.dataset.switchTo));
  });

  // Honour ?role= for anyone bookmarking / sharing a link with it, even
  // though each page is already role-specific.
  const urlRole = new URLSearchParams(window.location.search).get("role");
  if (urlRole && urlRole !== role) {
    console.warn(`This is the ${role} login page; ignoring ?role=${urlRole}`);
  }

  function slugifyUsername(first, last, email) {
    // Backend only allows letters, numbers, hyphens and underscores.
    const base = `${first}-${last}`.trim().toLowerCase() || email.split("@")[0];
    const cleaned = base.replace(/[^a-z0-9-_]/g, "").replace(/^[-_]+|[-_]+$/g, "");
    return (cleaned || "EklavyaX-user").slice(0, 40);
  }

  async function handleLogin(e) {
    e.preventDefault();
    clearError();
    const form = e.target;
    const submitBtn = form.querySelector(".auth-submit");
    const username = form.username.value.trim();
    const password = form.password.value;

    submitBtn.disabled = true;
    submitBtn.textContent = "Signing in…";
    try {
      const result = await EklavyaXAPI.login({ username, password });
      if (result.user.role !== role) {
        showError(
          `That account is registered as a ${result.user.role}. Please use the ${result.user.role} login page instead.`
        );
        return;
      }
      EklavyaXAPI.saveSession(result.access_token, result.user);
      window.location.href = redirectUrl;
    } catch (err) {
      showError(err.message || "Login failed. Please check your credentials.");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Sign in";
    }
  }

  async function handleSignup(e) {
    e.preventDefault();
    clearError();
    const form = e.target;
    const submitBtn = form.querySelector(".auth-submit");

    const firstName = form.firstName.value.trim();
    const lastName = form.lastName.value.trim();
    const email = form.email.value.trim();
    const password = form.password.value;
    const confirmPassword = form.confirmPassword.value;

    if (password !== confirmPassword) {
      showError("Passwords don't match.");
      return;
    }
    if (password.length < 8) {
      showError("Password must be at least 8 characters.");
      return;
    }

    const username = slugifyUsername(firstName, lastName, email);

    const gender = (form.gender && form.gender.value) ? form.gender.value : (role === "teacher" ? "male" : "boy");
    const isFemale = gender === "female" || gender === "girl";
    const avatar_url = role === "teacher"
      ? (isFemale ? "assets/img/teacher_female.jpg" : "assets/img/teacher_male.jpg")
      : (isFemale ? "assets/img/student_girl.jpg" : "assets/img/student_boy.jpg");

    submitBtn.disabled = true;
    submitBtn.textContent = "Creating account…";
    try {
      let result;
      try {
        result = await EklavyaXAPI.register({ username, email, password, role, gender, avatar_url });
      } catch (err) {
        // Username collision → retry once with a short random suffix.
        if (/already taken/i.test(err.message || "")) {
          const suffix = Math.floor(100 + Math.random() * 900);
          result = await EklavyaXAPI.register({
            username: `${username}-${suffix}`,
            email,
            password,
            role,
            gender,
            avatar_url,
          });
        } else {
          throw err;
        }
      }
      EklavyaXAPI.saveSession(result.access_token, result.user);
      window.location.href = redirectUrl;
    } catch (err) {
      showError(err.message || "Couldn't create your account. Please try again.");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Create account";
    }
  }

  loginForm.addEventListener("submit", handleLogin);
  signupForm.addEventListener("submit", handleSignup);

  // If already logged in as this role, skip straight to the dashboard.
  const existingUser = EklavyaXAPI.getUser();
  if (EklavyaXAPI.isLoggedIn() && existingUser && existingUser.role === role) {
    window.location.href = redirectUrl;
  }
})();
