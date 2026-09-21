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

  // Floating Voice Tutor Widget Injection has been removed as requested


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
