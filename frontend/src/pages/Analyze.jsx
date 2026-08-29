import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyzeImage } from '../services/api';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const ACCEPTED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp'];
const MAX_SIZE_MB = 10;

export default function Analyze() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dimensions, setDimensions] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const handleFile = useCallback((f) => {
    setError(null);
    setDimensions(null);
    if (!f) return;

    const ext = f.name.split('.').pop().toLowerCase();
    if (!ACCEPTED_TYPES.includes(f.type) && !ACCEPTED_EXTENSIONS.includes(ext)) {
      setError(`Invalid file type: ${f.type || ext || 'unknown'}. Accepted: JPG, PNG, WEBP`);
      return;
    }
    if (f.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`File too large: ${(f.size / 1024 / 1024).toFixed(1)}MB. Maximum: ${MAX_SIZE_MB}MB`);
      return;
    }

    setFile(f);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    handleFile(f);
  }, [handleFile]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => setDragOver(false), []);

  const removeFile = () => {
    setFile(null);
    setPreview(null);
    setDimensions(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setAnalyzing(true);
    setProgress(0);
    setError(null);

    try {
      const result = await analyzeImage(file, setProgress);
      navigate(`/analysis/${result.id}`);
    } catch (err) {
      let msg = 'Analysis failed. Please try again.';
      if (err.response) {
        msg = err.response.data?.detail || `Server error (${err.response.status})`;
      } else if (err.request) {
        msg = 'Cannot connect to backend. Make sure the server is running on port 8000.';
      } else {
        msg = err.message || msg;
      }
      setError(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  const formatSize = (bytes) => {
    if (!bytes && bytes !== 0) return 'Unknown';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  };

  return (
    <div>
      <h1 className="page-title">Analyze Image</h1>

      {error && <div className="error-message">{error}</div>}

      {!file ? (
        <div
          className={`upload-zone ${dragOver ? 'dragover' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => inputRef.current?.click()}
        >
          <div className="upload-icon">&#128444;</div>
          <div className="upload-text">Drag and drop an image here, or click to browse</div>
          <div className="upload-hint">Supports JPG, PNG, WEBP up to {MAX_SIZE_MB}MB</div>
          <input
            ref={inputRef}
            type="file"
            accept=".jpg,.jpeg,.png,.webp"
            style={{ display: 'none' }}
            onChange={(e) => handleFile(e.target.files[0])}
          />
        </div>
      ) : (
        <div className="card">
          <div className="preview-container">
            <img src={preview} alt="Preview" className="preview-image" />
            <div className="preview-info">
              <h3>File Information</h3>
              <p><strong>Name:</strong> {file.name}</p>
              <p><strong>Type:</strong> {file.type}</p>
              <p><strong>Size:</strong> {formatSize(file.size)}</p>
              {preview && !dimensions && (
                <img
                  src={preview}
                  alt=""
                  style={{ display: 'none' }}
                  onLoad={(e) => {
                    setDimensions({ width: e.target.naturalWidth, height: e.target.naturalHeight });
                  }}
                />
              )}
              {dimensions && <p><strong>Dimensions:</strong> {dimensions.width} x {dimensions.height}</p>}

              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <button className="btn btn-primary" onClick={handleAnalyze} disabled={analyzing}>
                  {analyzing ? 'Analyzing...' : 'Analyze Image'}
                </button>
                <button className="btn btn-secondary" onClick={removeFile} disabled={analyzing}>Remove</button>
              </div>

              {analyzing && (
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
