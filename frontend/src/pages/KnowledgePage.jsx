import { useEffect, useState } from "react";
import {
  getKnowledgeEntries,
  createKnowledgeEntry,
  updateKnowledgeEntry,
  deleteKnowledgeEntry,
} from "../services/api";
import { useNavigate } from "react-router-dom";

export default function KnowledgePage() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [formData, setFormData] = useState({ question: "", answer: "" });
  const navigate = useNavigate();

  useEffect(() => {
    loadEntries();
  }, []);

  const loadEntries = async () => {
    try {
      const res = await getKnowledgeEntries();
      setEntries(res.data);
    } catch (e) {
      console.error("Ошибка загрузки:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!formData.question.trim() || !formData.answer.trim()) return;
    try {
      await createKnowledgeEntry(formData.question, formData.answer);
      setShowAddModal(false);
      setFormData({ question: "", answer: "" });
      loadEntries();
    } catch (e) {
      console.error("Ошибка добавления:", e);
    }
  };

  const handleEdit = async () => {
    if (!editingEntry) return;
    try {
      await updateKnowledgeEntry(editingEntry.id, {
        question: formData.question,
        answer: formData.answer,
      });
      setEditingEntry(null);
      setFormData({ question: "", answer: "" });
      loadEntries();
    } catch (e) {
      console.error("Ошибка обновления:", e);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Удалить эту запись?")) return;
    try {
      await deleteKnowledgeEntry(id);
      loadEntries();
    } catch (e) {
      console.error("Ошибка удаления:", e);
    }
  };

  const handleToggleActive = async (entry) => {
    try {
      await updateKnowledgeEntry(entry.id, { is_active: !entry.is_active });
      loadEntries();
    } catch (e) {
      console.error("Ошибка:", e);
    }
  };

  const openEditModal = (entry) => {
    setEditingEntry(entry);
    setFormData({ question: entry.question, answer: entry.answer });
  };

  const filteredEntries = entries.filter(
    (e) =>
      e.question.toLowerCase().includes(search.toLowerCase()) ||
      e.answer.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) return <p className="loading">Загрузка...</p>;

  return (
    <div className="knowledge-page">
      <div className="knowledge-header">
        <button className="btn-back" onClick={() => navigate("/")}>
          ← Назад
        </button>
        <h1>База знаний</h1>
        <button className="btn-add" onClick={() => setShowAddModal(true)}>
          + Добавить
        </button>
      </div>

      <div className="knowledge-search">
        <input
          type="text"
          placeholder="Поиск..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="knowledge-stats">
        Всего записей: {entries.length} | Активных:{" "}
        {entries.filter((e) => e.is_active).length}
      </div>

      <div className="knowledge-list">
        {filteredEntries.length === 0 ? (
          <p className="no-entries">
            {search ? "Ничего не найдено" : "База знаний пуста"}
          </p>
        ) : (
          filteredEntries.map((entry) => (
            <div
              key={entry.id}
              className={`knowledge-entry ${!entry.is_active ? "inactive" : ""}`}
            >
              <div className="entry-content">
                <div className="entry-question">
                  <strong>Вопрос:</strong> {entry.question}
                </div>
                <div className="entry-answer">
                  <strong>Ответ:</strong> {entry.answer}
                </div>
                <div className="entry-meta">
                  {entry.added_by_name && <span>Добавил: {entry.added_by_name}</span>}
                  <span>Использован: {entry.times_used} раз</span>
                  {!entry.is_active && <span className="badge-inactive">Отключено</span>}
                </div>
              </div>
              <div className="entry-actions">
                <button
                  className="btn-toggle"
                  onClick={() => handleToggleActive(entry)}
                  title={entry.is_active ? "Отключить" : "Включить"}
                >
                  {entry.is_active ? "🟢" : "⚪"}
                </button>
                <button
                  className="btn-edit"
                  onClick={() => openEditModal(entry)}
                >
                  ✏️
                </button>
                <button
                  className="btn-delete"
                  onClick={() => handleDelete(entry.id)}
                >
                  🗑️
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Модальное окно добавления */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Добавить запись</h2>
            <div className="form-group">
              <label>Вопрос клиента:</label>
              <textarea
                value={formData.question}
                onChange={(e) =>
                  setFormData({ ...formData, question: e.target.value })
                }
                placeholder="Например: Есть ли у вас номер с видом на озеро?"
              />
            </div>
            <div className="form-group">
              <label>Ответ бота:</label>
              <textarea
                value={formData.answer}
                onChange={(e) =>
                  setFormData({ ...formData, answer: e.target.value })
                }
                placeholder="Например: Да, у нас есть номера с панорамным видом на Иссык-Куль..."
              />
            </div>
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setShowAddModal(false)}>
                Отмена
              </button>
              <button className="btn-save" onClick={handleAdd}>
                Добавить
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно редактирования */}
      {editingEntry && (
        <div className="modal-overlay" onClick={() => setEditingEntry(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Редактировать запись</h2>
            <div className="form-group">
              <label>Вопрос клиента:</label>
              <textarea
                value={formData.question}
                onChange={(e) =>
                  setFormData({ ...formData, question: e.target.value })
                }
              />
            </div>
            <div className="form-group">
              <label>Ответ бота:</label>
              <textarea
                value={formData.answer}
                onChange={(e) =>
                  setFormData({ ...formData, answer: e.target.value })
                }
              />
            </div>
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setEditingEntry(null)}>
                Отмена
              </button>
              <button className="btn-save" onClick={handleEdit}>
                Сохранить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
