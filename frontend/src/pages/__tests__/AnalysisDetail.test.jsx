import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter, Route, Routes } from 'react-router-dom';
import AnalysisDetail from '../AnalysisDetail';

const mockAnalysis = {
  id: 1,
  filename: 'test.png',
  quality_score: 82.0,
  quality_label: 'ACCEPTABLE',
  issues: [
    { type: 'BLUR', severity: 'LOW', confidence: 0.35, explanation: 'Sharpness score is 180.0, borderline.' },
  ],
  statistics: {
    width: 256,
    height: 256,
    sharpness: 180.0,
    brightness: 128.5,
    contrast: 52.1,
    noise: 15.3,
    dark_pixel_ratio: 0.02,
    bright_pixel_ratio: 0.01,
    saturation_ratio: 0.01,
    edge_density: 0.16,
  },
  model: { name: 'RandomForestClassifier', version: '1.0' },
  created_at: '2026-08-28T12:00:00Z',
};

vi.mock('../../services/api', () => ({
  getAnalysis: vi.fn(),
  deleteAnalysis: vi.fn(),
}));

import { getAnalysis } from '../../services/api';

function renderDetail(id = '1') {
  return render(
    <MemoryRouter initialEntries={[`/analysis/${id}`]}>
      <Routes>
        <Route path="/analysis/:id" element={<AnalysisDetail />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AnalysisDetail Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state', () => {
    getAnalysis.mockReturnValue(new Promise(() => {}));
    renderDetail();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders analysis details after loading', async () => {
    getAnalysis.mockResolvedValue(mockAnalysis);
    renderDetail();
    await waitFor(() => {
      expect(screen.getByText('82')).toBeInTheDocument();
      expect(screen.getByText('ACCEPTABLE')).toBeInTheDocument();
      expect(screen.getByText('test.png')).toBeInTheDocument();
    });
  });

  it('displays issues', async () => {
    getAnalysis.mockResolvedValue(mockAnalysis);
    renderDetail();
    await waitFor(() => {
      expect(screen.getByText('BLUR')).toBeInTheDocument();
      expect(screen.getByText(/35%/)).toBeInTheDocument();
    });
  });

  it('displays statistics', async () => {
    getAnalysis.mockResolvedValue(mockAnalysis);
    renderDetail();
    await waitFor(() => {
      expect(screen.getByText('180.0')).toBeInTheDocument();
      expect(screen.getByText('256 x 256')).toBeInTheDocument();
    });
  });

  it('displays model info', async () => {
    getAnalysis.mockResolvedValue(mockAnalysis);
    renderDetail();
    await waitFor(() => {
      expect(screen.getByText(/RandomForestClassifier v1.0/)).toBeInTheDocument();
    });
  });

  it('shows error state', async () => {
    getAnalysis.mockRejectedValue(new Error('Not found'));
    renderDetail();
    await waitFor(() => {
      expect(screen.getByText(/failed to load analysis/i)).toBeInTheDocument();
    });
  });

  it('has delete button', async () => {
    getAnalysis.mockResolvedValue(mockAnalysis);
    renderDetail();
    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument();
    });
  });

  it('has back button', async () => {
    getAnalysis.mockResolvedValue(mockAnalysis);
    renderDetail();
    await waitFor(() => {
      expect(screen.getByText('Back')).toBeInTheDocument();
    });
  });
});
