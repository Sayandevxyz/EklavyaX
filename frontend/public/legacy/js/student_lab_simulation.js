/**
 * js/student_lab_simulation.js
 * ───────────────────────────
 * Controller for PhET Simulation Player Modal in EklavyaX.
 */

let currentLabUrl = "";

function openLab(url, labTitle = "Interactive STEM Lab") {
  currentLabUrl = url;
  const modal = document.getElementById("labModal");
  const iframe = document.getElementById("labFrame");
  const titleEl = document.getElementById("labModalTitle");
  const extLink = document.getElementById("labExternalLink");

  if (titleEl) titleEl.textContent = labTitle;
  if (extLink) extLink.href = url;

  if (iframe) {
    iframe.src = url;
  }

  if (modal) {
    modal.style.display = "flex";
    modal.classList.add("active");
    document.body.style.overflow = "hidden"; // Prevent background scroll
  }

  // Record lab activity for daily streak
  if (window.EklavyaXAPI && EklavyaXAPI.recordActivity) {
    EklavyaXAPI.recordActivity().catch(() => {});
  }
}

function closeLab() {
  const modal = document.getElementById("labModal");
  const iframe = document.getElementById("labFrame");

  if (iframe) {
    iframe.src = "";
  }

  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

// Close on backdrop click
window.addEventListener("click", function(event) {
  const modal = document.getElementById("labModal");
  if (event.target === modal) {
    closeLab();
  }
});

// Close on Escape key press
window.addEventListener("keydown", function(event) {
  if (event.key === "Escape") {
    closeLab();
  }
});