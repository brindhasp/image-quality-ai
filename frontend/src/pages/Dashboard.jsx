import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, Legend } from 'recharts';
import { getStatistics } from '../services/api';

const COLORS = ['#22c55e', '#f59e0b', '#ef4444', '#6366f1', '#3b82f6', '#ec4899'];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    setLoading(true);
    setError(null);
    try {
      const data = await getStatistics();
      setStats(data);
    } catch (err) {
      setError('Failed to load statistics. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="loading"><div className="spinner"></div> Loading dashboard...</div>;
  if (error) return <div className="empty-state"><div className="empty-icon">&#9888;</div><p>{error}</p></div>;
  if (!stats) return null;

  const labelData = Object.entries(stats.label_distribution || {}).map(([name, value]) => ({ name, value }));
  const issueData = Object.entries(stats.issue_distribution || {}).map(([name, value]) => ({ name, value }));

  const trendData = (stats.recent_analyses || []).map(a => ({
    name: a.filename.length > 12 ? a.filename.substring(0, 12) + '...' : a.filename,
    score: a.quality_score,
    id: a.id,
  })).reverse();

  const scoreGauge = [
    { name: 'Score', value: stats.average_score || 0 },
    { name: 'Remaining', value: 100 - (stats.average_score || 0) },
  ];

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total_analyses}</div>
          <div className="stat-label">Total Analyzed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#6366f1' }}>{stats.average_score}</div>
          <div className="stat-label">Avg Quality Score</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#22c55e' }}>{stats.acceptable_count}</div>
          <div className="stat-label">Acceptable</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#f59e0b' }}>{stats.degraded_count}</div>
          <div className="stat-label">Degraded</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#ef4444' }}>{stats.defective_count}</div>
          <div className="stat-label">Defective</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: '18px' }}>{stats.most_common_issue || 'N/A'}</div>
          <div className="stat-label">Most Common Issue</div>
        </div>
      </div>

      {stats.total_analyses === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px' }}>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>No analyses yet. Upload an image to get started.</p>
          <button className="btn btn-primary" onClick={() => navigate('/analyze')}>Analyze Image</button>
        </div>
      ) : (
        <>
          <div className="dashboard-row">
            <div className="chart-card dashboard-score-gauge">
              <h3>Average Quality Score</h3>
              <div className="gauge-container">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={scoreGauge}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={85}
                      startAngle={180}
                      endAngle={0}
                      dataKey="value"
                      stroke="none"
                    >
                      <Cell fill={stats.average_score >= 75 ? '#22c55e' : stats.average_score >= 50 ? '#f59e0b' : '#ef4444'} />
                      <Cell fill="#2a2d3e" />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="gauge-center">
                  <div className="gauge-score">{stats.average_score}</div>
                  <div className="gauge-label">out of 100</div>
                </div>
              </div>
            </div>

            <div className="chart-card">
              <h3>Quality Label Distribution</h3>
              {labelData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={labelData} cx="50%" cy="50%" outerRadius={75} innerRadius={40} dataKey="value" paddingAngle={3}>
                      {labelData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: '#1e2130', border: '1px solid #2a2d3e', borderRadius: '8px' }} />
                    <Legend wrapperStyle={{ fontSize: '12px', color: '#9aa0b0' }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : <p style={{ color: 'var(--text-muted)', textAlign: 'center' }}>No data</p>}
            </div>

            <div className="chart-card">
              <h3>Issue Distribution</h3>
              {issueData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={issueData} layout="vertical" margin={{ left: 10 }}>
                    <XAxis type="number" tick={{ fill: '#9aa0b0', fontSize: 11 }} />
                    <YAxis type="category" dataKey="name" tick={{ fill: '#9aa0b0', fontSize: 11 }} width={100} />
                    <Tooltip contentStyle={{ background: '#1e2130', border: '1px solid #2a2d3e', borderRadius: '8px' }} />
                    <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <p style={{ color: 'var(--text-muted)', textAlign: 'center' }}>No issues detected</p>}
            </div>
          </div>

          {trendData.length > 1 && (
            <div className="chart-card" style={{ marginBottom: '16px' }}>
              <h3>Quality Score Trend</h3>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                  <XAxis dataKey="name" tick={{ fill: '#9aa0b0', fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#9aa0b0', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#1e2130', border: '1px solid #2a2d3e', borderRadius: '8px' }} />
                  <Line type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={2} dot={{ r: 4, fill: '#6366f1' }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="chart-card">
            <h3>Recent Analyses</h3>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Score</th>
                    <th>Label</th>
                    <th>Issues</th>
                    <th>Date</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {(stats.recent_analyses || []).map(a => (
                    <tr key={a.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/analysis/${a.id}`)}>
                      <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.filename}</td>
                      <td style={{ fontWeight: 600 }}>{a.quality_score}</td>
                      <td><span className={`quality-label ${a.quality_label.toLowerCase()}`}>{a.quality_label}</span></td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{(a.issues || []).length > 0 ? a.issues.map(i => i.type).join(', ') : 'None'}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{new Date(a.created_at).toLocaleDateString()}</td>
                      <td><button className="btn btn-sm btn-secondary">View</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
