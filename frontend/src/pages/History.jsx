import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAnalyses, deleteAnalysis } from '../services/api';

export default function History() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [label, setLabel] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(1);
  const navigate = useNavigate();
  const searchTimer = useRef(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAnalyses({ page, page_size: 10, search, label, sort_by: sortBy, sort_order: sortOrder });
      setData(res);
    } catch (err) {
      if (!err.__cancelled) {
        setError('Failed to load history');
      }
    } finally {
      setLoading(false);
    }
  }, [page, search, label, sortBy, sortOrder]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSearch = (e) => {
    const val = e.target.value;
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setSearch(val);
      setPage(1);
    }, 300);
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!confirm('Delete this analysis?')) return;
    try {
      await deleteAnalysis(id);
      loadData();
    } catch {
      alert('Failed to delete');
    }
  };

  return (
    <div>
      <h1 className="page-title">Analysis History</h1>

      <div className="filters-bar">
        <input className="input" placeholder="Search by filename..." defaultValue={search} onChange={handleSearch} />
        <select className="select" value={label} onChange={(e) => { setLabel(e.target.value); setPage(1); }}>
          <option value="">All Labels</option>
          <option value="ACCEPTABLE">Acceptable</option>
          <option value="DEGRADED">Degraded</option>
          <option value="BLUR">Blur</option>
          <option value="DEFECTIVE">Defective</option>
        </select>
        <select className="select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="created_at">Sort by Date</option>
          <option value="quality_score">Sort by Score</option>
        </select>
        <select className="select" value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading"><div className="spinner"></div> Loading...</div>
      ) : !data || data.items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">&#128196;</div>
          <p>No analyses found</p>
        </div>
      ) : (
        <>
          <div className="card">
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
                  {data.items.map(a => (
                    <tr key={a.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/analysis/${a.id}`)}>
                      <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.filename}</td>
                      <td style={{ fontWeight: 600 }}>{a.quality_score}</td>
                      <td><span className={`quality-label ${a.quality_label.toLowerCase()}`}>{a.quality_label}</span></td>
                      <td>{a.issues.length > 0 ? a.issues.map(i => i.type).join(', ') : 'None'}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{new Date(a.created_at).toLocaleDateString()}</td>
                      <td>
                        <button className="btn btn-sm btn-danger" onClick={(e) => handleDelete(a.id, e)}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {data.total_pages > 1 && (
            <div className="pagination">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
              {Array.from({ length: data.total_pages }, (_, i) => i + 1).map(p => (
                <button key={p} className={p === page ? 'active' : ''} onClick={() => setPage(p)}>{p}</button>
              ))}
              <button disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}>Next</button>
            </div>
          )}

          <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px', marginTop: '12px' }}>
            Showing {data.items.length} of {data.total} results
          </p>
        </>
      )}
    </div>
  );
}
