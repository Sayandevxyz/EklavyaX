/**
 * voice_tutor.js — Voice-Based AI Tutor for EklavyaX (4 Languages: Hindi, English, Malayalam, Telugu)
 * ─────────────────────────────────────────────────────────────────────────────────────────────────────
 * Enables students to ask questions via voice in Hindi, English, Malayalam, or Telugu,
 * and listen to the AI's explanation with full Play, Pause, and Stop audio controls.
 */

const VoiceTutor = (() => {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

  let recognition = null;
  let isListening = false;
  let isSpeaking = false;
  let isPaused = false;
  let currentLang = "hi-IN"; // 'hi-IN', 'en-IN', 'ml-IN', 'te-IN'

  const LANGUAGE_CONFIG = {
    "hi-IN": { label: "🇮🇳 Hindi (हिन्दी)", aiName: "Hindi", voicePrefix: "hi" },
    "en-IN": { label: "🇬🇧 English", aiName: "English", voicePrefix: "en" },
    "ml-IN": { label: "🌴 Malayalam (മലയാളം)", aiName: "Malayalam", voicePrefix: "ml" },
    "te-IN": { label: "🏛️ Telugu (తెలుగు)", aiName: "Telugu", voicePrefix: "te" },
    "ta-IN": { label: "🪔 Tamil (தமிழ்)", aiName: "Tamil", voicePrefix: "ta" },
  };

  function init() {
    if (!SpeechRecognition) {
      console.warn("Web Speech API is not supported in this browser.");
      return false;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = currentLang;

    recognition.onstart = () => {
      isListening = true;
      updateUIState("listening");
    };

    recognition.onend = () => {
      isListening = false;
      updateUIState("idle");
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      isListening = false;
      updateUIState("idle");
    };

    return true;
  }

  function startListening(onResultCallback) {
    if (!recognition && !init()) {
      alert("Aapka browser Speech Recognition support nahi karta. Google Chrome ya Edge use karein.");
      return;
    }

    try {
      recognition.lang = currentLang;
      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }

        if (event.results[0].isFinal) {
          if (onResultCallback) {
            onResultCallback(transcript);
          }
        }
      };
      recognition.start();
    } catch (e) {
      console.warn("Speech recognition already running:", e);
    }
  }

  function stopListening() {
    if (recognition && isListening) {
      recognition.stop();
    }
  }

  function speakText(text, { lang = null, rate = 0.95, pitch = 1.0, onComplete } = {}) {
    if (!window.speechSynthesis) {
      console.warn("SpeechSynthesis is not supported in this browser.");
      return;
    }

    const selectedLang = lang || currentLang;

    // Stop any currently speaking audio
    window.speechSynthesis.cancel();
    isPaused = false;

    // Clean markdown symbols from spoken text
    const cleanText = text
      .replace(/[#*_`~>-]/g, " ")
      .replace(/\[.*?\]\(.*?\)/g, " ")
      .replace(/<[^>]*>/g, " ")
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = selectedLang;
    utterance.rate = rate;
    utterance.pitch = pitch;

    // Match best voice available in browser
    const voices = window.speechSynthesis.getVoices();
    const config = LANGUAGE_CONFIG[selectedLang] || LANGUAGE_CONFIG["hi-IN"];
    const matchVoice = voices.find(
      (v) =>
        v.lang === selectedLang ||
        v.lang.startsWith(config.voicePrefix) ||
        v.name.toLowerCase().includes(config.voicePrefix)
    );
    if (matchVoice) {
      utterance.voice = matchVoice;
    }

    utterance.onstart = () => {
      isSpeaking = true;
      isPaused = false;
      updateUIState("speaking");
    };

    utterance.onpause = () => {
      isPaused = true;
      updateUIState("paused");
    };

    utterance.onresume = () => {
      isPaused = false;
      updateUIState("speaking");
    };

    utterance.onend = () => {
      isSpeaking = false;
      isPaused = false;
      updateUIState("idle");
      if (onComplete) onComplete();
    };

    utterance.onerror = () => {
      isSpeaking = false;
      isPaused = false;
      updateUIState("idle");
    };

    window.speechSynthesis.speak(utterance);
  }

  function pauseSpeaking() {
    if (window.speechSynthesis && isSpeaking && !isPaused) {
      window.speechSynthesis.pause();
      isPaused = true;
      updateUIState("paused");
    }
  }

  function resumeSpeaking() {
    if (window.speechSynthesis && isSpeaking && isPaused) {
      window.speechSynthesis.resume();
      isPaused = false;
      updateUIState("speaking");
    }
  }

  function stopSpeaking() {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      isSpeaking = false;
      isPaused = false;
      updateUIState("idle");
    }
  }

  function updateUIState(state) {
    const micBtn = document.getElementById("voice-tutor-mic-btn");
    const waveElem = document.getElementById("voice-tutor-wave");
    const pauseBtn = document.getElementById("voice-tutor-pause-btn");
    const playBtn = document.getElementById("voice-tutor-play-btn");
    const stopBtn = document.getElementById("voice-tutor-stop-btn");
    const statusText = document.getElementById("voice-tutor-status-text");

    if (state === "listening") {
      if (micBtn) {
        micBtn.style.background = "#ef4444";
        micBtn.innerHTML = "🔴 Sun rahe hain...";
      }
      if (statusText) statusText.textContent = `🎙️ Listening in ${LANGUAGE_CONFIG[currentLang].aiName}...`;
    } else if (state === "speaking") {
      if (micBtn) {
        micBtn.style.background = "#3b82f6";
        micBtn.innerHTML = "🔊 Bol rahe hain...";
      }
      if (statusText) statusText.textContent = `🔊 Speaking in ${LANGUAGE_CONFIG[currentLang].aiName}...`;
      if (pauseBtn) pauseBtn.style.display = "inline-block";
      if (playBtn) playBtn.style.display = "none";
      if (stopBtn) stopBtn.style.display = "inline-block";
    } else if (state === "paused") {
      if (micBtn) {
        micBtn.style.background = "#f59e0b";
        micBtn.innerHTML = "⏸️ Paused";
      }
      if (statusText) statusText.textContent = "⏸️ Voice Paused";
      if (pauseBtn) pauseBtn.style.display = "none";
      if (playBtn) playBtn.style.display = "inline-block";
      if (stopBtn) stopBtn.style.display = "inline-block";
    } else {
      if (micBtn) {
        micBtn.style.background = "var(--accent-gold, #f4ae25)";
        micBtn.innerHTML = "🎤 Bol kar Poochein";
      }
      if (statusText) statusText.textContent = `Voice Tutor: ${LANGUAGE_CONFIG[currentLang].aiName}`;
      if (pauseBtn) pauseBtn.style.display = "none";
      if (playBtn) playBtn.style.display = "none";
      if (stopBtn) stopBtn.style.display = "none";
    }

    if (waveElem) {
      waveElem.style.display = state !== "idle" ? "flex" : "none";
    }
  }

  function setLanguage(langCode) {
    if (LANGUAGE_CONFIG[langCode]) {
      currentLang = langCode;
      if (recognition) recognition.lang = langCode;
      const statusText = document.getElementById("voice-tutor-status-text");
      if (statusText) statusText.textContent = `Voice Tutor: ${LANGUAGE_CONFIG[currentLang].aiName}`;
    }
  }

  // Floating Voice Tutor Widget Injection
  window.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("voice-tutor-float") && window.location.pathname.includes("/student/")) {
      const floatWrap = document.createElement("div");
      floatWrap.id = "voice-tutor-float";
      floatWrap.style.position = "fixed";
      floatWrap.style.bottom = "85px";
      floatWrap.style.right = "24px";
      floatWrap.style.zIndex = "9990";
      floatWrap.style.display = "flex";
      floatWrap.style.flexDirection = "column";
      floatWrap.style.alignItems = "flex-end";
      floatWrap.style.gap = "8px";

      floatWrap.innerHTML = `
        <!-- Audio Control & Wave Banner -->
        <div id="voice-tutor-wave" style="display:none; gap:8px; align-items:center; background:rgba(15,23,42,0.92); padding:8px 14px; border-radius:24px; border:1px solid rgba(255,255,255,0.18); backdrop-filter:blur(10px); box-shadow:0 8px 24px rgba(0,0,0,0.3);">
          <span id="voice-tutor-status-text" style="font-size:12px; color:#e2e8f0; font-weight:600;">Voice Tutor Active</span>
          
          <!-- Play / Resume Button -->
          <button id="voice-tutor-play-btn" title="Resume" style="display:none; background:#10b981; color:white; border:none; width:26px; height:26px; border-radius:50%; font-size:11px; cursor:pointer;">
            ▶
          </button>

          <!-- Pause Button -->
          <button id="voice-tutor-pause-btn" title="Pause" style="display:none; background:#f59e0b; color:white; border:none; width:26px; height:26px; border-radius:50%; font-size:11px; cursor:pointer;">
            ⏸
          </button>

          <!-- Stop Button -->
          <button id="voice-tutor-stop-btn" title="Stop" style="display:none; background:#ef4444; color:white; border:none; width:26px; height:26px; border-radius:50%; font-size:11px; cursor:pointer;">
            ⏹
          </button>
        </div>

        <!-- Language Selector & Mic Button Row -->
        <div style="display:flex; align-items:center; gap:8px; background:rgba(15,23,42,0.85); padding:4px 6px; border-radius:30px; border:1px solid rgba(255,255,255,0.15); box-shadow:0 8px 24px rgba(0,0,0,0.25);">
          <!-- 4 Language Selector Dropdown -->
          <select id="voice-lang-select" style="background:transparent; color:#f4ae25; border:none; font-size:12px; font-weight:700; padding:4px 6px; cursor:pointer; outline:none;">
            <option value="hi-IN" selected style="background:#0f172a; color:#ffffff;">🇮🇳 Hindi</option>
            <option value="en-IN" style="background:#0f172a; color:#ffffff;">🇬🇧 English</option>
            <option value="ml-IN" style="background:#0f172a; color:#ffffff;">🌴 Malayalam</option>
            <option value="te-IN" style="background:#0f172a; color:#ffffff;">🏛️ Telugu</option>
            <option value="ta-IN" style="background:#0f172a; color:#ffffff;">🪔 Tamil (தமிழ்)</option>
          </select>

          <!-- Mic Trigger Button -->
          <button id="voice-tutor-mic-btn" style="background:var(--accent-gold, #f4ae25); color:#0b281d; border:none; padding:8px 14px; border-radius:20px; font-size:13px; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:6px; transition:all 0.2s ease;">
            🎤 Bol kar Poochein
          </button>
        </div>
      `;

      document.body.appendChild(floatWrap);

      // Event Listeners for Controls
      const langSelect = floatWrap.querySelector("#voice-lang-select");
      langSelect.addEventListener("change", (e) => {
        setLanguage(e.target.value);
      });

      const playBtn = floatWrap.querySelector("#voice-tutor-play-btn");
      playBtn.addEventListener("click", () => resumeSpeaking());

      const pauseBtn = floatWrap.querySelector("#voice-tutor-pause-btn");
      pauseBtn.addEventListener("click", () => pauseSpeaking());

      const stopBtn = floatWrap.querySelector("#voice-tutor-stop-btn");
      stopBtn.addEventListener("click", () => stopSpeaking());

      const micBtn = floatWrap.querySelector("#voice-tutor-mic-btn");
      micBtn.addEventListener("click", () => {
        if (isSpeaking) {
          pauseSpeaking();
          return;
        }
        if (isListening) {
          stopListening();
          return;
        }

        const chosenLangConfig = LANGUAGE_CONFIG[currentLang];

        startListening(async (queryText) => {
          micBtn.innerHTML = "⚡ Soch rahe hain...";
          const statusText = document.getElementById("voice-tutor-status-text");
          if (statusText) statusText.textContent = `Answering in ${chosenLangConfig.aiName}...`;

          try {
            const token = localStorage.getItem("EklavyaX_token");
            const res = await fetch("/api/tutor/chat", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
              },
              body: JSON.stringify({
                message: `[Language: ${chosenLangConfig.aiName}] Question: ${queryText}`,
                target_language: chosenLangConfig.aiName,
              }),
            });

            if (res.ok) {
              const data = await res.json();
              const reply = data.reply || data.explanation || "Answer ready.";
              speakText(reply, { lang: currentLang });
            } else {
              speakText("Sorry, unable to connect right now. Please retry.", { lang: currentLang });
            }
          } catch (err) {
            speakText("Network connection issue. Please check backend.", { lang: currentLang });
          }
        });
      });
    }
  });

  return {
    startListening,
    stopListening,
    speakText,
    pauseSpeaking,
    resumeSpeaking,
    stopSpeaking,
    setLanguage,
    LANGUAGE_CONFIG,
  };
})();

window.VoiceTutor = VoiceTutor;
