import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getConversation,
  getConversations,
  getMessages,
  sendMessage,
  updateConversation,
  getTrainSuggestion,
  trainFromConversation,
  getNotesByClient,
  createNote,
  deleteNote,
} from "../services/api";

const STATUS_LABELS = {
  in_progress: "В процессе",
  bot_completed: "Бот справился",
  needs_operator: "Нужен менеджер",
  operator_active: "Менеджер отвечает",
  closed: "Закрыт",
};

const SENDER_LABELS = {
  client: "Клиент",
  bot: "Бот",
  operator: "Менеджер",
};

const QUICK_TEMPLATES = [
  {
    key: "payment",
    label: "💰 Реквизиты",
    text:
      "💰 Реквизиты для оплаты:\n\n" +
      "[РЕКВИЗИТЫ]\n\n" +
      "После оплаты, пожалуйста, пришлите скриншот или чек — " +
      "и мы подтвердим бронирование 😊",
  },
  {
    key: "confirmed",
    label: "✅ Подтверждена",
    text:
      "Отличная новость — ваша бронь подтверждена! ✅\n\n" +
      "Мы будем рады видеть вас в Тон Азур. " +
      "Если появятся вопросы до заезда — пишите, всегда на связи 😊",
  },
  {
    key: "no_rooms",
    label: "❌ Нет мест",
    text:
      "К сожалению, на выбранные даты свободных номеров нет 😔\n\n" +
      "Могу предложить посмотреть ближайшие доступные даты — " +
      "хотите, подберём альтернативный вариант?",
  },
  {
    key: "directions",
    label: "🚗 Добраться",
    text:
      "🚗 Как добраться до Тон Азур:\n\n" +
      "Мы находимся в 278 км от Бишкека — это примерно 4–4,5 часа на авто.\n\n" +
      "🛫 Трансфер от аэропорта Манас — 10 000 сом.\n" +
      "Аэропорт Тамчы — 146 км, трансфер индивидуально.\n" +
      "Летом — бесплатный трансфер до пляжей.\n\n" +
      "Если нужен трансфер — напишите, организуем! 😊",
  },
  {
    key: "cancellation",
    label: "📋 Условия отмены",
    text:
      "📋 Условия отмены бронирования:\n\n" +
      "• Более чем за 48 часов до заезда — отмена бесплатна.\n" +
      "• Менее чем за 48 часов — предоплата не возвращается.\n\n" +
      "Если есть вопросы — с удовольствием подскажу 😊",
  },
];

export default function ChatPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [clientConversations, setClientConversations] = useState([]);
  const [clientSidebarOpen, setClientSidebarOpen] = useState(false);
  const [showTrainModal, setShowTrainModal] = useState(false);
  const [trainQuestion, setTrainQuestion] = useState("");
  const [trainAnswer, setTrainAnswer] = useState("");
  const [trainSaving, setTrainSaving] = useState(false);
  const [trainSuccess, setTrainSuccess] = useState(false);
  const [notes, setNotes] = useState([]);
  const [noteText, setNoteText] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);
  const messagesEnd = useRef(null);

  const loadData = async () => {
    try {
      const [convRes, msgRes] = await Promise.all([
        getConversation(id),
        getMessages(id),
      ]);
      setConversation(convRes.data);
      setMessages(msgRes.data);

      // Загрузить историю обращений клиента и заметки
      if (convRes.data?.client_id) {
        const allConvs = await getConversations();
        const clientConvs = allConvs.data.filter(
          (c) => c.client_id === convRes.data.client_id
        );
        setClientConversations(clientConvs);

        try {
          const notesRes = await getNotesByClient(convRes.data.client_id);
          setNotes(notesRes.data);
        } catch {
          setNotes([]);
        }
      }
    } catch {
      navigate("/");
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [id]);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!text.trim() || sending) return;
    setSending(true);
    try {
      await sendMessage(id, text.trim());
      setText("");
      await loadData();
    } catch (err) {
      console.error(err);
    }
    setSending(false);
  };

  const handleTemplate = async (tpl) => {
    if (sending) return;
    setSending(true);
    try {
      await sendMessage(id, tpl.text);
      await loadData();
    } catch (err) {
      console.error(err);
    }
    setSending(false);
  };

  const handleClose = async () => {
    await updateConversation(id, { status: "closed" });
    await loadData();
  };

  const handleTakeover = async () => {
    await updateConversation(id, { status: "operator_active" });
    await loadData();
  };

  const handleReturnToBot = async () => {
    await updateConversation(id, { status: "in_progress" });
    await loadData();
  };

  const handleConfirmBooking = async () => {
    const msg =
      "Ваше бронирование подтверждено!\n" +
      "Мы с нетерпением ждём вас в отеле Ton Azure!\n\n" +
      "Если возникнут вопросы — пишите, будем рады помочь 😊";
    setSending(true);
    try {
      await sendMessage(id, msg);
      await updateConversation(id, { status: "closed" });
      await loadData();
    } catch (err) {
      console.error(err);
    }
    setSending(false);
  };

  const handleOpenTrain = async () => {
    try {
      const res = await getTrainSuggestion(id);
      setTrainQuestion(res.data.question);
      setTrainAnswer(res.data.answer);
      setTrainSuccess(false);
      setShowTrainModal(true);
    } catch {
      // Нет пары Q&A — откроем пустую форму
      setTrainQuestion("");
      setTrainAnswer("");
      setTrainSuccess(false);
      setShowTrainModal(true);
    }
  };

  const handleTrain = async () => {
    if (!trainQuestion.trim() || !trainAnswer.trim()) return;
    setTrainSaving(true);
    try {
      await trainFromConversation(trainQuestion.trim(), trainAnswer.trim(), Number(id));
      setTrainSuccess(true);
      setTimeout(() => setShowTrainModal(false), 1500);
    } catch (err) {
      console.error(err);
    }
    setTrainSaving(false);
  };

  const handleAddNote = async () => {
    if (!noteText.trim() || noteSaving) return;
    const phone =
      client?.phone ||
      (client?.channel === "whatsapp" ? client?.channel_user_id : null);
    if (!phone) return;
    setNoteSaving(true);
    try {
      await createNote(phone, noteText.trim());
      setNoteText("");
      const notesRes = await getNotesByClient(conversation.client_id);
      setNotes(notesRes.data);
    } catch (err) {
      console.error(err);
    }
    setNoteSaving(false);
  };

  const handleDeleteNote = async (noteId) => {
    try {
      await deleteNote(noteId);
      setNotes(notes.filter((n) => n.id !== noteId));
    } catch (err) {
      console.error(err);
    }
  };

  if (!conversation) return <p className="loading">Загрузка...</p>;

  const client = conversation.client;

  const CATEGORY_LABELS = {
    booking: "Бронирование",
    hotel: "Номера",
    service: "Услуги",
    general: "Общий",
  };

  return (
    <div className="chat-page">
      <div className="chat-header">
        <button className="btn-back" onClick={() => navigate("/")}>
          ← Назад
        </button>
        <div className="chat-info">
          <span className="chat-client-name">
            {client?.channel === "whatsapp" ? "📱" : "✈️"}{" "}
            {client?.name || client?.username || `Клиент #${conversation.client_id}`}
          </span>
          <span className="chat-status">
            {STATUS_LABELS[conversation.status]}
          </span>
        </div>
        <div className="chat-actions">
          {conversation.status !== "closed" &&
            conversation.status !== "operator_active" && (
              <button className="btn-takeover" onClick={handleTakeover}>
                Перехватить чат
              </button>
            )}
          {conversation.status === "operator_active" && (
            <button className="btn-return-bot" onClick={handleReturnToBot}>
              Вернуть боту
            </button>
          )}
          {conversation.status !== "closed" && (
            <button className="btn-confirm-booking" onClick={handleConfirmBooking}>
              Подтвердить бронь
            </button>
          )}
          {conversation.status !== "closed" && (
            <button className="btn-close-conv" onClick={handleClose}>
              Закрыть диалог
            </button>
          )}
          <button className="btn-train" onClick={handleOpenTrain}>
            Обучить
          </button>
          <button className="client-sidebar-toggle" onClick={() => setClientSidebarOpen(!clientSidebarOpen)}>
            👤 Клиент
          </button>
        </div>
      </div>

      <div className="chat-body">
        <div className="chat-main">
          <div className="messages-container">
            {messages.map((msg) => (
              <div key={msg.id} className={`message message-${msg.sender}`}>
                <div className="message-sender">
                  {SENDER_LABELS[msg.sender]}
                </div>
                <div className="message-text">{msg.text}</div>
                <div className="message-time">
                  {new Date(msg.created_at).toLocaleString("ru-RU")}
                </div>
              </div>
            ))}
            <div ref={messagesEnd} />
          </div>

          {conversation.status !== "closed" && (
            <div className="chat-input-area">
              <div className="quick-templates">
                {QUICK_TEMPLATES.map((tpl) => (
                  <button
                    key={tpl.key}
                    className="btn-template"
                    onClick={() => handleTemplate(tpl)}
                    disabled={sending}
                    title={tpl.text}
                  >
                    {tpl.label}
                  </button>
                ))}
              </div>
              <form className="message-form" onSubmit={handleSend}>
                <input
                  type="text"
                  placeholder="Написать клиенту..."
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  disabled={sending}
                />
                <button type="submit" disabled={sending || !text.trim()}>
                  Отправить
                </button>
              </form>
            </div>
          )}
        </div>

        <div className={`client-sidebar ${clientSidebarOpen ? "open" : ""}`}>
          <h3>Клиент</h3>
          <div className="client-field">
            <span className="client-label">Имя</span>
            <span className="client-value">{client?.name || "—"}</span>
          </div>
          <div className="client-field">
            <span className="client-label">Username</span>
            <span className="client-value">{client?.username ? `@${client.username}` : "—"}</span>
          </div>
          <div className="client-field">
            <span className="client-label">Телефон</span>
            <span className="client-value">{client?.phone || "Не указан"}</span>
          </div>
          <div className="client-field">
            <span className="client-label">Канал</span>
            <span className="client-value">
              {client?.channel === "whatsapp" ? "📱 WhatsApp" : "✈️ Telegram"}
            </span>
          </div>
          <div className="client-field">
            <span className="client-label">Категория</span>
            <span className="client-value">{CATEGORY_LABELS[conversation.category] || "—"}</span>
          </div>
          <div className="client-field">
            <span className="client-label">Первый контакт</span>
            <span className="client-value">
              {new Date(client?.created_at).toLocaleDateString("ru-RU")}
            </span>
          </div>
          <div className="client-field">
            <span className="client-label">Обращений</span>
            <span className="client-value">{clientConversations.length}</span>
          </div>
          {clientConversations.length > 1 && (
            <div className="client-history">
              <span className="client-label">История</span>
              {clientConversations
                .filter((c) => c.id !== conversation.id)
                .map((c) => (
                  <div
                    key={c.id}
                    className="client-history-item"
                    onClick={() => navigate(`/chat/${c.id}`)}
                  >
                    #{c.id} — {CATEGORY_LABELS[c.category]}{" "}
                    <span className="client-history-date">
                      {new Date(c.created_at).toLocaleDateString("ru-RU")}
                    </span>
                  </div>
                ))}
            </div>
          )}

          <div className="client-notes">
            <span className="client-label">Заметки менеджера</span>
            {notes.length > 0 ? (
              notes.map((note) => (
                <div key={note.id} className="note-item">
                  <div className="note-text">{note.text}</div>
                  <div className="note-meta">
                    {new Date(note.created_at).toLocaleDateString("ru-RU")}
                    <button
                      className="note-delete"
                      onClick={() => handleDeleteNote(note.id)}
                      title="Удалить заметку"
                    >
                      ×
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="note-empty">Нет заметок</div>
            )}
            {(client?.phone || client?.channel === "whatsapp") && (
              <div className="note-add">
                <textarea
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Добавить заметку (звонок, бронь и т.д.)..."
                  rows={2}
                />
                <button
                  onClick={handleAddNote}
                  disabled={noteSaving || !noteText.trim()}
                >
                  {noteSaving ? "..." : "Добавить"}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {showTrainModal && (
        <div className="modal-overlay" onClick={() => setShowTrainModal(false)}>
          <div className="modal train-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Обучить бота</h3>
            <p className="train-hint">Бот запомнит этот ответ и будет использовать его в будущем</p>
            <label>Вопрос клиента</label>
            <textarea
              value={trainQuestion}
              onChange={(e) => setTrainQuestion(e.target.value)}
              rows={3}
              placeholder="Вопрос, на который бот должен научиться отвечать..."
            />
            <label>Ответ бота</label>
            <textarea
              value={trainAnswer}
              onChange={(e) => setTrainAnswer(e.target.value)}
              rows={4}
              placeholder="Правильный ответ, который бот должен давать..."
            />
            <div className="train-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowTrainModal(false)}
                disabled={trainSaving}
              >
                Отмена
              </button>
              <button
                className="btn-save-train"
                onClick={handleTrain}
                disabled={trainSaving || !trainQuestion.trim() || !trainAnswer.trim()}
              >
                {trainSuccess ? "Сохранено!" : trainSaving ? "Сохраняю..." : "Сохранить в базу знаний"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
