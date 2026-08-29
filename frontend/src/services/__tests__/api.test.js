import { describe, it, expect, vi, beforeEach } from 'vitest';
import api, { getHealth, analyzeImage, getAnalyses, getAnalysis, deleteAnalysis, getStatistics } from '../api';

vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    defaults: { headers: { common: {} } },
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };
  return { default: mockAxios };
});

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getHealth calls /health endpoint', async () => {
    api.get.mockResolvedValue({ data: { status: 'ok' } });
    const result = await getHealth();
    expect(result).toEqual({ status: 'ok' });
    expect(api.get).toHaveBeenCalledWith('/health');
  });

  it('getAnalyses calls /analyses with params', async () => {
    const mockResponse = { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 };
    api.get.mockResolvedValue({ data: mockResponse });
    const result = await getAnalyses({ page: 1, search: 'test' });
    expect(result).toEqual(mockResponse);
    expect(api.get).toHaveBeenCalledWith('/analyses', { params: { page: 1, search: 'test' } });
  });

  it('getAnalysis calls /analyses/:id', async () => {
    const mockAnalysis = { id: 1, filename: 'test.png' };
    api.get.mockResolvedValue({ data: mockAnalysis });
    const result = await getAnalysis(1);
    expect(result).toEqual(mockAnalysis);
    expect(api.get).toHaveBeenCalledWith('/analyses/1');
  });

  it('deleteAnalysis calls DELETE /analyses/:id', async () => {
    api.delete.mockResolvedValue({ data: { message: 'deleted' } });
    const result = await deleteAnalysis(1);
    expect(result).toEqual({ message: 'deleted' });
    expect(api.delete).toHaveBeenCalledWith('/analyses/1');
  });

  it('getStatistics calls /statistics', async () => {
    const mockStats = { total_analyses: 0 };
    api.get.mockResolvedValue({ data: mockStats });
    const result = await getStatistics();
    expect(result).toEqual(mockStats);
    expect(api.get).toHaveBeenCalledWith('/statistics');
  });

  it('analyzeImage posts FormData to /analyze', async () => {
    const mockResult = { id: 1, quality_score: 85 };
    api.post.mockResolvedValue({ data: mockResult });
    const file = new File(['dummy'], 'test.png', { type: 'image/png' });
    const result = await analyzeImage(file);
    expect(result).toEqual(mockResult);
    expect(api.post).toHaveBeenCalledWith(
      '/analyze',
      expect.any(FormData),
      expect.objectContaining({
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    );
  });
});
