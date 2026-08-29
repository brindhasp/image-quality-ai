import React from 'react';

function AnalysisResult({ result }) {
  const getScoreClass = (score) => {
    if (score >= 70) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  };

  const getBadgeClass = (label) => {
    switch (label) {
      case 'ACCEPTABLE': return 'acceptable';
      case 'DEGRADED': return 'degraded';
      default: return 'defective';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'high': return '🔴';
      case 'medium': return '🟡';
      case 'low': return '🔵';
      default: return '⚪';
    }
  };

  const getIssueIcon = (type) => {
    switch (type) {
      case 'blur': return '🌫️';
      case 'underexposure': return '🌑';
      case 'overexposure': return '☀️';
      case 'noise': return '📊';
      case 'corruption': return '💥';
      case 'low_contrast': return '🔘';
      default: return '✅';
    }
  };

  return (
    <div className="result-card">
      <div className="result-header">
        <div>
          <h2>Analysis Result</h2>
          <span className={`quality-badge ${getBadgeClass(result.quality_label)}`}>
            {result.quality_label}
          </span>
        </div>
        <div className={`score-circle ${getScoreClass(result.quality_score)}`}>
          {result.quality_score}
        </div>
      </div>

      {result.issues && result.issues.length > 0 && (
        <div className="issues-list">
          <h3>Detected Issues</h3>
          {result.issues.map((issue, index) => (
            <div key={index} className={`issue-item severity-${issue.severity}`}>
              <span className="issue-icon">{getIssueIcon(issue.type)}</span>
              <div className="issue-info">
                <h4>
                  {getSeverityIcon(issue.severity)} {issue.type.replace('_', ' ').toUpperCase()}
                </h4>
                <p>{issue.description}</p>
                <p>Confidence: {(issue.confidence * 100).toFixed(1)}%</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {result.statistics && (
        <div className="statistics-grid">
          <h3 style={{ gridColumn: '1 / -1' }}>Image Statistics</h3>
          <div className="stat-item">
            <div className="stat-label">Sharpness</div>
            <div className="stat-value">{(result.statistics.sharpness * 100).toFixed(1)}%</div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Brightness</div>
            <div className="stat-value">{(result.statistics.brightness * 100).toFixed(1)}%</div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Contrast</div>
            <div className="stat-value">{(result.statistics.contrast * 100).toFixed(1)}%</div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Noise Level</div>
            <div className="stat-value">{(result.statistics.noise_level * 100).toFixed(1)}%</div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Saturation</div>
            <div className="stat-value">{(result.statistics.saturation * 100).toFixed(1)}%</div>
          </div>
          <div className="stat-item">
            <div className="stat-label">Exposure</div>
            <div className="stat-value">{(result.statistics.exposure_score * 100).toFixed(1)}%</div>
          </div>
        </div>
      )}

      {result.created_at && (
        <p style={{ marginTop: '16px', color: '#666', fontSize: '0.9rem' }}>
          Analyzed at: {new Date(result.created_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}

export default AnalysisResult;