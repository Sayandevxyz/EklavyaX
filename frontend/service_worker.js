/**
 * service_worker.js — EklavyaX Offline & PWA Engine
 * ──────────────────────────────────────────────────
 * Provides offline caching for students with low or intermittent
 * internet connectivity, specifically caching quizzes and lab simulations.
 */

const CACHE_NAME = "eklavyax-v2.0-cache";
const PRECACHE_URLS = [
  "/",
  "/index.html",
  "/css/global.css",
  "/css/app_pages.css",
  "/css/quiz.css",
  "/css/student_lab_simulation.css",
  "/js/api.js",
  "/js/theme_toggle.js",
  "/js/voice_tutor.js",
  "/student/student_dashboard.html",
  "/student/quiz.html",
  "/student/lab_simulation.html",
  "/student/flashcards.html",
  "/student/leaderboard.html",
  "/student/certificates.html",
  "/student/study_planner.html",
  "/student/study_groups.html",
  "/favicon.ico"
];

// 1. Install event: Precache core app shell & offline learning tools
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[EklavyaX Service Worker] Pre-caching offline modules...");
      return cache.addAll(PRECACHE_URLS).catch((err) => {
        console.warn("[EklavyaX Service Worker] Cache addAll skipped missing items:", err);
      });
    }).then(() => self.skipWaiting())
  );
});

// 2. Activate event: Clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("[EklavyaX Service Worker] Clearing old cache:", key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. Fetch event: Stale-While-Revalidate for assets, Network-First for API with cache fallback
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // For non-GET requests, just pass through
  if (event.request.method !== "GET") {
    return;
  }

  // API Requests: Network first, fall back to cached data
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request).then((cached) => {
            if (cached) return cached;
            return new Response(
              JSON.stringify({
                offline: true,
                detail: "Aap abhi offline hain. Connect hone par latest progress sync ho jayegi."
              }),
              { headers: { "Content-Type": "application/json" } }
            );
          });
        })
    );
    return;
  }

  // Static Assets (HTML/CSS/JS/Fonts): Cache first, fallback to network
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        // Fetch update in background
        fetch(event.request).then((freshResponse) => {
          if (freshResponse && freshResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, freshResponse));
          }
        }).catch(() => {});
        return cachedResponse;
      }

      return fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return networkResponse;
      }).catch(() => {
        // Return offline page if navigating
        if (event.request.headers.get("accept")?.includes("text/html")) {
          return caches.match("/student/quiz.html");
        }
      });
    })
  );
});
