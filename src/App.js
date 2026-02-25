import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
const FALLBACK_DATA = '/data.json';

// Fallback week data generator
function generateWeekDataFallback(habitId) {
  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const today = new Date();
  const dayOfWeek = (today.getDay() + 6) % 7;
  
  return dayNames.map((day, i) => {
    const isFuture = i > dayOfWeek;
    const isToday = i === dayOfWeek;
    
    if (isFuture) {
      return { day, completion: 0, status: 'future', is_future: true, is_today: false };
    }
    
    // Generate deterministic random based on habit id
    const seed = (habitId * 7 + i) % 100;
    let completion;
    if (seed > 60) completion = 100;
    else if (seed > 30) completion = 50;
    else completion = 0;
    
    return {
      day,
      completion,
      status: completion >= 75 ? 'completed' : completion >= 30 ? 'partial' : 'missed',
      is_future: false,
      is_today
    };
  });
}

// ==================== API FUNCTIONS ====================

const api = {
  async getHabits() {
    try {
      const res = await fetch(`${API_URL}/habits`);
      if (!res.ok) throw new Error('Failed to fetch habits');
      return res.json();
    } catch (err) {
      // Fallback to local JSON
      const res = await fetch(FALLBACK_DATA);
      const data = await res.json();
      // Transform to expected format
      return data.habits.map(h => ({
        ...h,
        week_data: generateWeekDataFallback(h.id)
      }));
    }
  },

  async createHabit(habit) {
    const res = await fetch(`${API_URL}/habits`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(habit),
    });
    if (!res.ok) throw new Error('Failed to create habit');
    return res.json();
  },

  async updateCompletion(habitId, date, completionPercent) {
    const res = await fetch(`${API_URL}/habits/${habitId}/completion/${date}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ completion_percent: completionPercent }),
    });
    if (!res.ok) throw new Error('Failed to update completion');
    return res.json();
  },

  async getMonthlyData(habitId) {
    const res = await fetch(`${API_URL}/habits/${habitId}/monthly`);
    if (!res.ok) throw new Error('Failed to fetch monthly data');
    return res.json();
  },

  async deleteHabit(habitId) {
    const res = await fetch(`${API_URL}/habits/${habitId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete habit');
    return res.json();
  },
};

// ==================== COMPONENTS ====================

const ProgressBar = ({ percentage, height = 40, showTooltip = true, label = null }) => {
  const [showTip, setShowTip] = useState(false);
  
  const getBarClass = (pct) => {
    if (pct >= 75) return 'completed';
    if (pct >= 30) return 'partial';
    return 'missed';
  };
  
  return (
    <div 
      className="progress-bar-wrapper"
      onMouseEnter={() => setShowTip(true)}
      onMouseLeave={() => setShowTip(false)}
    >
      <div className={`progress-bar ${getBarClass(percentage)}`} style={{ height: `${height}px` }}>
        <div className="progress-fill" style={{ height: `${percentage}%` }} />
      </div>
      {showTooltip && showTip && (
        <div className="progress-tooltip">
          {label || `${Math.round(percentage)}%`}
        </div>
      )}
    </div>
  );
};

const WeeklyBars = ({ routine, weekData, onDayClick }) => {
  return (
    <div className="weekly-bars">
      {weekData.map((dayData, index) => (
        <div key={index} className="day-column">
          <div 
            className={`day-bar-container ${dayData.status}`}
            onClick={() => !dayData.is_future && onDayClick(routine.id, dayData)}
            style={{ cursor: dayData.is_future ? 'default' : 'pointer' }}
          >
            <ProgressBar 
              percentage={dayData.completion}
              height={50}
              showTooltip={!dayData.is_future}
              label={`${dayData.day}: ${Math.round(dayData.completion)}%`}
            />
          </div>
          <span className="day-name">{dayData.day}</span>
          <div className={`status-indicator ${dayData.status}`} />
          {dayData.is_today && <span className="today-badge">TODAY</span>}
        </div>
      ))}
    </div>
  );
};

const MonthlyHeatmap = ({ data, onDayHover }) => {
  const weeks = [];
  let currentWeek = [];
  
  const firstDay = data.days?.[0] ? new Date(data.days[0].date).getDay() : 0;
  const paddingDays = firstDay === 0 ? 6 : firstDay - 1;
  
  for (let i = 0; i < paddingDays; i++) {
    currentWeek.push(null);
  }
  
  data.days?.forEach(dayData => {
    currentWeek.push(dayData);
    if (currentWeek.length === 7) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  });
  
  if (currentWeek.length > 0) {
    while (currentWeek.length < 7) currentWeek.push(null);
    weeks.push(currentWeek);
  }

  const getLevel = (pct) => {
    if (pct === 0) return 0;
    if (pct < 25) return 1;
    if (pct < 50) return 2;
    if (pct < 75) return 3;
    return 4;
  };
  
  return (
    <div className="heatmap-grid">
      {weeks.map((week, weekIndex) => (
        <div key={weekIndex} className="heatmap-week">
          {week.map((dayData, dayIndex) => {
            if (!dayData) {
              return <div key={dayIndex} className="heatmap-day empty" />;
            }
            
            const level = getLevel(dayData.completion);
            
            return (
              <div
                key={dayIndex}
                className={`heatmap-day level-${level} ${dayData.is_future ? 'future' : ''}`}
                onMouseEnter={() => onDayHover(dayData)}
                onMouseLeave={() => onDayHover(null)}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
};

const RoutineCard = ({ routine, onClick, onDayClick, onDelete }) => {
  const completedCount = routine.week_data?.filter(d => d.status === 'completed').length || 0;
  const totalTracked = routine.week_data?.filter(d => !d.is_future).length || 0;
  const percent = totalTracked > 0 ? Math.round((completedCount / totalTracked) * 100) : 0;
  const todayData = routine.week_data?.find(d => d.is_today);

  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm(`Delete "${routine.name}"?`)) {
      onDelete(routine.id);
    }
  };
  
  return (
    <div className="routine-card" onClick={() => onClick(routine)}>
      <div className="routine-header">
        <div className="routine-title">
          <span className="routine-icon">{routine.icon}</span>
          <span className="routine-name">{routine.name}</span>
          {routine.is_recurring && (
            <span className="recurring-badge">🔄 {routine.duration}</span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="weekly-percentage">{percent}% this week</div>
          <button className="delete-btn" onClick={handleDelete} title="Delete habit">🗑️</button>
        </div>
      </div>
      
      <WeeklyBars 
        routine={routine} 
        weekData={routine.week_data || []} 
        onDayClick={onDayClick}
      />
      
      <div className="routine-stats">
        <div className="stat">
          <div className="stat-value completed">{completedCount}</div>
          <div className="stat-label">Completed</div>
        </div>
        <div className="stat">
          <div className="stat-value partial">
            {routine.week_data?.filter(d => d.status === 'partial').length || 0}
          </div>
          <div className="stat-label">Partial</div>
        </div>
        <div className="stat">
          <div className="stat-value missed">
            {routine.week_data?.filter(d => d.status === 'missed').length || 0}
          </div>
          <div className="stat-label">Missed</div>
        </div>
        <div className="stat">
          <div className="stat-value">
            {todayData ? `${Math.round(todayData.completion)}%` : '-'}
          </div>
          <div className="stat-label">Today</div>
        </div>
      </div>
    </div>
  );
};

const MonthlyModal = ({ routine, onClose, onUpdate }) => {
  const [data, setData] = useState(null);
  const [hoveredDay, setHoveredDay] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMonthlyData(routine.id)
      .then(setData)
      .finally(() => setLoading(false));
  }, [routine.id]);

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={e => e.stopPropagation()}>
          <div style={{ textAlign: 'center', padding: '40px', color: '#8b949e' }}>
            Loading...
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <span className="modal-icon">{routine.icon}</span>
            <span>{routine.name} - Monthly View</span>
          </div>
          <button className="close-btn" onClick={onClose}>✕ Close</button>
        </div>
        
        <div className="monthly-stats">
          <div className="month-stat">
            <span className="month-stat-value">{data?.stats?.completed_days || 0}</span>
            <span className="month-stat-label">Days completed</span>
          </div>
          <div className="month-stat">
            <span className="month-stat-value">{Math.round(data?.stats?.avg_completion || 0)}%</span>
            <span className="month-stat-label">Avg completion</span>
          </div>
          <div className="month-stat">
            <span className="month-stat-value">{data?.stats?.current_streak || routine.streak || 0}</span>
            <span className="month-stat-label">Current streak</span>
          </div>
        </div>
        
        <MonthlyHeatmap data={data || {}} onDayHover={setHoveredDay} />
        
        <div className="heatmap-tooltip">
          {hoveredDay ? (
            <>
              <strong>{formatDate(hoveredDay.date)}</strong>
              <span>{Math.round(hoveredDay.completion)}% complete</span>
            </>
          ) : (
            <span className="placeholder">Hover over a day to see details</span>
          )}
        </div>
        
        <div className="legend">
          <span>Less</span>
          <div className="legend-box level-0" />
          <div className="legend-box level-1" />
          <div className="legend-box level-2" />
          <div className="legend-box level-3" />
          <div className="legend-box level-4" />
          <span>More</span>
        </div>
      </div>
    </div>
  );
};

const AddHabitModal = ({ onClose, onAdd }) => {
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('✨');
  const [isRecurring, setIsRecurring] = useState(false);
  const [duration, setDuration] = useState('30 days');
  const [submitting, setSubmitting] = useState(false);
  
  const icons = ['🏃', '🎯', '📚', '🌙', '💪', '🧘', '💧', '🥗', '💤', '🎨', '🎸', '✍️', '💻', '☕', '🚶'];
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || submitting) return;
    
    setSubmitting(true);
    try {
      const newHabit = await api.createHabit({
        name: name.trim(),
        icon,
        is_recurring: isRecurring,
        duration: isRecurring ? duration : null,
      });
      onAdd(newHabit);
      onClose();
    } catch (err) {
      alert('Failed to create habit: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content add-habit-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">➕ Add New Habit</div>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Habit Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Morning Meditation"
              autoFocus
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
          
          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isRecurring}
                onChange={(e) => setIsRecurring(e.target.checked)}
              />
              <span>Make this a recurring habit</span>
            </label>
          </div>
          
          {isRecurring && (
            <div className="form-group">
              <label>Duration</label>
              <select value={duration} onChange={(e) => setDuration(e.target.value)}>
                <option value="7 days">7 days (1 week)</option>
                <option value="14 days">14 days (2 weeks)</option>
                <option value="21 days">21 days (3 weeks)</option>
                <option value="30 days">30 days (1 month)</option>
                <option value="60 days">60 days (2 months)</option>
                <option value="90 days">90 days (3 months)</option>
                <option value="365 days">365 days (1 year)</option>
              </select>
            </div>
          )}
          
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Adding...' : 'Add Habit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ==================== MAIN APP ====================

function App() {
  const [routines, setRoutines] = useState([]);
  const [selectedRoutine, setSelectedRoutine] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRoutines = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getHabits();
      setRoutines(data);
      setError(null);
    } catch (err) {
      setError('Failed to load habits. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRoutines();
    // Refresh every 30 seconds
    const interval = setInterval(fetchRoutines, 30000);
    return () => clearInterval(interval);
  }, [fetchRoutines]);

  const handleAddHabit = useCallback((newHabit) => {
    setRoutines(prev => [newHabit, ...prev]);
  }, []);

  const handleDeleteHabit = useCallback(async (habitId) => {
    try {
      await api.deleteHabit(habitId);
      setRoutines(prev => prev.filter(r => r.id !== habitId));
    } catch (err) {
      alert('Failed to delete habit: ' + err.message);
    }
  }, []);

  const handleDayClick = useCallback(async (habitId, dayData) => {
    // Calculate new completion (cycle: 0 -> 50 -> 100 -> 0)
    const current = dayData.completion;
    let newCompletion;
    if (current < 30) newCompletion = 50;
    else if (current < 75) newCompletion = 100;
    else newCompletion = 0;

    // Get date from day name
    const today = new Date();
    const dayOfWeek = (today.getDay() + 6) % 7;
    const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const dayIndex = dayNames.indexOf(dayData.day);
    const date = new Date(today);
    date.setDate(today.getDate() - (dayOfWeek - dayIndex));
    const dateStr = date.toISOString().split('T')[0];

    try {
      await api.updateCompletion(habitId, dateStr, newCompletion);
      // Refresh to show updated data
      fetchRoutines();
    } catch (err) {
      alert('Failed to update: ' + err.message);
    }
  }, [fetchRoutines]);

  if (loading && routines.length === 0) {
    return (
      <div className="app">
        <div style={{ textAlign: 'center', padding: '60px', color: '#8b949e' }}>
          <h1>📊 Routine Tracker</h1>
          <p>Loading your habits...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>📊 Routine Tracker</h1>
        <p className="subtitle">Click any routine for monthly view • Click bars to toggle</p>
        {error && <p style={{ color: '#f85149' }}>{error}</p>}
      </header>
      
      <main className="routines-list">
        {routines.map(routine => (
          <RoutineCard
            key={routine.id}
            routine={routine}
            onClick={setSelectedRoutine}
            onDayClick={handleDayClick}
            onDelete={handleDeleteHabit}
          />
        ))}
      </main>
      
      <button className="add-habit-fab" onClick={() => setShowAddModal(true)}>
        <span>+</span>
      </button>
      
      {selectedRoutine && (
        <MonthlyModal
          routine={selectedRoutine}
          onClose={() => setSelectedRoutine(null)}
          onUpdate={fetchRoutines}
        />
      )}
      
      {showAddModal && (
        <AddHabitModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddHabit}
        />
      )}
    </div>
  );
}

export default App;
