import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function ImageUpload({ onAnalysisComplete }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.bmp', '.tiff', '.webp']
    },
    multiple: false
  });

  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(`${API_URL}/api/analyze`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      onAnalysisComplete(response.data);
    } catch (err) {
      const message = err.response?.data?.detail || 'Analysis failed. Please try again.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div
        {...getRootProps()}
        className={`upload-area ${isDragActive ? 'dragging' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="upload-icon">📷</div>
        <p className="upload-text">
          {isDragActive ? 'Drop the image here' : 'Drag & drop an image here, or click to select'}
        </p>
        <p className="upload-hint">
          Supports: JPEG, PNG, BMP, TIFF, WebP (max 10MB)
        </p>
      </div>

      {preview && (
        <div className="upload-preview">
          <img src={preview} alt="Preview" className="preview-image" />
          <button
            className="analyze-btn"
            onClick={handleAnalyze}
            disabled={loading}
          >
            {loading ? 'Analyzing...' : 'Analyze Image'}
          </button>
        </div>
      )}

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Analyzing image quality...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
    </div>
  );
}

export default ImageUpload;