import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

export async function getHealth() {
  const res = await api.get('/health');
  return res.data;
}

export async function analyzeImage(file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 50));
      }
    },
    onDownloadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(50 + Math.round((e.loaded / e.total) * 50));
      }
    },
  });
  return res.data;
}

export async function getAnalyses(params = {}) {
  const res = await api.get('/analyses', { params });
  return res.data;
}

export async function getAnalysis(id) {
  const res = await api.get(`/analyses/${id}`);
  return res.data;
}

export async function deleteAnalysis(id) {
  const res = await api.delete(`/analyses/${id}`);
  return res.data;
}

export async function getStatistics() {
  const res = await api.get('/statistics');
  return res.data;
}

export default api;
