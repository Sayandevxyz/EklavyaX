require("dotenv").config();
const express = require("express");
const cors = require("cors");
const path = require("path");
const fs = require("fs");

const { DB_PATH } = require("./src/db");
const { seed } = require("./src/utils/seed");

const authRoutes = require("./src/routes/auth");
const dashboardRoutes = require("./src/routes/dashboard");
const teacherRoutes = require("./src/routes/teacher");

// Seed the JSON "database" on first run so the app works out of the box.
if (!fs.existsSync(DB_PATH)) {
  seed();
}

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());

app.use("/api/auth", authRoutes);
app.use("/api/dashboard", dashboardRoutes);
app.use("/api/teacher", teacherRoutes);

app.get("/api/health", (req, res) => res.json({ ok: true }));

// Serve the static frontend (index.html, login.html, style.css, script.js)
app.use(express.static(path.join(__dirname, "public")));

app.listen(PORT, () => {
  console.log(`EklavyaX server running at http://localhost:${PORT}`);
});
