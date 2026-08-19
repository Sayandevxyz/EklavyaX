/**
 * js/student_courses.js
 * ─────────────────────
 * Dynamic Course Catalog, Enrollment System, Lesson Player,
 * and Curriculum Syllabus Viewer for EklavyaX.
 */

const ALL_COURSES_CATALOG = {
  math: {
    id: "math",
    category: "math",
    icon: "fa-chart-line",
    title: "Mathematics & Coordinate Geometry",
    teacher: "Mr. Rajib Kumar",
    rating: "4.8/5",
    totalLessons: 24,
    completedLessons: 17,
    progress: 70,
    description: "Master polynomials, linear algebra, geometric proofs, and probability calculations.",
    currentLesson: {
      number: 18,
      title: "Linear Equations in Two Variables — Graphical Solutions",
      duration: "25 mins",
      summary: "Learn how to plot algebraic linear equations on a Cartesian coordinate plane and find intersection roots.",
      keyPoints: [
        "Standard form: ax + by + c = 0",
        "Every linear equation in two variables represents a straight line on the Cartesian plane.",
        "Intersection of two distinct lines gives the unique common solution (x, y)."
      ]
    },
    chapters: [
      { name: "Chapter 1: Number Systems & Real Numbers", lessons: 4, completed: true },
      { name: "Chapter 2: Polynomials & Algebraic Identities", lessons: 5, completed: true },
      { name: "Chapter 3: Coordinate Geometry", lessons: 4, completed: true },
      { name: "Chapter 4: Linear Equations in Two Variables", lessons: 4, completed: false, current: true },
      { name: "Chapter 5: Lines, Angles & Triangles", lessons: 4, completed: false },
      { name: "Chapter 6: Statistics & Probability", lessons: 3, completed: false }
    ]
  },
  english: {
    id: "english",
    category: "humanities",
    icon: "fa-book",
    title: "English Literature & Grammar",
    teacher: "Ms. Sunita Devi",
    rating: "4.9/5",
    totalLessons: 20,
    completedLessons: 17,
    progress: 85,
    description: "Analytical reading, poetic analysis, vocabulary building, and advanced essay composition.",
    currentLesson: {
      number: 18,
      title: "Poetry Analysis: The Road Not Taken by Robert Frost",
      duration: "20 mins",
      summary: "Explore symbolism, metaphorical paths of life, and rhyme scheme in Frost's masterpiece.",
      keyPoints: [
        "Rhyme Scheme: ABAAB",
        "Symbolism: The yellow wood represents life choices and diverging paths.",
        "Tone: Reflective and contemplative."
      ]
    },
    chapters: [
      { name: "Unit 1: The Fun They Had & The Road Not Taken", lessons: 5, completed: true },
      { name: "Unit 2: The Sound of Music & Wind", lessons: 5, completed: true },
      { name: "Unit 3: The Little Girl & Rain on the Roof", lessons: 5, completed: true },
      { name: "Unit 4: Advanced Grammar & Creative Writing", lessons: 5, completed: false, current: true }
    ]
  },
  science: {
    id: "science",
    category: "physics",
    icon: "fa-flask",
    title: "Science (Physics & Chemistry Core)",
    teacher: "Dr. Amit Singh",
    rating: "4.7/5",
    totalLessons: 30,
    completedLessons: 12,
    progress: 40,
    description: "Core physical science covering chemical reactions, atomic models, motion, and gravitational laws.",
    currentLesson: {
      number: 13,
      title: "Newton's Laws of Motion & Momentum Conservation",
      duration: "30 mins",
      summary: "Understand inertia, force equations F = ma, and interactive recoil velocities in collisions.",
      keyPoints: [
        "First Law: Law of Inertia (an object at rest remains at rest unless acted upon).",
        "Second Law: F = dp/dt = m * a.",
        "Third Law: For every action, there is an equal and opposite reaction."
      ],
      simUrl: "https://phet.colorado.edu/sims/html/forces-and-motion-basics/latest/forces-and-motion-basics_en.html"
    },
    chapters: [
      { name: "Physics Ch 1: Motion & Rate of Change", lessons: 6, completed: true },
      { name: "Physics Ch 2: Force & Laws of Motion", lessons: 6, completed: true },
      { name: "Physics Ch 3: Gravitation & Free Fall", lessons: 6, completed: false, current: true },
      { name: "Chemistry Ch 1: Matter in Our Surroundings", lessons: 6, completed: false },
      { name: "Chemistry Ch 2: Atoms and Molecules", lessons: 6, completed: false }
    ]
  },
  computer: {
    id: "computer",
    category: "tech",
    icon: "fa-laptop-code",
    title: "Computer Science & Python",
    teacher: "Mrs. Kavita Sharma",
    rating: "4.6/5",
    totalLessons: 18,
    completedLessons: 11,
    progress: 60,
    description: "Hands-on coding in Python, data structures, algorithm design, and computational thinking.",
    currentLesson: {
      number: 12,
      title: "Python Data Structures: Lists, Tuples, and Loops",
      duration: "25 mins",
      summary: "Hands-on coding session learning list indexing, slicing, for loops, and list comprehension in Python.",
      keyPoints: [
        "Lists are mutable ordered collections defined with square brackets [].",
        "Tuples are immutable sequences defined with parentheses ().",
        "Use 'for item in list:' to iterate seamlessly."
      ]
    },
    chapters: [
      { name: "Module 1: Basics of IT & Cyber Ethics", lessons: 4, completed: true },
      { name: "Module 2: Flowcharts & Computational Logic", lessons: 4, completed: true },
      { name: "Module 3: Python Variables & Conditionals", lessons: 4, completed: true },
      { name: "Module 4: Loops & Data Structures", lessons: 4, completed: false, current: true },
      { name: "Module 5: Mini Project & Quiz", lessons: 2, completed: false }
    ]
  },
  physics_adv: {
    id: "physics_adv",
    category: "physics",
    icon: "fa-atom",
    title: "Advanced Physics: Mechanics & Optics",
    teacher: "Mr. Aarav Singh",
    rating: "4.9/5",
    totalLessons: 28,
    completedLessons: 0,
    progress: 0,
    description: "Deep dive into rotational dynamics, wave optics, ray diagrams, and electromagnetic induction.",
    currentLesson: {
      number: 1,
      title: "Kinematics in Two Dimensions & Projectile Motion",
      duration: "35 mins",
      summary: "Analyze parabolic trajectories, time of flight, maximum height, and horizontal range.",
      keyPoints: [
        "Horizontal velocity component remains constant (ax = 0).",
        "Vertical acceleration is due to gravity (ay = -g).",
        "Time of Flight: T = (2 * u * sin(θ)) / g."
      ],
      simUrl: "https://phet.colorado.edu/sims/html/projectile-motion/latest/projectile-motion_en.html"
    },
    chapters: [
      { name: "Chapter 1: Kinematics & Projectile Vectors", lessons: 5, completed: false, current: true },
      { name: "Chapter 2: Work, Power & Energy Theorem", lessons: 6, completed: false },
      { name: "Chapter 3: Rotational Motion & Center of Mass", lessons: 6, completed: false },
      { name: "Chapter 4: Wave Optics & Interference", lessons: 5, completed: false },
      { name: "Chapter 5: Ray Optics & Lens Simulations", lessons: 6, completed: false }
    ]
  },
  chemistry_adv: {
    id: "chemistry_adv",
    category: "chemistry",
    icon: "fa-vial",
    title: "Organic Chemistry & Reaction Mechanisms",
    teacher: "Dr. Meera Patel",
    rating: "4.8/5",
    totalLessons: 25,
    completedLessons: 0,
    progress: 0,
    description: "Understand IUPAC nomenclature, isomerism, reaction mechanisms (SN1, SN2), and biomolecules.",
    currentLesson: {
      number: 1,
      title: "Structure & Hybridization of Carbon Compounds",
      duration: "30 mins",
      summary: "Understand sp3, sp2, and sp hybridization and tetrahedral molecular geometries.",
      keyPoints: [
        "Carbon exhibits tetravalency due to sp3 hybridization in alkanes.",
        "Sigma bonds form by head-on overlapping; pi bonds by lateral overlapping.",
        "Bond angle for sp3 is 109.5°."
      ]
    },
    chapters: [
      { name: "Module 1: General Organic Chemistry (GOC)", lessons: 5, completed: false, current: true },
      { name: "Module 2: Hydrocarbons (Alkanes, Alkenes, Alkynes)", lessons: 6, completed: false },
      { name: "Module 3: Haloalkanes & Substitution Reactions", lessons: 5, completed: false },
      { name: "Module 4: Alcohols, Phenols & Ethers", lessons: 5, completed: false },
      { name: "Module 5: Biomolecules & Polymers", lessons: 4, completed: false }
    ]
  },
  biology_adv: {
    id: "biology_adv",
    category: "biology",
    icon: "fa-dna",
    title: "Biology: Cell Biology, Genetics & Ecology",
    teacher: "Dr. Rajesh Sen",
    rating: "4.9/5",
    totalLessons: 26,
    completedLessons: 0,
    progress: 0,
    description: "Explore cellular architecture, DNA replication, Mendelian inheritance, and ecosystems.",
    currentLesson: {
      number: 1,
      title: "Cell Organelles: Structure and Function of Mitochondria",
      duration: "25 mins",
      summary: "Discover the powerhouse of the cell, ATP generation, and the electron transport chain.",
      keyPoints: [
        "Mitochondria possess their own double membrane and circular DNA.",
        "Cristae increase surface area for ATP synthase enzymes.",
        "Aerobic cellular respiration takes place inside the inner matrix."
      ]
    },
    chapters: [
      { name: "Unit 1: The Unit of Life — Cell Biology", lessons: 5, completed: false, current: true },
      { name: "Unit 2: Biomolecules & Cell Division (Mitosis/Meiosis)", lessons: 5, completed: false },
      { name: "Unit 3: Principles of Inheritance & Genetics", lessons: 6, completed: false },
      { name: "Unit 4: Molecular Basis of Inheritance", lessons: 5, completed: false },
      { name: "Unit 5: Ecology & Biodiversity Conservation", lessons: 5, completed: false }
    ]
  },
  robotics: {
    id: "robotics",
    category: "tech",
    icon: "fa-robot",
    title: "Robotics, IoT & Embedded Systems",
    teacher: "Prof. Priya Menon",
    rating: "4.9/5",
    totalLessons: 20,
    completedLessons: 0,
    progress: 0,
    description: "Build robotic circuits, program microcontrollers with Arduino/C++, and connect IoT sensors.",
    currentLesson: {
      number: 1,
      title: "Introduction to Microcontrollers & Sensor Interfacing",
      duration: "30 mins",
      summary: "Overview of microcontrollers, digital vs analog pins, and reading ultrasonic distance sensors.",
      keyPoints: [
        "Microcontrollers integrate CPU, memory, and programmable I/O pins.",
        "Analog inputs use ADC (Analog-to-Digital Converter) channels.",
        "Ultrasonic sensors measure distance using sound wave time-of-flight."
      ]
    },
    chapters: [
      { name: "Chapter 1: Circuit Foundations & Arduino IDE", lessons: 4, completed: false, current: true },
      { name: "Chapter 2: Sensor Interfacing & Actuators", lessons: 4, completed: false },
      { name: "Chapter 3: Motor Drivers & Autonomous Navigation", lessons: 4, completed: false },
      { name: "Chapter 4: Wireless Communication & IoT Cloud", lessons: 4, completed: false },
      { name: "Chapter 5: Capstone Autonomous Rover Project", lessons: 4, completed: false }
    ]
  },
  astronomy: {
    id: "astronomy",
    category: "physics",
    icon: "fa-user-astronaut",
    title: "Astronomy, Cosmology & Space Science",
    teacher: "Dr. Vikram Sarabhai Academy",
    rating: "4.9/5",
    totalLessons: 18,
    completedLessons: 0,
    progress: 0,
    description: "Journey through stellar evolution, black holes, orbital mechanics, and exoplanet exploration.",
    currentLesson: {
      number: 1,
      title: "Stellar Lifecycle: From Nebulae to Supernovae",
      duration: "25 mins",
      summary: "Learn how stars are born in molecular clouds and evolve into white dwarfs, neutron stars, or black holes.",
      keyPoints: [
        "Nuclear fusion of Hydrogen into Helium sustains main-sequence stars.",
        "Chandrasekhar Limit (1.44 Solar Masses) governs white dwarf stability.",
        "Supernovae disperse heavy elements across the cosmos."
      ],
      simUrl: "https://phet.colorado.edu/sims/html/gravity-and-orbits/latest/gravity-and-orbits_en.html"
    },
    chapters: [
      { name: "Module 1: The Solar System & Orbital Dynamics", lessons: 4, completed: false, current: true },
      { name: "Module 2: Stellar Physics & Spectroscopy", lessons: 4, completed: false },
      { name: "Module 3: Galaxies, Dark Matter & Big Bang", lessons: 4, completed: false },
      { name: "Module 4: Space Missions & Exoplanet Habitability", lessons: 6, completed: false }
    ]
  },
  ai_ml: {
    id: "ai_ml",
    category: "tech",
    icon: "fa-brain",
    title: "AI, Machine Learning & Neural Networks",
    teacher: "Dr. Ananya Mukherjee",
    rating: "4.9/5",
    totalLessons: 22,
    completedLessons: 0,
    progress: 0,
    description: "Practical introduction to computer vision, neural networks, NLP, and responsible AI.",
    currentLesson: {
      number: 1,
      title: "Fundamentals of Artificial Neural Networks (ANN)",
      duration: "30 mins",
      summary: "Understand perceptrons, activation functions (ReLU, Sigmoid), and forward propagation.",
      keyPoints: [
        "Neurons compute weighted sum of inputs plus bias: z = W*x + b.",
        "Non-linear activation functions allow learning complex boundaries.",
        "Backpropagation optimizes weights via Gradient Descent."
      ]
    },
    chapters: [
      { name: "Unit 1: Foundations of Machine Learning", lessons: 4, completed: false, current: true },
      { name: "Unit 2: Linear & Logistic Regression with Python", lessons: 5, completed: false },
      { name: "Unit 3: Deep Neural Networks & Backpropagation", lessons: 5, completed: false },
      { name: "Unit 4: Computer Vision & Convolutional Networks", lessons: 4, completed: false },
      { name: "Unit 5: Generative AI & Ethics in STEM", lessons: 4, completed: false }
    ]
  }
};

let activeCourseKey = null;

// ── Progress State Management (localStorage) ──────────────────────────────

function loadSavedCourseProgress() {
  try {
    const raw = localStorage.getItem("eklavya_courses_progress");
    if (raw) {
      const saved = JSON.parse(raw);
      Object.keys(saved).forEach(key => {
        if (ALL_COURSES_CATALOG[key]) {
          ALL_COURSES_CATALOG[key].completedLessons = saved[key].completedLessons ?? ALL_COURSES_CATALOG[key].completedLessons;
          ALL_COURSES_CATALOG[key].progress = saved[key].progress ?? ALL_COURSES_CATALOG[key].progress;
          if (saved[key].currentLessonNumber && ALL_COURSES_CATALOG[key].currentLesson) {
            ALL_COURSES_CATALOG[key].currentLesson.number = saved[key].currentLessonNumber;
          }
        }
      });
    }
  } catch (_) {}
}

function saveCourseProgress() {
  try {
    const progressMap = {};
    Object.keys(ALL_COURSES_CATALOG).forEach(key => {
      const c = ALL_COURSES_CATALOG[key];
      progressMap[key] = {
        completedLessons: c.completedLessons,
        progress: c.progress,
        currentLessonNumber: c.currentLesson ? c.currentLesson.number : 1
      };
    });
    localStorage.setItem("eklavya_courses_progress", JSON.stringify(progressMap));
  } catch (_) {}
}

// Load any previously saved progress immediately
loadSavedCourseProgress();

// ── Enrollment State Management ───────────────────────────────────────────

const DEFAULT_ENROLLED = ["math", "english", "science", "computer"];

function getEnrolledCourseIds() {
  const raw = localStorage.getItem("eklavya_enrolled_courses");
  if (!raw) {
    localStorage.setItem("eklavya_enrolled_courses", JSON.stringify(DEFAULT_ENROLLED));
    return DEFAULT_ENROLLED;
  }
  try {
    return JSON.parse(raw);
  } catch (_) {
    return DEFAULT_ENROLLED;
  }
}

function saveEnrolledCourseIds(ids) {
  localStorage.setItem("eklavya_enrolled_courses", JSON.stringify(ids));
}

function enrollInCourse(courseId) {
  const enrolled = getEnrolledCourseIds();
  if (enrolled.includes(courseId)) {
    if (window.EklavyaXPages && EklavyaXPages.showToast) {
      EklavyaXPages.showToast("You are already enrolled in this course!", "info-circle");
    }
    return;
  }

  enrolled.push(courseId);
  saveEnrolledCourseIds(enrolled);
  renderCoursesPage();

  const course = ALL_COURSES_CATALOG[courseId];
  const title = course ? course.title : "Course";
  if (window.EklavyaXPages && EklavyaXPages.showToast) {
    EklavyaXPages.showToast(`🎉 Enrolled in ${title}! +50 XP`, "award");
  } else {
    alert(`Enrolled in ${title} successfully!`);
  }
}

// ── Render Enrolled Courses & Catalog ─────────────────────────────────────

function renderCoursesPage() {
  const enrolledIds = getEnrolledCourseIds();
  const enrolledGrid = document.getElementById("enrolledCoursesGrid");
  const catalogGrid = document.getElementById("catalogCoursesGrid");
  const enrolledCountEl = document.getElementById("enrolledCountBadge");

  if (enrolledCountEl) {
    enrolledCountEl.textContent = `${enrolledIds.length} Active Courses`;
  }

  // 1. Render My Enrolled Courses
  if (enrolledGrid) {
    const enrolledCourses = enrolledIds.map(id => ALL_COURSES_CATALOG[id]).filter(Boolean);
    if (enrolledCourses.length === 0) {
      enrolledGrid.innerHTML = `
        <div style="grid-column: 1/-1; text-align:center; padding: 40px; color: var(--chalk-dim);">
          <i class="fas fa-graduation-cap" style="font-size: 2.2rem; margin-bottom: 12px; color: var(--marigold);"></i>
          <p>You haven't enrolled in any courses yet. Browse the catalog below and enroll with 1-click!</p>
        </div>
      `;
    } else {
      enrolledGrid.innerHTML = enrolledCourses.map(c => `
        <div class="course-card border-blue">
          <div class="course-header">
            <i class="fas ${c.icon || 'fa-book'} icon"></i>
            <div>
              <h3>${c.title}</h3>
              <p>${c.teacher}</p>
              <div class="meta">
                <span><i class="fas fa-clock"></i> ${c.totalLessons} lessons</span>
                <span><i class="fas fa-star"></i> ${c.rating}</span>
              </div>
            </div>
          </div>
          <div class="progress-info">
            <span>Progress: ${c.progress}%</span>
            <span>${c.completedLessons}/${c.totalLessons} lessons completed</span>
          </div>
          <div class="progress">
            <div class="progress-bar blue" style="width:${c.progress}%"></div>
          </div>
          <div class="actions">
            <button class="btn-primary" onclick="continueLearning('${c.id}')"><i class="fas fa-play"></i> Continue Learning</button>
            <button class="btn-secondary" onclick="viewCourseDetails('${c.id}')"><i class="fas fa-list-ul"></i> View Details</button>
          </div>
        </div>
      `).join("");
    }
  }

  // 2. Render Explore Course Catalog (Filterable)
  filterCatalog();
}

function filterCatalog() {
  const catalogGrid = document.getElementById("catalogCoursesGrid");
  if (!catalogGrid) return;

  const enrolledIds = getEnrolledCourseIds();
  const activeFilter = document.querySelector(".catalog-tab.active")?.getAttribute("data-cat") || "all";
  const searchVal = (document.getElementById("catalogSearch")?.value || "").toLowerCase();

  const allList = Object.values(ALL_COURSES_CATALOG);
  const filtered = allList.filter(c => {
    const matchesCat = (activeFilter === "all") || (c.category === activeFilter);
    const matchesSearch = c.title.toLowerCase().includes(searchVal) || c.teacher.toLowerCase().includes(searchVal) || c.description.toLowerCase().includes(searchVal);
    return matchesCat && matchesSearch;
  });

  if (filtered.length === 0) {
    catalogGrid.innerHTML = `
      <div style="grid-column: 1/-1; text-align:center; padding: 40px; color: var(--chalk-dim);">
        <i class="fas fa-search" style="font-size: 2rem; margin-bottom: 10px;"></i>
        <p>No courses found matching your filter criteria.</p>
      </div>
    `;
    return;
  }

  catalogGrid.innerHTML = filtered.map(c => {
    const isEnrolled = enrolledIds.includes(c.id);
    const badgeCategory = `badge-${c.category === 'tech' ? 'cs' : (c.category === 'humanities' ? 'math' : c.category)}`;

    return `
      <div class="catalog-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div style="display:flex; align-items:center; gap:12px;">
            <div class="catalog-icon"><i class="fas ${c.icon || 'fa-book'}"></i></div>
            <div>
              <span class="badge ${badgeCategory}">${c.category}</span>
              <h4 style="color:var(--chalk); font-size:1.05rem; font-weight:700; margin-top:4px;">${c.title}</h4>
            </div>
          </div>
        </div>
        
        <p style="font-size:0.85rem; color:var(--chalk-dim); line-height:1.5; margin:12px 0;">${c.description}</p>
        
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8rem; color:var(--marigold); margin-bottom:14px;">
          <span><i class="fas fa-chalkboard-teacher"></i> ${c.teacher}</span>
          <span><i class="fas fa-video"></i> ${c.totalLessons} Lessons</span>
          <span><i class="fas fa-star"></i> ${c.rating}</span>
        </div>

        <div>
          ${isEnrolled ? `
            <button class="btn-secondary" style="width:100%; border-color:#4ade80; color:#4ade80;" onclick="continueLearning('${c.id}')">
              <i class="fas fa-check-circle"></i> Enrolled — Resume
            </button>
          ` : `
            <button class="btn-primary" style="width:100%;" onclick="enrollInCourse('${c.id}')">
              <i class="fas fa-plus-circle"></i> Enroll in Subject
            </button>
          `}
        </div>
      </div>
    `;
  }).join("");
}

// ── Continue Learning Modal ───────────────────────────────────────────────

function continueLearning(courseKey) {
  const course = ALL_COURSES_CATALOG[courseKey];
  if (!course) return;

  activeCourseKey = courseKey;

  const modal = document.getElementById("lessonModal");
  const titleEl = document.getElementById("lessonCourseTitle");
  const lessonNumEl = document.getElementById("lessonNumberBadge");
  const lessonTitleEl = document.getElementById("lessonTitle");
  const summaryEl = document.getElementById("lessonSummary");
  const pointsEl = document.getElementById("lessonKeyPoints");
  const progressEl = document.getElementById("lessonCourseProgress");

  if (titleEl) titleEl.textContent = course.title;
  if (lessonNumEl) lessonNumEl.textContent = `Lesson ${course.currentLesson ? course.currentLesson.number : course.completedLessons + 1} of ${course.totalLessons}`;
  if (lessonTitleEl) lessonTitleEl.textContent = course.currentLesson ? course.currentLesson.title : "Module Lesson";
  if (summaryEl) summaryEl.textContent = course.currentLesson ? course.currentLesson.summary : "Complete interactive learning module and review key concepts.";
  if (progressEl) progressEl.textContent = `${course.progress}% Completed (${course.completedLessons}/${course.totalLessons} Lessons)`;

  if (pointsEl && course.currentLesson && course.currentLesson.keyPoints) {
    pointsEl.innerHTML = course.currentLesson.keyPoints
      .map(pt => `<li><i class="fas fa-check-circle" style="color:var(--marigold); margin-right:8px;"></i>${pt}</li>`)
      .join("");
  }

  const labActionBtn = document.getElementById("lessonLabBtn");
  if (labActionBtn) {
    if (course.currentLesson && course.currentLesson.simUrl) {
      labActionBtn.style.display = "inline-flex";
      labActionBtn.onclick = () => {
        window.location.href = "lab_simulation.html";
      };
    } else {
      labActionBtn.style.display = "none";
    }
  }

  if (modal) {
    modal.style.display = "flex";
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  if (window.EklavyaXAPI && EklavyaXAPI.recordActivity) {
    EklavyaXAPI.recordActivity().catch(() => {});
  }
}

function completeCurrentLesson() {
  const courseKey = activeCourseKey || "math";
  const course = ALL_COURSES_CATALOG[courseKey];

  if (course) {
    // Increment completed lessons
    if (course.completedLessons < course.totalLessons) {
      course.completedLessons += 1;
    }
    
    // Recalculate percentage
    course.progress = Math.min(100, Math.round((course.completedLessons / course.totalLessons) * 100));

    // Increment current lesson number if available
    if (course.currentLesson && course.currentLesson.number < course.totalLessons) {
      course.currentLesson.number += 1;
    }

    // Update chapter completion status dynamically
    let accumulated = 0;
    if (Array.isArray(course.chapters)) {
      course.chapters.forEach(ch => {
        accumulated += ch.lessons;
        if (course.completedLessons >= accumulated) {
          ch.completed = true;
          ch.current = false;
        } else if (course.completedLessons + ch.lessons >= accumulated) {
          ch.completed = false;
          ch.current = true;
        } else {
          ch.completed = false;
          ch.current = false;
        }
      });
    }

    // Save to localStorage
    saveCourseProgress();

    // Re-render UI
    renderCoursesPage();

    closeLessonModal();

    if (window.EklavyaXPages && EklavyaXPages.showToast) {
      EklavyaXPages.showToast(`🎉 Lesson completed! Progress updated to ${course.progress}% (${course.completedLessons}/${course.totalLessons} Lessons)! +20 XP awarded!`, "award");
    } else {
      alert(`Lesson completed! Progress is now ${course.progress}%. +20 XP awarded! 🎉`);
    }
  } else {
    closeLessonModal();
  }
}

function closeLessonModal() {
  const modal = document.getElementById("lessonModal");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

// ── View Course Details Modal ─────────────────────────────────────────────

function viewCourseDetails(courseKey) {
  const course = ALL_COURSES_CATALOG[courseKey];
  if (!course) return;

  const modal = document.getElementById("courseDetailsModal");
  const titleEl = document.getElementById("detailCourseTitle");
  const teacherEl = document.getElementById("detailTeacher");
  const statsEl = document.getElementById("detailStats");
  const chapterListEl = document.getElementById("detailChapterList");

  if (titleEl) titleEl.textContent = course.title;
  if (teacherEl) teacherEl.textContent = `Instructor: ${course.teacher} • Rating: ⭐ ${course.rating}`;
  if (statsEl) statsEl.textContent = `${course.completedLessons}/${course.totalLessons} Lessons Completed (${course.progress}%)`;

  if (chapterListEl) {
    chapterListEl.innerHTML = course.chapters.map((ch) => `
      <div style="display:flex; align-items:center; justify-content:space-between; padding:12px 14px; background:rgba(10,24,18,0.6); border-radius:10px; border-left:3px solid ${ch.completed ? '#4ade80' : (ch.current ? 'var(--marigold)' : 'rgba(255,255,255,0.2)')};">
        <div style="display:flex; align-items:center; gap:10px;">
          <i class="fas ${ch.completed ? 'fa-check-circle' : (ch.current ? 'fa-play-circle' : 'fa-lock')}" style="color:${ch.completed ? '#4ade80' : (ch.current ? 'var(--marigold)' : 'var(--chalk-dim)')}; font-size:1.1rem;"></i>
          <div>
            <strong style="color:var(--chalk); font-size:0.92rem;">${ch.name}</strong>
            <span style="display:block; font-size:0.78rem; color:var(--chalk-dim);">${ch.lessons} Modules</span>
          </div>
        </div>
        <span class="badge ${ch.completed ? 'badge-resolved' : (ch.current ? 'badge-cs' : 'badge-pending')}" style="font-size:0.75rem;">
          ${ch.completed ? 'Completed' : (ch.current ? 'In Progress' : 'Locked')}
        </span>
      </div>
    `).join("");
  }

  const resumeBtn = document.getElementById("detailResumeBtn");
  if (resumeBtn) {
    resumeBtn.onclick = () => {
      closeDetailsModal();
      continueLearning(courseKey);
    };
  }

  if (modal) {
    modal.style.display = "flex";
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function closeDetailsModal() {
  const modal = document.getElementById("courseDetailsModal");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

// ── Global Event Listeners & Tab Filters ───────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  renderCoursesPage();

  // Search input
  const searchInput = document.getElementById("catalogSearch");
  if (searchInput) {
    searchInput.addEventListener("input", filterCatalog);
  }

  // Catalog category filter buttons
  const catBtns = document.querySelectorAll(".catalog-tab");
  catBtns.forEach(btn => {
    btn.addEventListener("click", function() {
      catBtns.forEach(b => b.classList.remove("active"));
      this.classList.add("active");
      filterCatalog();
    });
  });
});

window.addEventListener("click", function(event) {
  const lessonModal = document.getElementById("lessonModal");
  const detailsModal = document.getElementById("courseDetailsModal");
  if (event.target === lessonModal) closeLessonModal();
  if (event.target === detailsModal) closeDetailsModal();
});

window.addEventListener("keydown", function(event) {
  if (event.key === "Escape") {
    closeLessonModal();
    closeDetailsModal();
  }
});
