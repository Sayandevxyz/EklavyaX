const express = require("express");
const { read, write } = require("../db");
const { requireAuth, requireRole } = require("../middleware/auth");

const router = express.Router();

// GET /api/dashboard/me — current student's dashboard stats
router.get("/me", requireAuth, requireRole("student"), (req, res) => {
  const db = read();
  const user = db.users.find((u) => u.id === req.user.id);
  if (!user) return res.status(404).json({ error: "User not found." });

  const { passwordHash, ...safe } = user;
  res.json(safe);
});

// POST /api/dashboard/progress — bump XP / lesson progress (demo mutation)
router.post("/progress", requireAuth, requireRole("student"), (req, res) => {
  const { xpGained = 0, lessonProgress } = req.body || {};

  const db = read();
  const user = db.users.find((u) => u.id === req.user.id);
  if (!user) return res.status(404).json({ error: "User not found." });

  if (xpGained > 0) {
    user.xp += xpGained;
    user.coins += Math.round(xpGained / 10);
    while (user.xp >= user.xpNext) {
      user.xp -= user.xpNext;
      user.level += 1;
      user.xpNext = Math.round(user.xpNext * 1.25);
    }
  }

  if (lessonProgress && user.continueLesson) {
    user.continueLesson.progress = Math.min(100, lessonProgress);
  }

  user.lastActive = new Date().toISOString().slice(0, 10);

  write(db);
  const { passwordHash, ...safe } = user;
  res.json(safe);
});

module.exports = router;
