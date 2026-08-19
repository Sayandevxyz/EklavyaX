const express = require("express");
const { read } = require("../db");
const { requireAuth, requireRole } = require("../middleware/auth");

const router = express.Router();

// GET /api/teacher/students — class roster with at-risk flags
router.get("/students", requireAuth, requireRole("teacher"), (req, res) => {
  const db = read();
  const students = db.users.filter((u) => u.role === "student");

  const roster = students.map((s) => ({
    id: s.id,
    name: s.name,
    level: s.level,
    accuracy: s.accuracy,
    streak: s.streak,
    lastActive: s.lastActive,
    continueLesson: s.continueLesson,
    atRisk: s.accuracy < 65 || s.streak === 0,
  }));

  res.json({
    totalStudents: roster.length,
    atRiskCount: roster.filter((r) => r.atRisk).length,
    averageAccuracy:
      roster.length === 0
        ? 0
        : Math.round(roster.reduce((sum, r) => sum + r.accuracy, 0) / roster.length),
    students: roster,
  });
});

module.exports = router;
