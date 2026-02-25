import React, { useState, useEffect } from 'react';
import './Routines.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://pop-os.tailf0835c.ts.net:8000/api';

const api = {
  async getRoutines() {
    const res = await fetch(`${API_URL}/routines`);
    if (!res.ok) throw new Error('Failed to fetch routines');
    return res.json();
  },

  async createRoutine(routine) {
    const res = await fetch(`${API_URL}/routines`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(routine),
    });
    if (!res.ok) throw new Error('Failed to create routine');
    return res.json();
  },

  async updateRoutine(routineId, updates) {
    const res = await fetch(`${API_URL}/routines/${routineId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error('Failed to update routine');
    return res.json();
  },

  async deleteRoutine(routineId) {
    const res = await fetch(`${API_URL}/routines/${routineId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete routine');
    return res.json();
  },
};

const AddRoutineModal = ({ onClose, onAdd }) => {
  const [name, setName] = useState('');
  const [timeSlot, setTimeSlot] = useState('');
  const [days, setDays] = useState('Daily');
  const [description, setDescription] = useState('');
  const [icon, setIcon] = useState('📋');
  const [submitting, setSubmitting] = useState(false);

  const icons = ['📋', '☀️', '🌙', '🏃', '📚', '💻', '🍳', '🧘', '🎵', '✍️', '🎯', '💪'];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || submitting) return;

    setSubmitting(true);
    try {
      const newRoutine = await api.createRoutine({
        name: name.trim(),
        time_slot: timeSlot.trim() || null,
        days: days.trim() || 'Daily',
        description: description.trim() || null,
        icon,
      });
      onAdd(newRoutine);
      onClose();
    } catch (err) {
      alert('Failed to create routine: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content add-routine-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">➕ Add New Routine</div>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Routine Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Morning Writing"
              autoFocus
              required
            />
          </div>

          <div className="form-group">
            <label>Time Slot</label>
            <input
              type="text"
              value={timeSlot}
              onChange={(e) => setTimeSlot(e.target.value)}
              placeholder="e.g., 7:00-8:00 AM"
            />
          </div>

          <div className="form-group">
            <label>Days</label>
            <input
              type="text"
              value={days}
              onChange={(e) => setDays(e.target.value)}
              placeholder="e.g., Mon-Fri or Daily"
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description..."
              rows={3}
            />
          </div>

          <div className="form-group">
            <label>Choose Icon</label>
            <div className="icon-picker">
              {icons.map(i => (
                <button
                  key={i}
                  type="button"
                  className={`icon-btn ${icon === i ? 'selected' : ''}`}
                  onClick={() => setIcon(i)}
                >
                  {i}
                </button>
              ))}
            </div>
          </div>

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Adding...' : 'Add Routine'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const EditRoutineModal = ({ routine, onClose, onUpdate }) => {
  const [name, setName] = useState(routine.name);
  const [timeSlot, setTimeSlot] = useState(routine.time_slot || '');
  const [days, setDays] = useState(routine.days || 'Daily');
  const [description, setDescription] = useState(routine.description || '');
  const [icon, setIcon] = useState(routine.icon);
  const [submitting, setSubmitting] = useState(false);

  const icons = ['📋', '☀️', '🌙', '🏃', '📚', '💻', '🍳', '🧘', '🎵', '✍️', '🎯', '💪'];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || submitting) return;

    setSubmitting(true);
    try {
      await api.updateRoutine(routine.routine_id, {
        name: name.trim(),
        time_slot: timeSlot.trim() || null,
        days: days.trim() || 'Daily',
        description: description.trim() || null,
        icon,
      });
      onUpdate();
      onClose();
    } catch (err) {
      alert('Failed to update routine: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content add-routine-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">✏️ Edit Routine</div>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Routine Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Time Slot</label>
            <input
              type="text"
              value={timeSlot}
              onChange={(e) => setTimeSlot(e.target.value)}
              placeholder="e.g., 7:00-8:00 AM"
            />
          </div>

          <div className="form-group">
            <label>Days</label>
            <input
              type="text"
              value={days}
              onChange={(e) => setDays(e.target.value)}
              placeholder="e.g., Mon-Fri or Daily"
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description..."
              rows={3}
            />
          </div>

          <div className="form-group">
            <label>Choose Icon</label>
            <div className="icon-picker">
              {icons.map(i => (
                <button
                  key={i}
                  type="button"
                  className={`icon-btn ${icon === i ? 'selected' : ''}`}
                  onClick={() => setIcon(i)}
                >
                  {i}
                </button>
              ))}
            </div>
          </div>

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const RoutineCard = ({ routine, onEdit, onDelete }) => {
  const handleDelete = () => {
    if (window.confirm(`Delete "${routine.name}"?`)) {
      onDelete(routine.routine_id);
    }
  };

  return (
    <div className="routine-item-card">
      <div className="routine-item-content">
        <span className="routine-item-icon">{routine.icon}</span>
        <div className="routine-item-details">
          <div className="routine-item-name">{routine.name}</div>
          {(routine.time_slot || routine.days) && (
            <div className="routine-item-meta">
              {routine.time_slot && <span className="time-badge">🕐 {routine.time_slot}</span>}
              {routine.days && <span className="days-badge">📅 {routine.days}</span>}
            </div>
          )}
          {routine.description && (
            <div className="routine-item-desc">{routine.description}</div>
          )}
        </div>
      </div>
      <div className="routine-item-actions">
        <button className="edit-btn" onClick={() => onEdit(routine)} title="Edit">✏️</button>
        <button className="delete-btn" onClick={handleDelete} title="Delete">🗑️</button>
      </div>
    </div>
  );
};

function DailyRoutines() {
  const [routines, setRoutines] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingRoutine, setEditingRoutine] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRoutines = async () => {
    try {
      setLoading(true);
      const data = await api.getRoutines();
      setRoutines(data);
      setError(null);
    } catch (err) {
      setError('Failed to load routines. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoutines();
  }, []);

  const handleAddRoutine = (newRoutine) => {
    setRoutines(prev => [...prev, newRoutine]);
  };

  const handleDeleteRoutine = async (routineId) => {
    try {
      await api.deleteRoutine(routineId);
      setRoutines(prev => prev.filter(r => r.routine_id !== routineId));
    } catch (err) {
      alert('Failed to delete routine: ' + err.message);
    }
  };

  if (loading) {
    return (
      <div className="routines-page">
        <div style={{ textAlign: 'center', padding: '60px', color: '#8b949e' }}>
          <h1>📅 Daily Routines</h1>
          <p>Loading your routines...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="routines-page">
      <header className="routines-header">
        <h1>📅 Daily Routines</h1>
        <p className="subtitle">Plan and organize your daily schedule</p>
        {error && <p style={{ color: '#f85149' }}>{error}</p>}
      </header>

      <main className="routines-list-container">
        {routines.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>No routines yet</h3>
            <p>Add your first daily routine to get started!</p>
          </div>
        ) : (
          routines.map(routine => (
            <RoutineCard
              key={routine.id}
              routine={routine}
              onEdit={setEditingRoutine}
              onDelete={handleDeleteRoutine}
            />
          ))
        )}
      </main>

      <button className="add-routine-fab" onClick={() => setShowAddModal(true)}>
        <span>+</span>
      </button>

      {showAddModal && (
        <AddRoutineModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddRoutine}
        />
      )}

      {editingRoutine && (
        <EditRoutineModal
          routine={editingRoutine}
          onClose={() => setEditingRoutine(null)}
          onUpdate={fetchRoutines}
        />
      )}
    </div>
  );
}

export default DailyRoutines;
