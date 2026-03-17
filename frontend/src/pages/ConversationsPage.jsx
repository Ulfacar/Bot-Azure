import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getConversations, getStats, getEfficiency } from "../services/api";

const STATUS_LABELS = {
  in_progress: "В процессе",
  bot_completed: "Бот справился",
  needs_operator: "Нужен менеджер",
  operator_active: "Менеджер отвечает",
  closed: "Закрыт",
};

const STATUS_COLORS = {
  in_progress: "#3b82f6",
  bot_completed: "#22c55e",
  needs_operator: "#ef4444",
  operator_active: "#f59e0b",
  closed: "#6b7280",
};

const CATEGORY_LABELS = {
  booking: "Бронирование",
  hotel: "Номера",
  service: "Услуги",
  general: "Общий",
};

const FILTERS = [
  { value: "", label: "Все" },
  { value: "needs_operator", label: "Нужен менеджер" },
  { value: "in_progress", label: "В процессе" },
  { value: "bot_completed", label: "Бот справился" },
  { value: "operator_active", label: "Менеджер отвечает" },
  { value: "closed", label: "Закрытые" },
];

export default function ConversationsPage() {
  const [searchParams] = useSearchParams();
  const [conversations, setConversations] = useState([]);
  const [stats, setStats] = useState(null);
  const [efficiency, setEfficiency] = useState(null);
  const [filter, setFilter] = useState(searchParams.get("filter") || "");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const [convRes, statsRes, effRes] = await Promise.all([
        getConversations(filter || undefined, search || undefined),
        getStats(),
        getEfficiency(),
      ]);
      setConversations(convRes.data);
      setStats(statsRes.data);
      setEfficiency(effRes.data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [filter, search]);

  return (
    <div className="conversations-page">
      <div className="page-header">
        <h2>Диалоги</h2>
        <button className="btn-refresh" onClick={load}>
          Обновить
        </button>
      </div>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-number">{stats.today.total}</div>
            <div className="stat-label">Сегодня всего</div>
          </div>
          <div className="stat-card stat-bot">
            <div className="stat-number">{stats.today.bot_completed}</div>
            <div className="stat-label">Бот справился</div>
          </div>
          <div className="stat-card stat-operator">
            <div className="stat-number">{stats.today.needs_operator + stats.today.operator_active}</div>
            <div className="stat-label">Менеджер</div>
          </div>
          <div className="stat-card stat-all">
            <div className="stat-number">{stats.total.total}</div>
            <div className="stat-label">Всего диалогов</div>
          </div>
          <div className="stat-card stat-efficiency">
            <div className="stat-number">
              {efficiency ? efficiency.efficiency_percent : 0}%
            </div>
            <div className="stat-label">Эффективность бота</div>
            {efficiency && (
              <div className="stat-details">
                <span title="Уникальных клиентов">👤 {efficiency.unique_clients}</span>
                <span title="Среднее сообщений бота">💬 {efficiency.avg_bot_messages}</span>
              </div>
            )}
          </div>
        </div>
      )}

      <input
        className="search-input"
        type="text"
        placeholder="Поиск по имени клиента..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div className="filters">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            className={`filter-btn ${filter === f.value ? "active" : ""}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && conversations.length === 0 ? (
        <p className="loading">Загрузка...</p>
      ) : conversations.length === 0 ? (
        <p className="empty">Диалогов пока нет</p>
      ) : (
        <div className="conversation-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-card${conv.status === "needs_operator" ? " needs-operator" : ""}`}
              onClick={() => navigate(`/chat/${conv.id}`)}
            >
              <div className="conv-top">
                <div className="conv-top-left">
                  <span className="conv-client">
                    {conv.client?.name || conv.client?.username || `Клиент #${conv.client_id}`}
                  </span>
                  <span className={`conv-channel conv-channel--${conv.client?.channel === "whatsapp" ? "wa" : "tg"}`}>
                    {conv.client?.channel === "whatsapp" ? "📱 WhatsApp" : "✈️ Telegram"}
                  </span>
                </div>
                <span
                  className="conv-status"
                  style={{ background: STATUS_COLORS[conv.status] }}
                >
                  {STATUS_LABELS[conv.status]}
                </span>
              </div>
              <div className="conv-bottom">
                <span className="conv-category">
                  {CATEGORY_LABELS[conv.category]}
                </span>
                <span className="conv-date">
                  {new Date(conv.updated_at).toLocaleString("ru-RU")}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
