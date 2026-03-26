import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getConversations, getStats, getEfficiency, deleteConversationsBatch } from "../services/api";

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
  const [selected, setSelected] = useState(new Set());
  const [selectMode, setSelectMode] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const [convRes, statsRes] = await Promise.all([
        getConversations(filter || undefined, search || undefined),
        getStats(),
      ]);
      setConversations(convRes.data);
      setStats(statsRes.data);
      try {
        const effRes = await getEfficiency();
        setEfficiency(effRes.data);
      } catch {
        // efficiency — не критично
      }
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

  const toggleSelect = (id, e) => {
    e.stopPropagation();
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === conversations.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(conversations.map((c) => c.id)));
    }
  };

  const handleDelete = async () => {
    if (selected.size === 0) return;
    const confirmed = window.confirm(
      `Удалить ${selected.size} диалог(ов)? Это действие необратимо.`
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await deleteConversationsBatch([...selected]);
      setSelected(new Set());
      await load();
    } catch (err) {
      console.error(err);
      alert("Ошибка при удалении");
    }
    setDeleting(false);
  };

  const exitSelectMode = () => {
    setSelectMode(false);
    setSelected(new Set());
  };

  return (
    <div className="conversations-page">
      <div className="page-header">
        <h2>Диалоги</h2>
        <div className="page-header-actions">
          {selectMode ? (
            <>
              <button className="btn-select-all" onClick={toggleSelectAll}>
                {selected.size === conversations.length ? "Снять все" : "Выбрать все"}
              </button>
              <button
                className="btn-delete"
                onClick={handleDelete}
                disabled={selected.size === 0 || deleting}
              >
                {deleting ? "Удаление..." : `Удалить (${selected.size})`}
              </button>
              <button className="btn-cancel" onClick={exitSelectMode}>
                Отмена
              </button>
            </>
          ) : (
            <>
              <button className="btn-select-mode" onClick={() => setSelectMode(true)}>
                Выбрать
              </button>
              <button className="btn-refresh" onClick={load}>
                Обновить
              </button>
            </>
          )}
        </div>
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
              className={`conversation-card${conv.status === "needs_operator" ? " needs-operator" : ""}${selected.has(conv.id) ? " selected" : ""}`}
              onClick={() => (selectMode ? toggleSelect(conv.id, { stopPropagation: () => {} }) : navigate(`/chat/${conv.id}`))}
            >
              <div className="conv-top">
                <div className="conv-top-left">
                  {selectMode && (
                    <input
                      type="checkbox"
                      className="conv-checkbox"
                      checked={selected.has(conv.id)}
                      onChange={(e) => toggleSelect(conv.id, e)}
                    />
                  )}
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
