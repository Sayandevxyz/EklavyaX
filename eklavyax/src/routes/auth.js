const express = require("express");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { nanoid } = require("nanoid");
const { read, write } = require("../db");
const { JWT_SECRET } = require("../middleware/auth");

const router = express.Router();

function signToken(user) {
  return jwt.sign(
    { id: user.id, role: user.role, name: user.name, email: user.email },
    JWT_SECRET,
    { expiresIn: "7d" }
  );
}

function publicUser(user) {
  const { passwordHash, ...safe } = user;
  return safe;
}

// POST /api/auth/register
router.post("/register", (req, res) => {
  const { name, email, password, role } = req.body || {};

  if (!name || !email || !password || !role) {
    return res.status(400).json({ error: "name, email, password, and role are required." });
  }
  if (!["student", "teacher"].includes(role)) {
    return res.status(400).json({ error: "role must be 'student' or 'teacher'." });
  }
  if (password.length < 6) {
    return res.status(400).json({ error: "Password must be at least 6 characters." });
  }

  const db = read();
  const exists = db.users.some((u) => u.email.toLowerCase() === email.toLowerCase());
  if (exists) {
    return res.status(409).json({ error: "An account with that email already exists." });
  }

  const passwordHash = bcrypt.hashSync(password, 10);
  const base = {
    id: nanoid(),
    role,
    name,
    email,
    passwordHash,
  };

  const newUser =
    role === "student"
      ? {
          ...base,
          level: 1,
          levelTitle: "Amber Novice",
          xp: 0,
          xpNext: 500,
          accuracy: 0,
          coins: 0,
          streak: 0,
          lastActive: new Date().toISOString().slice(0, 10),
          continueLesson: null,
          tip: "Start your first lesson to get a personalised tip here.",
        }
      : { ...base, subject: "", institution: "" };

  db.users.push(newUser);
  write(db);

  const token = signToken(newUser);
  res.status(201).json({ token, user: publicUser(newUser) });
});

// POST /api/auth/login
router.post("/login", (req, res) => {
  const { email, password, role } = req.body || {};

  if (!email || !password) {
    return res.status(400).json({ error: "email and password are required." });
  }

  const db = read();
  const user = db.users.find((u) => u.email.toLowerCase() === (email || "").toLowerCase());

  if (!user || !bcrypt.compareSync(password, user.passwordHash)) {
    return res.status(401).json({ error: "Invalid email or password." });
  }

  if (role && user.role !== role) {
    return res
      .status(401)
      .json({ error: `That account is registered as a ${user.role}, not a ${role}.` });
  }

  const token = signToken(user);
  res.json({ token, user: publicUser(user) });
});

module.exports = router;
