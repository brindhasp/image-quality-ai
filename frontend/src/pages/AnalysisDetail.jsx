import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAnalysis, deleteAnalysis } from '../services/api';

export default function AnalysisDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAnalysis();
  }, [id]);

  async function loadAnalysis() {
    setLoading(true);
    setError(null);
    try {
      const data = await getAnalysis(id);
      setAnalysis(data);
    } catch (err) {
      setError('Failed to load analysis');
    } finally {
      setLoading(false);
    }
  }

  const handleDelete = async () => {
    if (!confirm('Delete this analysis?')) return;
    try {
      await deleteAnalysis(id);
      navigate('/history');
    } catch {
      alert('Failed to delete');
    }
  };

  if (loading) return <div className="loading"><div className="spinner"></div> Loading...</div>;
  if (error) return <div className="empty-state"><div className="empty-icon">&#9888;</div><p>{error}</p></div>;
  if (!analysis) return null;

  const scoreClass = analysis.quality_score >= 75 ? 'acceptable' : analysis.quality_score >= 50 ? 'degraded' : 'defective';
  const stats = analysis.statistics || {};

  const statItems = [
    { key: 'Sharpness', val: stats.sharpness?.toFixed(1) },
    { key: 'Brightness', val: stats.brightness?.toFixed(1) },
    { key: 'Contrast', val: stats.contrast?.toFixed(1) },
    { key: 'Noise Level', val: stats.noise_level?.toFixed(1) },
    { key: 'Saturation', val: stats.saturation?.toFixed(1) },
    { key: 'Exposure Score', val: stats.exposure_score?.toFixed(1) },
    { key: 'Blur Score', val: stats.blur_score?.toFixed(1) },
  ].filter(item => item.val !== undefined);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 className="page-title" style={{ marginBottom: 0 }}>Analysis Details</h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={() => navigate(-1)}>Back</button>
          <button className="btn btn-danger" onClick={handleDelete}>Delete</button>
        </div>
      </div>

      <div className="detail-grid">
        <div className="card score-display">
          <div className={`score-circle ${scoreClass}`}>
            {analysis.quality_score}
          </div>
          <div className={`quality-label ${analysis.quality_label.toLowerCase()}`}>
            {analysis.quality_label}
          </div>
          <p style={{ marginTop: '12px', color: 'var(--text-muted)', fontSize: '13px' }}>
            {analysis.filename}
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
            {new Date(analysis.created_at).toLocaleString()}
          </p>
        </div>

        <div className="card">
          <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px' }}>Detected Issues</h3>
          {(analysis.issues || []).length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No issues detected</p>
          ) : (
            <div className="issues-grid">
              {(analysis.issues || []).map((issue, i) => (
                <div className="issue-card" key={i}>
                  <div className="issue-header">
                    <span className="issue-type">{issue.type}</span>
                    <span className={`severity-badge ${issue.severity}`}>{issue.severity}</span>
                  </div>
                  <div className="issue-confidence">Confidence: {(issue.confidence * 100).toFixed(0)}%</div>
                  {issue.description && <div className="issue-explanation">{issue.description}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {statItems.length > 0 && (
        <div className="card" style={{ marginTop: '24px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px' }}>Image Statistics</h3>
          <div className="stats-grid">
            {statItems.map(item => (
              <div className="stat-item" key={item.key}>
                <span className="stat-key">{item.key}</span>
                <span className="stat-val">{item.val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card" style={{ marginTop: '24px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px' }}>Summary</h3>
        <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius)', fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          This image has a quality score of <strong>{analysis.quality_score}/100</strong>,
          classified as <strong>{analysis.quality_label.replace('_', ' ')}</strong>.
          {(analysis.issues || []).length > 0
            ? ` Detected ${(analysis.issues || []).length} issue(s): ${(analysis.issues || []).map(i => i.type.toLowerCase()).join(', ')}.`
            : ' No significant issues were detected.'}
        </div>
      </div>
    </div>
  );
}
