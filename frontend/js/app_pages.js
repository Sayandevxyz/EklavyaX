/**
 * js/app_pages.js
 * ───────────────
 * Interactive features and state handling for Doubts, Assignments,
 * Announcements, Content Library, and Settings pages in EklavyaX.
 */

const EklavyaXPages = (() => {

  // ── Initial Mock Data Seeds for Local Storage ───────────────────────────

  const INITIAL_DOUBTS = [
    {
      id: "d1",
      author: "Rahul Sharma",
      authorRole: "student",
      avatar: "../assets/img/student_boy.jpg",
      subject: "physics",
      title: "Why does the center of mass remain constant during elastic collisions?",
      body: "In a two-body elastic collision without external forces, why is the velocity of the center of mass conserved throughout the interaction?",
      time: "2 hours ago",
      upvotes: 12,
      upvoted: false,
      resolved: true,
      answers: [
        {
          author: "Aarav Singh",
          authorRole: "teacher",
          avatar: "../assets/img/teacher_male.jpg",
          text: "Since net external force \\(F_{ext} = 0\\), linear momentum \\(P = M v_{cm}\\) is conserved according to Newton's Second Law \\(F_{ext} = \\frac{dP}{dt}\\)."
        }
      ]
    },
    {
      id: "d2",
      author: "Ananya Roy",
      authorRole: "student",
      avatar: "../assets/img/student_girl.jpg",
      subject: "chemistry",
      title: "Difference between SN1 and SN2 reaction mechanisms?",
      body: "Could someone clarify when carbocation rearrangement occurs in nucleophilic substitution?",
      time: "5 hours ago",
      upvotes: 8,
      upvoted: false,
      resolved: false,
      answers: []
    },
    {
      id: "d3",
      author: "Sayan Mondal",
      authorRole: "student",
      avatar: "../assets/img/student_boy.jpg",
      subject: "math",
      title: "How to apply L'Hôpital's Rule to 0^0 indeterminate form?",
      body: "I am stuck taking natural logarithm on both sides before evaluating limit of x^x as x approaches 0.",
      time: "1 day ago",
      upvotes: 15,
      upvoted: true,
      resolved: true,
      answers: [
        {
          author: "Aarav Singh",
          authorRole: "teacher",
          avatar: "../assets/img/teacher_male.jpg",
          text: "Let \\(y = x^x\\), then \\(\\ln y = x \\ln x = \\frac{\\ln x}{1/x}\\). Now apply L'Hôpital's rule to evaluate \\(\\lim_{x\\to 0} \\ln y = 0\\), so \\(y \\to 1\\)."
        }
      ]
    }
  ];

  const INITIAL_ASSIGNMENTS = [
    {
      id: "a1",
      subject: "physics",
      title: "Kinematics & Rotational Motion Problem Set",
      teacher: "Aarav Singh",
      dueDate: "Tomorrow, 11:59 PM",
      points: 100,
      rewardCoins: 50,
      status: "pending",
      score: null,
      feedback: "",
      instructions: "Solve problems 1 through 15 from Chapter 4. Attach your step-by-step working."
    },
    {
      id: "a2",
      subject: "chemistry",
      title: "Organic Reaction Mechanisms Lab Report",
      teacher: "Dr. Meera Patel",
      dueDate: "24 Aug 2026",
      points: 50,
      rewardCoins: 30,
      status: "submitted",
      score: null,
      feedback: "",
      instructions: "Document observation of aldol condensation experiment conducted in simulation lab."
    },
    {
      id: "a3",
      subject: "math",
      title: "Definite Integrals & Area Under Curves",
      teacher: "Aarav Singh",
      dueDate: "15 Aug 2026",
      points: 100,
      rewardCoins: 50,
      status: "graded",
      score: "96 / 100",
      feedback: "Excellent work! Neat diagrams for integral limits.",
      instructions: "Calculate enclosed areas for parabolas and trigonometric functions."
    }
  ];

  const INITIAL_ANNOUNCEMENTS = [
    {
      id: "ann1",
      pinned: true,
      category: "academic",
      title: "📢 Physics Mid-Term Examination Schedule Released",
      author: "Mr. Aarav Singh (Physics Department)",
      date: "18 Aug 2026",
      content: "The Mid-Term theory & lab practical schedule for Class 11th Science is now live. Physics paper will take place on 28th August 10:00 AM."
    },
    {
      id: "ann2",
      pinned: false,
      category: "events",
      title: "🏆 National STEM Faction Wars Season 2 Begins!",
      author: "EklavyaX Admin",
      date: "16 Aug 2026",
      content: "Earn bonus EduCoins for your faction by completing daily lab simulations and solving peer challenges!"
    }
  ];

  const INITIAL_LIBRARY = [
    {
      id: "lib1",
      title: "Class 11 Physics Formula Handbook (PDF)",
      category: "notes",
      subject: "physics",
      size: "2.4 MB",
      uploader: "Aarav Singh",
      downloads: 142
    },
    {
      id: "lib2",
      title: "Interactive Optics & Light Simulation Guide",
      category: "lab",
      subject: "physics",
      size: "4.1 MB",
      uploader: "Aarav Singh",
      downloads: 98
    },
    {
      id: "lib3",
      title: "Organic Chemistry Reactions Cheatsheet",
      category: "notes",
      subject: "chemistry",
      size: "1.8 MB",
      uploader: "Dr. Meera Patel",
      downloads: 215
    }
  ];

  // Helper to load or seed local storage
  function getStorageItem(key, initialSeed) {
    const raw = localStorage.getItem(key);
    if (!raw) {
      localStorage.setItem(key, JSON.stringify(initialSeed));
      return initialSeed;
    }
    try {
      return JSON.parse(raw);
    } catch (_) {
      return initialSeed;
    }
  }

  function setStorageItem(key, val) {
    localStorage.setItem(key, JSON.stringify(val));
  }

  // Toast Helper
  function showToast(message, icon = "check-circle") {
    let container = document.querySelector(".toast-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `<i class="fas fa-${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  // ── Doubts Page Logic ───────────────────────────────────────────────────

  function initDoubtsPage(userRole) {
    const doubts = getStorageItem("eklavya_doubts", INITIAL_DOUBTS);
    renderDoubts(doubts, userRole);

    const searchInput = document.getElementById("doubtSearch");
    if (searchInput) {
      searchInput.addEventListener("input", () => filterDoubts(userRole));
    }

    const tabBtns = document.querySelectorAll(".tab-group .tab-btn");
    tabBtns.forEach(btn => {
      btn.addEventListener("click", function() {
        tabBtns.forEach(b => b.classList.remove("active"));
        this.classList.add("active");
        filterDoubts(userRole);
      });
    });

    const askForm = document.getElementById("askDoubtForm");
    if (askForm) {
      askForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const user = EklavyaXAPI.getUser() || { username: "Student", role: "student" };
        const newDoubt = {
          id: "d_" + Date.now(),
          author: EklavyaXAPI.displayName(user),
          authorRole: user.role,
          avatar: EklavyaXAPI.getAvatarUrl(user),
          subject: document.getElementById("doubtSubject").value,
          title: document.getElementById("doubtTitle").value,
          body: document.getElementById("doubtBody").value,
          time: "Just now",
          upvotes: 1,
          upvoted: true,
          resolved: false,
          answers: []
        };
        const currentDoubts = getStorageItem("eklavya_doubts", INITIAL_DOUBTS);
        currentDoubts.unshift(newDoubt);
        setStorageItem("eklavya_doubts", currentDoubts);
        closeModal("askDoubtModal");
        askForm.reset();
        renderDoubts(currentDoubts, userRole);
        showToast("Your doubt has been posted!");
      });
    }
  }

  function filterDoubts(userRole) {
    const doubts = getStorageItem("eklavya_doubts", INITIAL_DOUBTS);
    const query = (document.getElementById("doubtSearch")?.value || "").toLowerCase();
    const activeTab = document.querySelector(".tab-group .tab-btn.active")?.getAttribute("data-tab") || "all";
    const currentUser = EklavyaXAPI.getUser();

    const filtered = doubts.filter(d => {
      const matchesSearch = d.title.toLowerCase().includes(query) || d.body.toLowerCase().includes(query) || d.subject.toLowerCase().includes(query);
      if (!matchesSearch) return false;

      if (activeTab === "resolved") return d.resolved;
      if (activeTab === "pending") return !d.resolved;
      if (activeTab === "my") return d.author === EklavyaXAPI.displayName(currentUser);
      return true;
    });

    renderDoubts(filtered, userRole);
  }

  function renderDoubts(list, userRole) {
    const container = document.getElementById("doubtsList");
    if (!container) return;

    if (list.length === 0) {
      container.innerHTML = `<div class="doubt-card" style="text-align:center; padding: 40px; color: var(--chalk-dim);"><i class="fas fa-search" style="font-size: 2rem; margin-bottom: 10px;"></i><p>No doubts found matching your filter.</p></div>`;
      return;
    }

    container.innerHTML = list.map(d => {
      const subjectBadge = `badge-${d.subject.toLowerCase()}`;
      const statusBadge = d.resolved ? "badge-resolved" : "badge-pending";

      const answersHtml = d.answers.map(ans => `
        <div class="answers-section">
          <div class="answer-header">
            <i class="fas fa-check-circle"></i> Answered by ${ans.author}
          </div>
          <div class="answer-body">${ans.text}</div>
        </div>
      `).join("");

      const teacherAnswerAction = (userRole === "teacher" && !d.resolved) ? `
        <button class="btn-primary" style="padding: 5px 12px; font-size: 0.8rem;" onclick="EklavyaXPages.openAnswerModal('${d.id}')">
          <i class="fas fa-reply"></i> Answer Doubt
        </button>
      ` : "";

      return `
        <div class="doubt-card" id="doubt_${d.id}">
          <div class="doubt-header">
            <div class="author-meta">
              <img src="${d.avatar}" alt="${d.author}">
              <div class="author-info">
                <strong>${d.author}</strong>
                <span>${d.time}</span>
              </div>
            </div>
            <div style="display:flex; gap:8px;">
              <span class="badge ${subjectBadge}">${d.subject}</span>
              <span class="badge ${statusBadge}">${d.resolved ? "Resolved" : "Pending"}</span>
            </div>
          </div>
          <h3 class="doubt-title">${d.title}</h3>
          <p class="doubt-body">${d.body}</p>
          ${answersHtml}
          <div class="doubt-footer">
            <div class="doubt-actions">
              <button class="action-btn ${d.upvoted ? "active" : ""}" onclick="EklavyaXPages.toggleUpvote('${d.id}', '${userRole}')">
                <i class="fas fa-thumbs-up"></i> <span>${d.upvotes} Helpful</span>
              </button>
              <button class="action-btn">
                <i class="fas fa-comment"></i> <span>${d.answers.length} Answers</span>
              </button>
            </div>
            ${teacherAnswerAction}
          </div>
        </div>
      `;
    }).join("");

    const totalEl = document.getElementById("statTotalDoubts");
    const resEl = document.getElementById("statResolvedDoubts");
    const pendEl = document.getElementById("statPendingDoubts");
    if (totalEl) totalEl.textContent = list.length;
    if (resEl) resEl.textContent = list.filter(d => d.resolved).length;
    if (pendEl) pendEl.textContent = list.filter(d => !d.resolved).length;
  }

  function toggleUpvote(id, userRole) {
    const doubts = getStorageItem("eklavya_doubts", INITIAL_DOUBTS);
    const doubt = doubts.find(d => d.id === id);
    if (doubt) {
      if (doubt.upvoted) {
        doubt.upvotes--;
        doubt.upvoted = false;
      } else {
        doubt.upvotes++;
        doubt.upvoted = true;
      }
      setStorageItem("eklavya_doubts", doubts);
      renderDoubts(doubts, userRole);
    }
  }

  function openAnswerModal(doubtId) {
    document.getElementById("targetDoubtId").value = doubtId;
    openModal("answerDoubtModal");
  }

  function submitTeacherAnswer() {
    const doubtId = document.getElementById("targetDoubtId").value;
    const answerText = document.getElementById("teacherAnswerText").value;
    if (!answerText.trim()) return;

    const user = EklavyaXAPI.getUser() || { username: "Aarav Singh", role: "teacher" };
    const doubts = getStorageItem("eklavya_doubts", INITIAL_DOUBTS);
    const doubt = doubts.find(d => d.id === doubtId);
    if (doubt) {
      doubt.answers.push({
        author: EklavyaXAPI.displayName(user),
        authorRole: "teacher",
        avatar: EklavyaXAPI.getAvatarUrl(user),
        text: answerText
      });
      doubt.resolved = true;
      setStorageItem("eklavya_doubts", doubts);
      closeModal("answerDoubtModal");
      document.getElementById("teacherAnswerText").value = "";
      renderDoubts(doubts, "teacher");
      showToast("Answer published and doubt marked as resolved!");
    }
  }

  // ── Assignments Page Logic ──────────────────────────────────────────────

  function initAssignmentsPage(userRole) {
    const assignments = getStorageItem("eklavya_assignments", INITIAL_ASSIGNMENTS);
    renderAssignments(assignments, userRole);

    const tabBtns = document.querySelectorAll(".tab-group .tab-btn");
    tabBtns.forEach(btn => {
      btn.addEventListener("click", function() {
        tabBtns.forEach(b => b.classList.remove("active"));
        this.classList.add("active");
        filterAssignments(userRole);
      });
    });

    const createForm = document.getElementById("createAssignmentForm");
    if (createForm) {
      createForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const newAssign = {
          id: "a_" + Date.now(),
          subject: document.getElementById("assignSubject").value,
          title: document.getElementById("assignTitle").value,
          teacher: EklavyaXAPI.displayName(EklavyaXAPI.getUser()),
          dueDate: document.getElementById("assignDueDate").value,
          points: parseInt(document.getElementById("assignPoints").value) || 100,
          rewardCoins: parseInt(document.getElementById("assignCoins").value) || 50,
          status: "pending",
          score: null,
          feedback: "",
          instructions: document.getElementById("assignInstructions").value
        };
        const list = getStorageItem("eklavya_assignments", INITIAL_ASSIGNMENTS);
        list.unshift(newAssign);
        setStorageItem("eklavya_assignments", list);
        closeModal("createAssignmentModal");
        createForm.reset();
        renderAssignments(list, userRole);
        showToast("Assignment created and posted to class!");
      });
    }
  }

  function filterAssignments(userRole) {
    const assignments = getStorageItem("eklavya_assignments", INITIAL_ASSIGNMENTS);
    const activeTab = document.querySelector(".tab-group .tab-btn.active")?.getAttribute("data-tab") || "all";

    const filtered = assignments.filter(a => {
      if (activeTab === "pending") return a.status === "pending";
      if (activeTab === "submitted") return a.status === "submitted";
      if (activeTab === "graded") return a.status === "graded";
      return true;
    });

    renderAssignments(filtered, userRole);
  }

  function renderAssignments(list, userRole) {
    const container = document.getElementById("assignmentsGrid");
    if (!container) return;

    if (list.length === 0) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding: 40px; color: var(--chalk-dim);"><i class="fas fa-folder-open" style="font-size: 2rem; margin-bottom: 10px;"></i><p>No assignments found under this filter.</p></div>`;
      return;
    }

    container.innerHTML = list.map(a => {
      let statusBadgeClass = "badge-pending";
      let statusText = "Pending";
      if (a.status === "submitted") { statusBadgeClass = "badge-cs"; statusText = "Submitted"; }
      if (a.status === "graded") { statusBadgeClass = "badge-resolved"; statusText = "Graded"; }

      let actionBtn = "";
      if (userRole === "student") {
        if (a.status === "pending") {
          actionBtn = `<button class="btn-primary" style="width:100%;" onclick="EklavyaXPages.openSubmitModal('${a.id}')"><i class="fas fa-upload"></i> Submit Solution</button>`;
        } else if (a.status === "graded") {
          actionBtn = `<div style="background: rgba(34,197,94,0.15); color:#4ade80; padding:10px; border-radius:8px; font-weight:700; text-align:center;">Score: ${a.score}</div>`;
        } else {
          actionBtn = `<button class="btn-secondary" style="width:100%;" disabled><i class="fas fa-clock"></i> Awaiting Grading</button>`;
        }
      } else {
        actionBtn = `<button class="btn-primary" style="width:100%;" onclick="EklavyaXPages.openGradeModal('${a.id}')"><i class="fas fa-edit"></i> Grade / View</button>`;
      }

      return `
        <div class="assignment-card">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="badge badge-${a.subject.toLowerCase()}">${a.subject}</span>
              <span class="badge ${statusBadgeClass}">${statusText}</span>
            </div>
            <h3 class="assignment-title">${a.title}</h3>
            <div class="assignment-meta" style="margin-top:12px;">
              <span><i class="fas fa-user-circle"></i> ${a.teacher}</span>
              <span><i class="fas fa-calendar-alt"></i> Due: ${a.dueDate}</span>
              <span class="assignment-reward"><i class="fas fa-coins"></i> +${a.rewardCoins} EduCoins</span>
            </div>
          </div>
          <div>
            ${actionBtn}
          </div>
        </div>
      `;
    }).join("");
  }

  function openSubmitModal(id) {
    document.getElementById("submitAssignId").value = id;
    openModal("submitAssignmentModal");
  }

  function submitAssignmentWork() {
    const id = document.getElementById("submitAssignId").value;
    const text = document.getElementById("submissionText").value;
    if (!text.trim()) return;

    const list = getStorageItem("eklavya_assignments", INITIAL_ASSIGNMENTS);
    const assign = list.find(a => a.id === id);
    if (assign) {
      assign.status = "submitted";
      setStorageItem("eklavya_assignments", list);
      closeModal("submitAssignmentModal");
      document.getElementById("submissionText").value = "";
      renderAssignments(list, "student");
      showToast("Assignment submitted successfully! +10 XP earned", "award");
    }
  }

  function openGradeModal(id) {
    document.getElementById("gradeAssignId").value = id;
    openModal("gradeAssignmentModal");
  }

  function submitGrade() {
    const id = document.getElementById("gradeAssignId").value;
    const score = document.getElementById("gradeScore").value;
    const feedback = document.getElementById("gradeFeedback").value;

    const list = getStorageItem("eklavya_assignments", INITIAL_ASSIGNMENTS);
    const assign = list.find(a => a.id === id);
    if (assign) {
      assign.status = "graded";
      assign.score = score;
      assign.feedback = feedback;
      setStorageItem("eklavya_assignments", list);
      closeModal("gradeAssignmentModal");
      renderAssignments(list, "teacher");
      showToast("Grade and feedback saved!");
    }
  }

  // ── Announcements Page Logic ─────────────────────────────────────────────

  function initAnnouncementsPage(userRole) {
    const ann = getStorageItem("eklavya_announcements", INITIAL_ANNOUNCEMENTS);
    renderAnnouncements(ann, userRole);

    const postForm = document.getElementById("postAnnouncementForm");
    if (postForm) {
      postForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const newAnn = {
          id: "ann_" + Date.now(),
          pinned: document.getElementById("annPinned").checked,
          category: document.getElementById("annCategory").value,
          title: document.getElementById("annTitle").value,
          author: EklavyaXAPI.displayName(EklavyaXAPI.getUser()),
          date: new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }),
          content: document.getElementById("annContent").value
        };
        const list = getStorageItem("eklavya_announcements", INITIAL_ANNOUNCEMENTS);
        if (newAnn.pinned) list.unshift(newAnn); else list.push(newAnn);
        setStorageItem("eklavya_announcements", list);
        closeModal("postAnnouncementModal");
        postForm.reset();
        renderAnnouncements(list, userRole);
        showToast("Announcement published!");
      });
    }
  }

  function renderAnnouncements(list, userRole) {
    const container = document.getElementById("announcementsFeed");
    if (!container) return;

    if (list.length === 0) {
      container.innerHTML = `<div class="announcement-card" style="text-align:center; padding: 40px; color: var(--chalk-dim);"><p>No announcements at this time.</p></div>`;
      return;
    }

    container.innerHTML = list.map(a => `
      <div class="announcement-card ${a.pinned ? "pinned" : ""}">
        ${a.pinned ? `<div class="pinned-tag"><i class="fas fa-thumbtack"></i> Pinned</div>` : ""}
        <div class="announcement-header">
          <span class="badge badge-cs">${a.category}</span>
          <span style="font-size: 0.85rem; color: var(--chalk-dim);">${a.date} • ${a.author}</span>
        </div>
        <h3 class="announcement-title">${a.title}</h3>
        <p class="announcement-content" style="margin-top: 10px;">${a.content}</p>
      </div>
    `).join("");
  }

  // ── Content Library Logic ───────────────────────────────────────────────

  function initContentLibraryPage() {
    const items = getStorageItem("eklavya_library", INITIAL_LIBRARY);
    renderLibrary(items);

    const uploadForm = document.getElementById("uploadResourceForm");
    if (uploadForm) {
      uploadForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const newItem = {
          id: "lib_" + Date.now(),
          title: document.getElementById("resTitle").value,
          category: document.getElementById("resCategory").value,
          subject: document.getElementById("resSubject").value,
          size: "3.2 MB",
          uploader: EklavyaXAPI.displayName(EklavyaXAPI.getUser()),
          downloads: 1
        };
        const list = getStorageItem("eklavya_library", INITIAL_LIBRARY);
        list.unshift(newItem);
        setStorageItem("eklavya_library", list);
        closeModal("uploadResourceModal");
        uploadForm.reset();
        renderLibrary(list);
        showToast("Resource uploaded to Content Library!");
      });
    }
  }

  function renderLibrary(list) {
    const container = document.getElementById("libraryGrid");
    if (!container) return;

    container.innerHTML = list.map(item => `
      <div class="resource-card">
        <div class="resource-icon">
          <i class="fas fa-file-pdf"></i>
        </div>
        <div>
          <span class="badge badge-${item.subject}">${item.subject}</span>
          <h4 class="resource-title" style="margin-top: 6px;">${item.title}</h4>
          <p style="font-size: 0.8rem; color: var(--chalk-dim); margin-top: 4px;">By ${item.uploader} • ${item.size}</p>
        </div>
        <button class="btn-secondary" style="margin-top: auto; font-size: 0.85rem;" onclick="EklavyaXPages.showToast('Downloading resource...')">
          <i class="fas fa-download"></i> Download (${item.downloads})
        </button>
      </div>
    `).join("");
  }

  // ── Settings Page Logic ─────────────────────────────────────────────────

  async function initSettingsPage(userRole) {
    let user = EklavyaXAPI.getUser() || {};
    
    // Refresh latest user data from backend if logged in
    if (EklavyaXAPI.isLoggedIn() && EklavyaXAPI.me) {
      try {
        const freshUser = await EklavyaXAPI.me();
        if (freshUser) {
          user = freshUser;
          EklavyaXAPI.saveSession(EklavyaXAPI.getToken(), freshUser);
        }
      } catch (_) {}
    }
    
    // Tab switching for settings nav
    const navButtons = document.querySelectorAll(".settings-nav-btn");
    const panelTabs = document.querySelectorAll(".settings-panel-tab");

    navButtons.forEach(btn => {
      btn.addEventListener("click", function() {
        navButtons.forEach(b => b.classList.remove("active"));
        this.classList.add("active");

        const targetId = this.getAttribute("data-target");
        panelTabs.forEach(tab => {
          if (tab.id === targetId || tab.getAttribute("id") === targetId || tab.getAttribute("data-panel") === targetId) {
            tab.style.display = "flex";
          } else {
            tab.style.display = "none";
          }
        });
      });
    });

    // Populate all user details
    const nameInput = document.getElementById("settingName");
    const emailInput = document.getElementById("settingEmail");
    const phoneInput = document.getElementById("settingPhone");
    const genderInput = document.getElementById("settingGender");
    const rollInput = document.getElementById("settingRoll");
    const gradeInput = document.getElementById("settingGrade");
    const schoolInput = document.getElementById("settingSchool");
    const examInput = document.getElementById("settingTargetExam");
    const bioInput = document.getElementById("settingBio");

    if (nameInput) nameInput.value = user.username || EklavyaXAPI.displayName(user) || (userRole === "teacher" ? "Aarav Singh" : "Sayan Mondal");
    if (emailInput) emailInput.value = user.email || (userRole === "teacher" ? "teacher@eklavyax.edu" : "sayanmondal@gmail.com");
    if (phoneInput) phoneInput.value = user.phone || "";
    if (genderInput) genderInput.value = (user.gender === "female" || user.gender === "girl") ? "female" : "male";
    if (rollInput) rollInput.value = user.roll || "";
    if (gradeInput) gradeInput.value = user.grade || "";
    if (schoolInput) schoolInput.value = user.school || "";
    if (examInput && user.target_exam) examInput.value = user.target_exam;
    if (bioInput) bioInput.value = user.bio || "";

    // Avatar picker interactive logic
    const currentAvatarUrl = EklavyaXAPI.getAvatarUrl(user);
    const currentFilename = currentAvatarUrl.split("/").pop().split("\\").pop();
    const avatarOptions = document.querySelectorAll(".avatar-option");

    avatarOptions.forEach(opt => {
      const optAvatar = opt.getAttribute("data-avatar");
      if (optAvatar && currentFilename.includes(optAvatar)) {
        avatarOptions.forEach(o => o.classList.remove("selected"));
        opt.classList.add("selected");
      }

      opt.addEventListener("click", function() {
        avatarOptions.forEach(o => o.classList.remove("selected"));
        this.classList.add("selected");
        
        // Auto sync gender selector if available
        const selectedGender = this.getAttribute("data-gender");
        if (selectedGender && genderInput) {
          genderInput.value = selectedGender;
        }
      });
    });

    if (genderInput) {
      genderInput.addEventListener("change", function() {
        const val = this.value;
        avatarOptions.forEach(opt => {
          if (opt.getAttribute("data-gender") === val) {
            avatarOptions.forEach(o => o.classList.remove("selected"));
            opt.classList.add("selected");
          }
        });
      });
    }

    async function saveProfile() {
      const currentUser = EklavyaXAPI.getUser() || {};
      const selectedAvatarEl = document.querySelector(".avatar-option.selected");
      const avatarFilename = selectedAvatarEl?.getAttribute("data-avatar") || (userRole === "teacher" ? "teacher_male.jpg" : "student_boy.jpg");
      const selectedGender = selectedAvatarEl?.getAttribute("data-gender") || (genderInput ? genderInput.value : "male");

      const nameVal = document.getElementById("settingName")?.value?.trim() || currentUser.username || "User";
      const emailVal = document.getElementById("settingEmail")?.value?.trim() || currentUser.email || "";
      const phoneVal = phoneInput ? phoneInput.value.trim() : currentUser.phone || "";
      const rollVal = rollInput ? rollInput.value.trim() : currentUser.roll || "";
      const gradeVal = gradeInput ? gradeInput.value.trim() : currentUser.grade || "";
      const schoolVal = schoolInput ? schoolInput.value.trim() : currentUser.school || "";
      const examVal = examInput ? examInput.value : currentUser.target_exam || "";
      const bioVal = bioInput ? bioInput.value.trim() : currentUser.bio || "";
      const avatarVal = `assets/img/${avatarFilename}`;

      const updatePayload = {
        username: nameVal,
        email: emailVal,
        gender: selectedGender,
        avatar_url: avatarVal,
        phone: phoneVal,
        roll: rollVal,
        grade: gradeVal,
        school: schoolVal,
        target_exam: examVal,
        bio: bioVal
      };

      const saveBtn = document.getElementById("saveProfileBtn");
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Saving...`;
      }

      try {
        let savedUser = null;
        if (EklavyaXAPI.isLoggedIn() && EklavyaXAPI.updateProfile) {
          savedUser = await EklavyaXAPI.updateProfile(updatePayload);
        }

        const mergedUser = {
          ...currentUser,
          ...(savedUser || updatePayload),
          username: nameVal,
          email: emailVal,
          gender: selectedGender,
          avatar_url: avatarVal,
          phone: phoneVal,
          roll: rollVal,
          grade: gradeVal,
          school: schoolVal,
          target_exam: examVal,
          bio: bioVal
        };

        // Persist to localStorage session
        EklavyaXAPI.saveSession(EklavyaXAPI.getToken() || "session_token", mergedUser);

        // Update header & sidebar UI in real-time
        const nameEl = document.getElementById("profileName");
        const welcomeEl = document.getElementById("welcomeName");
        if (nameEl) nameEl.textContent = EklavyaXAPI.displayName(mergedUser);
        if (welcomeEl) welcomeEl.textContent = EklavyaXAPI.displayName(mergedUser).split(" ")[0] || mergedUser.username;
        
        // Immediately apply avatar across all page images
        EklavyaXAPI.applyUserAvatar(mergedUser);

        showToast("Profile & avatar updated across platform!", "user-check");
      } catch (err) {
        showToast(err.message || "Failed to update profile", "exclamation-triangle");
      } finally {
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = `<i class="fas fa-save"></i> ${userRole === "teacher" ? "Save Settings" : "Save Changes"}`;
        }
      }
    }

    // Profile Settings Form Submit & Button Click
    const profileForm = document.getElementById("profileSettingsForm");
    if (profileForm) {
      profileForm.addEventListener("submit", (e) => {
        e.preventDefault();
        saveProfile();
      });
    }

    const saveBtn = document.getElementById("saveProfileBtn");
    if (saveBtn) {
      saveBtn.addEventListener("click", (e) => {
        e.preventDefault();
        saveProfile();
      });
    }

    // Notifications Form Submit
    const notifForm = document.getElementById("notifSettingsForm");
    if (notifForm) {
      notifForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const prefs = {
          doubts: document.getElementById("notifDoubt")?.checked ?? true,
          assignments: document.getElementById("notifAssign")?.checked ?? true,
          announcements: document.getElementById("notifAnn")?.checked ?? true,
          streak: document.getElementById("notifStreak")?.checked ?? true
        };
        localStorage.setItem("eklavya_notifs", JSON.stringify(prefs));
        showToast("Notification preferences saved successfully!", "bell");
      });
    }

    // Security Form Submit
    const secForm = document.getElementById("securitySettingsForm");
    if (secForm) {
      secForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const currP = document.getElementById("currPass")?.value;
        const newP = document.getElementById("newPass")?.value;
        const confP = document.getElementById("confirmPass")?.value;
        if (newP !== confP) {
          showToast("New passwords do not match!", "exclamation-triangle");
          return;
        }
        if (newP.length < 6) {
          showToast("Password must be at least 6 characters!", "exclamation-triangle");
          return;
        }

        const submitBtn = secForm.querySelector("button[type='submit']");
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Updating...`;
        }

        try {
          if (EklavyaXAPI.isLoggedIn() && EklavyaXAPI.changePassword) {
            await EklavyaXAPI.changePassword({ current_password: currP, new_password: newP });
          }
          secForm.reset();
          showToast("Password updated securely!", "lock");
        } catch (err) {
          showToast(err.message || "Failed to update password", "exclamation-triangle");
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fas fa-key"></i> Update Password`;
          }
        }
      });
    }
  }

  // Modal helpers
  function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add("active");
  }

  function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove("active");
  }

  return {
    initDoubtsPage,
    toggleUpvote,
    openAnswerModal,
    submitTeacherAnswer,

    initAssignmentsPage,
    openSubmitModal,
    submitAssignmentWork,
    openGradeModal,
    submitGrade,

    initAnnouncementsPage,
    initContentLibraryPage,
    initSettingsPage,

    openModal,
    closeModal,
    showToast
  };
})();
