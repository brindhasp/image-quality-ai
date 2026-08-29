import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function History({ onViewItem, refresh }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHistory();
  }, [refresh]);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/history`);
      setHistory(response.data);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API_URL}/api/analysis/${id}`);
      setHistory(prev => prev.filter(item => item.id !== id));
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 70) return '#28a745';
    if (score >= 40) return '#ffc107';
    return '#dc3545';
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading history...</p>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="no-history">
        <p>No analyses yet. Upload an image to get started!</p>
      </div>
    );
  }

  return (
    <div className="history-list">
      <h2 style={{ marginBottom: '16px' }}>Analysis History</h2>
      {history.map((item) => (
        <div key={item.id} className="history-item" onClick={() => onViewItem(item)}>
          <div className="history-info">
            <h4>{item.filename}</h4>
            <p>{item.quality_label} • {new Date(item.created_at).toLocaleString()}</p>
          </div>
          <div className="history-score" style={{ color: getScoreColor(item.quality_score) }}>
            {item.quality_score}
          </div>
          <button 
            className="delete-btn"
            onClick={(e) => handleDelete(e, item.id)}
          >
            Delete
          </button>
        </div>
      ))}
    </div>
  );
}

export default History;