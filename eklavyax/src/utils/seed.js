const bcrypt = require("bcryptjs");
const { nanoid } = require("nanoid");
const fs = require("fs");
const path = require("path");
const { DB_PATH } = require("../db");

function seed() {
  const passwordHash = bcrypt.hashSync("password123", 10);

  const students = [
    {
      id: nanoid(),
      role: "student",
      name: "Arjun Sharma",
      email: "arjun@EklavyaX.com",
      passwordHash,
      level: 12,
      levelTitle: "Indigo Sage",
      xp: 3420,
      xpNext: 5000,
      accuracy: 91,
      coins: 1240,
      streak: 14,
      lastActive: new Date().toISOString().slice(0, 10),
      continueLesson: { title: "Recursion & Dynamic Programming", progress: 60 },
      tip: "Review memoization before your next quiz.",
    },
    {
      id: nanoid(),
      role: "student",
      name: "Anika Rao",
      email: "anika@EklavyaX.com",
      passwordHash,
      level: 9,
      levelTitle: "Cyan Scholar",
      xp: 2110,
      xpNext: 3500,
      accuracy: 88,
      coins: 860,
      streak: 6,
      lastActive: new Date().toISOString().slice(0, 10),
      continueLesson: { title: "Quantum Mechanics Basics", progress: 35 },
      tip: "Revisit wave-particle duality before the next module.",
    },
    {
      id: nanoid(),
      role: "student",
      name: "Rishi Verma",
      email: "rishi@EklavyaX.com",
      passwordHash,
      level: 15,
      levelTitle: "Violet Architect",
      xp: 4890,
      xpNext: 5000,
      accuracy: 95,
      coins: 2010,
      streak: 21,
      lastActive: new Date().toISOString().slice(0, 10),
      continueLesson: { title: "Graph Algorithms", progress: 80 },
      tip: "You're close to leveling up — finish today's quiz.",
    },
    {
      id: nanoid(),
      role: "student",
      name: "Meera Iyer",
      email: "meera@EklavyaX.com",
      passwordHash,
      level: 4,
      levelTitle: "Amber Novice",
      xp: 420,
      xpNext: 1000,
      accuracy: 58,
      coins: 90,
      streak: 0,
      lastActive: "2026-08-01",
      continueLesson: { title: "Algebra Foundations", progress: 12 },
      tip: "Try a short daily session to rebuild your streak.",
    },
  ];

  const teachers = [
    {
      id: nanoid(),
      role: "teacher",
      name: "Prof. Kavitha",
      email: "kavitha@EklavyaX.com",
      passwordHash,
      subject: "Mathematics",
      institution: "NIT Trichy",
    },
  ];

  const users = [...students, ...teachers];

  const db = {
    users,
    lessons: [
      { id: nanoid(), title: "Recursion & Dynamic Programming", subject: "Computer Science" },
      { id: nanoid(), title: "Quantum Mechanics Basics", subject: "Physics" },
      { id: nanoid(), title: "Graph Algorithms", subject: "Computer Science" },
      { id: nanoid(), title: "Algebra Foundations", subject: "Mathematics" },
    ],
  };

  fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
  fs.writeFileSync(DB_PATH, JSON.stringify(db, null, 2), "utf-8");
  console.log("Seeded database at", DB_PATH);
  console.log("Demo logins (password: password123):");
  users.forEach((u) => console.log(`  ${u.role.padEnd(8)} ${u.email}`));
}

if (require.main === module) {
  seed();
}

module.exports = { seed };
