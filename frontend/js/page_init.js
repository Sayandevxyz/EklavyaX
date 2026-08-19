/**
 * js/page_init.js
 * ───────────────
 * Shared helper loaded AFTER api.js on every protected page.
 *
 * Call window.initPage(role, loginUrl) in an inline script at the top of
 * <body> (or as the first thing in the page's own JS file) to:
 *   1. Redirect unauthenticated / wrong-role users to the login page.
 *   2. Inject the real username into #profileName.
 *   3. Wire #profileAction as a "Log out" button.
 *
 * Returns the user object on success, or null (already redirecting).
 */
function initPage(role, loginUrl) {
  const user = EklavyaXAPI.requireAuth(role, loginUrl);
  if (!user) return null;

  // Inject display name
  const nameEl = document.getElementById("profileName");
  if (nameEl) nameEl.textContent = EklavyaXAPI.displayName(user);

  // Dynamically apply user avatar based on gender/role
  if (EklavyaXAPI.applyUserAvatar) {
    EklavyaXAPI.applyUserAvatar(user);
  }

  // Asynchronously refresh profile from backend if logged in
  if (EklavyaXAPI.isLoggedIn() && EklavyaXAPI.me) {
    EklavyaXAPI.me().then((freshUser) => {
      if (freshUser) {
        EklavyaXAPI.saveSession(EklavyaXAPI.getToken(), freshUser);
        if (nameEl) nameEl.textContent = EklavyaXAPI.displayName(freshUser);
        if (EklavyaXAPI.applyUserAvatar) EklavyaXAPI.applyUserAvatar(freshUser);
      }
    }).catch(() => {});
  }

  // Wire logout
  const actionEl = document.getElementById("profileAction");
  if (actionEl) {
    actionEl.textContent = "Log out";
    actionEl.style.cursor = "pointer";
    actionEl.addEventListener("click", (e) => {
      e.stopPropagation();
      EklavyaXAPI.logout(loginUrl);
    });
  }

  return user;
}
