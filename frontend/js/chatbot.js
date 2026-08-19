/**
 * EklavyaX — EklavyaXInteractive Floating Chatbot
 * Brand new dark-green and chalkboard styled assistant.
 */
(function initEklavyaChatbot() {
  // Ensure we don't inject multiple instances
  if (document.getElementById("eklavya-chat-widget")) return;

  // Insert CSS dynamically if not already linked
  if (!document.querySelector('link[href*="chatbot.css"]')) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    const isSubdir = window.location.pathname.includes("/student/") || window.location.pathname.includes("/teacher/");
    link.href = (isSubdir ? "../css/chatbot.css" : "css/chatbot.css") + "?v=2.1";
    document.head.appendChild(link);
  }

  // Pre-configured knowledge base for instant answers
  const KNOWLEDGE_BASE = [
    {
      keywords: ["what is EklavyaX", "about EklavyaX", "what is EklavyaX", "who is eklavya"],
      response: "🏹 **EklavyaX** is a gamified STEM learning platform for Smart India Hackathon 2026. Inspired by Eklavya, who mastered archery through sheer dedication, it bridges rural students and real teachers with interactive labs, streak rewards, EduCoins, and AI tutors!"
    },
    {
      keywords: ["login as student", "student login", "how do i log in as a student"],
      response: "🎓 To log in as a student, visit the **Student Login** page (`/student/student_login.html`). You can sign in with your username and password, or create a brand new account with 100 bonus EduCoins!"
    },
    {
      keywords: ["login as teacher", "teacher login", "how do i log in as a teacher"],
      response: "👨‍🏫 Teachers can log in at `/teacher/login.html` to manage student batches, post question bounties, track STEM assignment progress, and mentor rural learners."
    },
    {
      keywords: ["educoin", "coins", "wallet", "earn coins", "earn educoins"],
      response: "🪙 **EduCoins** are our virtual learning currency! You earn coins by maintaining daily study streaks, completing teacher bounties, and correctly answering quizzes. You can spend 10 coins on Gravity AI explanations and get 5 coins refunded when you master the concept!"
    },
    {
      keywords: ["streak", "daily streak", "streak star"],
      response: "🔥 Complete at least one lesson or simulation each day to build your **Daily Streak**. Higher streaks give bonus EduCoins and XP boosters!"
    },
    {
      keywords: ["lab", "simulation", "phet", "experiments"],
      response: "🔬 Check out the **Lab Simulations** section (`/student/lab_simulation.html`) for hands-on interactive PhET simulations in Physics, Chemistry, and Mathematics!"
    },
    {
      keywords: ["bounty", "bounties", "teacher bounty"],
      response: "📜 Teachers post **Bounties** with reward pools. Solve difficult STEM problems posted on the bounty board to claim coins and climb the leaderboard!"
    }
  ];

  // Create Widget DOM
  const widgetContainer = document.createElement("div");
  widgetContainer.id = "eklavya-chat-widget";
  widgetContainer.innerHTML = `
    <!-- Chat Window -->
    <div id="eklavyaChatWindow" class="eklavya-chat-window">
      <div class="eklavya-chat-header">
        <div class="eklavya-chat-header-title">
          <div class="bot-avatar"><i class="fas fa-robot"></i></div>
          <div>
            <h3>Gravity AI<span class="status-dot"></span></h3>
          </div>
        </div>
        <div class="eklavya-chat-header-actions">
          <button id="eklavyaCloseBtn" class="eklavya-chat-header-btn" title="Close"><i class="fas fa-times"></i></button>
        </div>
      </div>

      <div id="eklavyaChatBody" class="eklavya-chat-body">
        <div class="eklavya-msg bot">
          Namaste! 🙏 Welcome to <strong>Gravity AI</strong> – your gamified learning platform. How can I help you today 😊?
        </div>

        <div class="eklavya-chips" id="eklavyaChips">
          <button class="eklavya-chip" data-query="What is EklavyaX?">🏹 What is EklavyaX?</button>
          <button class="eklavya-chip" data-query="How do I earn EduCoins?">🪙 How do I earn EduCoins?</button>
          <button class="eklavya-chip" data-query="How do I start a Lab Simulation?">🔬 How do I start a Lab Simulation?</button>
          <button class="eklavya-chip" data-query="How do I log in as a student?">🎓 How do I log in as a student?</button>
        </div>
      </div>

      <div class="eklavya-chat-footer">
        <form id="eklavyaChatForm" class="eklavya-input-row">
          <input type="text" id="eklavyaChatInput" placeholder="Ask in English, தமிழ் or हिंदी..." autocomplete="off" />
          <button type="submit" class="eklavya-send-btn" title="Send"><i class="fas fa-paper-plane"></i></button>
        </form>
        <div class="eklavya-footer-credit">EklavyaX• Made for SIH 2026 by Team GravityX</div>
      </div>
    </div>

    <!-- Trigger Button -->
    <button id="eklavyaToggleBtn" class="eklavya-chat-btn" title="Chat withGRAVITY AI">
      <i class="fas fa-robot"></i>
    </button>
  `;

  document.body.appendChild(widgetContainer);

  const toggleBtn = document.getElementById("eklavyaToggleBtn");
  const closeBtn = document.getElementById("eklavyaCloseBtn");
  const chatWindow = document.getElementById("eklavyaChatWindow");
  const chatForm = document.getElementById("eklavyaChatForm");
  const chatInput = document.getElementById("eklavyaChatInput");
  const chatBody = document.getElementById("eklavyaChatBody");
  const chipsContainer = document.getElementById("eklavyaChips");

  // Toggle open/close
  toggleBtn.addEventListener("click", () => {
    chatWindow.classList.toggle("open");
    if (chatWindow.classList.contains("open")) {
      chatInput.focus();
    }
  });

  closeBtn.addEventListener("click", () => {
    chatWindow.classList.remove("open");
  });

  // Suggestion chips
  if (chipsContainer) {
    chipsContainer.addEventListener("click", (e) => {
      const chip = e.target.closest(".eklavya-chip");
      if (!chip) return;
      const query = chip.getAttribute("data-query");
      handleUserMessage(query);
    });
  }

  // Handle Form Submit
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    handleUserMessage(text);
    chatInput.value = "";
  });

  function appendMessage(sender, htmlContent) {
    const msg = document.createElement("div");
    msg.className = `eklavya-msg ${sender}`;
    msg.innerHTML = htmlContent;
    chatBody.appendChild(msg);
    chatBody.scrollTop = chatBody.scrollHeight;
    return msg;
  }

  async function handleUserMessage(query) {
    appendMessage("user", escapeHTML(query));

    // Typing indicator
    const typingMsg = appendMessage("bot", '<i class="fas fa-spinner fa-spin"></i> Thinking...');

    // 1. Check local knowledge base
    const lower = query.toLowerCase();
    const match = KNOWLEDGE_BASE.find(k => k.keywords.some(kw => lower.includes(kw)));

    if (match) {
      setTimeout(() => {
        typingMsg.innerHTML = match.response.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        chatBody.scrollTop = chatBody.scrollHeight;
      }, 400);
      return;
    }

    // 2. Try Synapse AI Tutor endpoint if authenticated
    try {
      if (window.EklavyaXAPI && typeof window.EklavyaXAPI.tutorExplain === "function" && window.EklavyaXAPI.isLoggedIn()) {
        const res = await window.EklavyaXAPI.tutorExplain(query, "English");
        typingMsg.innerHTML = res.explanation.replace(/\n/g, "<br/>");
      } else {
        typingMsg.innerHTML = `🤖 <strong>GRAVITY AI:</strong> I'm here to help you study! For deep step-by-step STEM explanations with your EduCoin wallet, open the <a href="/student/eklavya_ai.html" style="color:#eeb43e; font-weight:bold; text-decoration:underline;">EklavyaXTutor</a> page!`;
      }
    } catch (err) {
      typingMsg.innerHTML = `Namaste! I'm <strong>GRAVITY AI</strong>. Ask me about STEM subjects, your courses, lab experiments, or how to earn EduCoins!`;
    }
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag));
  }
})();
