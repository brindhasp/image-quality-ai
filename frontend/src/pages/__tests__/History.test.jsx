import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import History from '../History';

const mockData = {
  items: [
    { id: 1, filename: 'test.png', file_size: 1024, quality_score: 85.0, quality_label: 'ACCEPTABLE', issues: [], created_at: '2026-08-28T12:00:00Z' },
    { id: 2, filename: 'blurry.jpg', file_size: 2048, quality_score: 45.0, quality_label: 'DEGRADED', issues: [{ type: 'BLUR', severity: 'HIGH', confidence: 0.85, explanation: 'Low sharpness' }], created_at: '2026-08-28T13:00:00Z' },
  ],
  total: 2,
  page: 1,
  page_size: 10,
  total_pages: 1,
};

vi.mock('../../services/api', () => ({
  getAnalyses: vi.fn(),
  deleteAnalysis: vi.fn(),
}));

import { getAnalyses } from '../../services/api';

function renderWithRouter(ui) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('History Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAnalyses.mockResolvedValue(mockData);
  });

  it('shows loading state initially', () => {
    getAnalyses.mockReturnValue(new Promise(() => {}));
    renderWithRouter(<History />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders analyses table after loading', async () => {
    renderWithRouter(<History />);
    await waitFor(() => {
      expect(screen.getByText('test.png')).toBeInTheDocument();
      expect(screen.getByText('blurry.jpg')).toBeInTheDocument();
    });
  });

  it('displays quality labels', async () => {
    renderWithRouter(<History />);
    await waitFor(() => {
      expect(screen.getByText('ACCEPTABLE')).toBeInTheDocument();
      expect(screen.getByText('DEGRADED')).toBeInTheDocument();
    });
  });

  it('shows score for each analysis', async () => {
    renderWithRouter(<History />);
    await waitFor(() => {
      expect(screen.getByText('85')).toBeInTheDocument();
      expect(screen.getByText('45')).toBeInTheDocument();
    });
  });

  it('shows empty state when no results', async () => {
    getAnalyses.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10, total_pages: 0 });
    renderWithRouter(<History />);
    await waitFor(() => {
      expect(screen.getByText(/no analyses found/i)).toBeInTheDocument();
    });
  });

  it('shows error state', async () => {
    getAnalyses.mockRejectedValue(new Error('Network error'));
    renderWithRouter(<History />);
    await waitFor(() => {
      expect(screen.getByText(/failed to load history/i)).toBeInTheDocument();
    });
  });

  it('displays search input', async () => {
    renderWithRouter(<History />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search by filename/i)).toBeInTheDocument();
    });
  });

  it('displays filter dropdowns', async () => {
    renderWithRouter(<History />);
    await waitFor(() => {
      expect(screen.getByText('All Labels')).toBeInTheDocument();
      expect(screen.getByText('Sort by Date')).toBeInTheDocument();
    });
  });
});
