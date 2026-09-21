import { useEffect, useState } from "react";
import { clearSession, getLeaderboard, getProfile, getSession, getWallet, login, register, saveSession } from "./api";

const PORTALS = [
  { role: "student", title: "Student", detail: "Daily labs, quests, and a learning path that remembers your momentum.", accent: "gold" },
  { role: "teacher", title: "Teacher", detail: "See classroom signals, guide practice, and make feedback count.", accent: "terra" }
];

function navigate(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function App() {
  const [path, setPath] = useState(window.location.pathname);
  const [session, setSession] = useState(getSession());

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const updateSession = (nextSession) => {
    setSession(nextSession);
    if (nextSession.user) navigate(`/${nextSession.user.role}`);
  };

  if (path === "/login" || path === "/register") {
    return <AuthPage mode={path.slice(1)} onAuthenticated={updateSession} />;
  }

  if (path === "/student" || path === "/teacher") {
    const expectedRole = path.slice(1);
    if (!session.user || session.user.role !== expectedRole) {
      return <AuthPage mode="login" preferredRole={expectedRole} onAuthenticated={updateSession} />;
    }
    return <Dashboard user={session.user} onLogout={() => { clearSession(); setSession({ token: null, user: null }); navigate("/"); }} />;
  }

  if (/^\/(student|teacher)\/.+\.html$/.test(path)) {
    return <LegacyPage src={`/legacy${path}`} />;
  }

  return <Home onChoose={(role) => navigate(`/login?role=${role}`)} />;
}

function LegacyPage({ src }) {
  return (
    <div className="legacy-page">
      <iframe className="legacy-frame" title="EklavyaX learning page" src={src} />
    </div>
  );
}

function Shell({ children, compact = false }) {
  return (
    <div className={`react-shell${compact ? " compact" : ""}`}>
      <header className="react-nav">
        <button className="brand" onClick={() => navigate("/")} aria-label="Go to home">
          <span className="brand-mark">E</span>
          <span>Eklavya<span className="brand-x">X</span></span>
        </button>
        <div className="nav-note">STEM learning, with a little more intent.</div>
      </header>
      {children}
      <footer className="react-footer">EklavyaX <span>/</span> Learn boldly. Build patiently.</footer>
    </div>
  );
}

function Home({ onChoose }) {
  return (
    <Shell>
      <main className="home-layout">
        <section className="home-copy">
          <p className="eyebrow">THE GRAVITY LEARNING PLATFORM</p>
          <h1>Find your next <em>why.</em></h1>
          <p className="home-lede">A focused learning space for students and teachers who want curiosity to turn into visible progress.</p>
          <div className="home-actions">
            <button className="primary-button" onClick={() => onChoose("student")}>Enter the classroom <span>↗</span></button>
            <button className="text-button" onClick={() => onChoose("teacher")}>I teach here <span>→</span></button>
          </div>
        </section>
        <section className="portal-grid" aria-label="Choose a portal">
          <div className="orbit-line" />
          {PORTALS.map((portal, index) => (
            <button key={portal.role} className={`portal-card ${portal.accent}`} onClick={() => onChoose(portal.role)}>
              <span className="portal-number">0{index + 1}</span>
              <span className="portal-icon">{portal.role === "student" ? "✦" : "◒"}</span>
              <strong>{portal.title}</strong>
              <span>{portal.detail}</span>
              <small>Open portal <b>↗</b></small>
            </button>
          ))}
        </section>
      </main>
    </Shell>
  );
}

function AuthPage({ mode, preferredRole = "student", onAuthenticated }) {
  const [role, setRole] = useState(preferredRole);
  const [form, setForm] = useState({ username: "", email: "", password: "", gender: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const isRegister = mode === "register";

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = isRegister
        ? await register({ ...form, role })
        : await login(form.username, form.password);
      saveSession(result.access_token, result.user);
      onAuthenticated({ token: result.access_token, user: result.user });
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell compact>
      <main className="auth-layout">
        <section className="auth-intro">
          <p className="eyebrow">{isRegister ? "MAKE A PLACE FOR YOUR CURIOSITY" : "WELCOME BACK"}</p>
          <h1>{isRegister ? "Start with one good question." : "Pick up where you left off."}</h1>
          <p>{isRegister ? "Your learning path is built from small, repeatable acts of attention." : "Your next useful step is probably closer than it feels."}</p>
          <button className="back-link" onClick={() => navigate("/")}>← Back to portal selection</button>
        </section>
        <form className="auth-form" onSubmit={submit}>
          <div className="role-toggle">
            {PORTALS.map((portal) => <button type="button" key={portal.role} className={role === portal.role ? "active" : ""} onClick={() => setRole(portal.role)}>{portal.title}</button>)}
          </div>
          <label>Username<input required value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} autoComplete="username" /></label>
          {isRegister && <label>Email<input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} autoComplete="email" /></label>}
          <label>Password<input required type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} autoComplete={isRegister ? "new-password" : "current-password"} /></label>
          {isRegister && <label>Gender <select value={form.gender} onChange={(event) => setForm({ ...form, gender: event.target.value })}><option value="">Prefer not to say</option><option value="female">Female</option><option value="male">Male</option></select></label>}
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button form-submit" disabled={busy}>{busy ? "Working..." : isRegister ? "Create my account" : "Sign in"} <span>↗</span></button>
          <p className="form-switch">{isRegister ? "Already have an account?" : "New to EklavyaX?"} <button type="button" onClick={() => navigate(isRegister ? "/login" : "/register")}>{isRegister ? "Sign in" : "Create one"}</button></p>
        </form>
      </main>
    </Shell>
  );
}

function Dashboard({ user, onLogout }) {
  const [wallet, setWallet] = useState(null);
  const [leaders, setLeaders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([getWallet(), getLeaderboard()]).then(([walletResult, leaderboardResult]) => {
      if (walletResult.status === "fulfilled") setWallet(walletResult.value);
      if (leaderboardResult.status === "fulfilled") setLeaders(leaderboardResult.value?.leaderboard || leaderboardResult.value || []);
      setLoading(false);
    });
  }, []);

  return (
    <Shell compact>
      <main className="dashboard-layout">
        <section className="dashboard-heading"><p className="eyebrow">{user.role.toUpperCase()} / TODAY</p><h1>Good to see you, <em>{user.username || "learner"}.</em></h1><button className="back-link" onClick={onLogout}>Sign out ↗</button></section>
        <section className="metric-grid">
          <Metric label="EduCoins" value={loading ? "..." : wallet?.balance ?? "0"} detail="Keep your momentum" />
          <Metric label="Current streak" value={user.current_streak ?? "5"} detail="Days in a row" />
          <Metric label="Your role" value={user.role} detail="A path with purpose" />
        </section>
        <section className="dashboard-lower"><div className="focus-panel"><p className="eyebrow">NEXT MOVE</p><h2>{user.role === "teacher" ? "See where your class needs you." : "Turn one question into progress."}</h2><p>{user.role === "teacher" ? "Review your classroom signals and give the next useful nudge." : "Explore a lab, revisit a concept, or ask GRAVITY to explain the hard bit."}</p><button className="primary-button">Open learning space <span>↗</span></button></div><div className="rank-panel"><p className="eyebrow">CLASS SIGNAL</p>{leaders.slice(0, 4).map((leader, index) => <div className="rank-row" key={leader.id || leader.username || index}><span>0{index + 1}</span><strong>{leader.username || leader.name || "Learner"}</strong><b>{leader.xp ?? leader.score ?? "—"}</b></div>)}{!leaders.length && <p className="muted">Your class leaderboard will appear here.</p>}</div></section>
      </main>
    </Shell>
  );
}

function Metric({ label, value, detail }) {
  return <article className="metric-card"><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

export default App;
