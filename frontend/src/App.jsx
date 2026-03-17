import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate, Route, Routes, useNavigate, useLocation } from "react-router-dom";
import { getMe, getConversations } from "./services/api";
import LoginPage from "./pages/LoginPage";
import ConversationsPage from "./pages/ConversationsPage";
import ChatPage from "./pages/ChatPage";
import KnowledgePage from "./pages/KnowledgePage";

function PrivateRoute({ children }) {
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setChecking(false);
      return;
    }
    getMe()
      .then(() => setAuthenticated(true))
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setChecking(false));
  }, []);

  if (checking) return <p className="loading">Загрузка...</p>;
  if (!authenticated) return <Navigate to="/login" />;
  return children;
}

function playNotificationSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(880, ctx.currentTime);
    oscillator.frequency.setValueAtTime(660, ctx.currentTime + 0.1);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + 0.3);
  } catch (e) {
    // Web Audio API not available
  }
}

export default function App() {
  const [needsOperatorCount, setNeedsOperatorCount] = useState(0);
  const prevCountRef = useRef(0);
  const navigate = useNavigate();
  const location = useLocation();

  const isLoginPage = location.pathname === "/login";
  const isLoggedIn = !!localStorage.getItem("token");

  const handleLogout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };

  const pollNeedsOperator = useCallback(async () => {
    if (!localStorage.getItem("token")) return;
    try {
      const res = await getConversations("needs_operator");
      const count = res.data.length;
      if (count > prevCountRef.current) {
        playNotificationSound();
      }
      prevCountRef.current = count;
      setNeedsOperatorCount(count);
    } catch (e) {
      // ignore polling errors
    }
  }, []);

  useEffect(() => {
    pollNeedsOperator();
    const interval = setInterval(pollNeedsOperator, 10000);
    return () => clearInterval(interval);
  }, [pollNeedsOperator]);

  if (isLoginPage) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    );
  }

  return (
    <div className="app-layout">
      {isLoggedIn && (
        <aside className="sidebar">
          <div className="sidebar-brand" onClick={() => navigate("/")}>
            <div className="sidebar-logo">TA</div>
            <span className="sidebar-title">Ton Azure</span>
          </div>

          <nav className="sidebar-nav">
            <button
              className={`sidebar-link ${location.pathname === "/" || location.pathname.startsWith("/chat") ? "active" : ""}`}
              onClick={() => navigate("/")}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span>Диалоги</span>
              {needsOperatorCount > 0 && (
                <span className="sidebar-badge">{needsOperatorCount}</span>
              )}
            </button>

            <button
              className={`sidebar-link ${location.pathname === "/knowledge" ? "active" : ""}`}
              onClick={() => navigate("/knowledge")}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
              </svg>
              <span>База знаний</span>
            </button>
          </nav>

          <div className="sidebar-footer">
            <button className="sidebar-link sidebar-logout" onClick={handleLogout}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              <span>Выйти</span>
            </button>
          </div>
        </aside>
      )}

      <main className="main-content">
        <Routes>
          <Route
            path="/"
            element={
              <PrivateRoute>
                <ConversationsPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/chat/:id"
            element={
              <PrivateRoute>
                <ChatPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/knowledge"
            element={
              <PrivateRoute>
                <KnowledgePage />
              </PrivateRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
