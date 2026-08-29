import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';

const mockStats = {
  total_analyses: 5,
  average_score: 72.5,
  acceptable_count: 3,
  degraded_count: 1,
  defective_count: 1,
  most_common_issue: 'BLUR',
  label_distribution: { ACCEPTABLE: 3, DEGRADED: 1, POTENTIALLY_DEFECTIVE: 1 },
  issue_distribution: { BLUR: 2, NOISE: 1 },
  recent_analyses: [
    { id: 1, filename: 'img1.png', quality_score: 85, quality_label: 'ACCEPTABLE', issues: [], created_at: '2026-08-28T12:00:00Z' },
    { id: 2, filename: 'img2.png', quality_score: 45, quality_label: 'DEGRADED', issues: [{ type: 'BLUR' }], created_at: '2026-08-28T13:00:00Z' },
  ],
};

vi.mock('../../services/api', () => ({
  getStatistics: vi.fn(),
}));

import { getStatistics } from '../../services/api';

function renderWithRouter(ui) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('Dashboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state', () => {
    getStatistics.mockReturnValue(new Promise(() => {}));
    renderWithRouter(<Dashboard />);
    expect(screen.getByText(/loading dashboard/i)).toBeInTheDocument();
  });

  it('renders statistics cards after loading', async () => {
    getStatistics.mockResolvedValue(mockStats);
    renderWithRouter(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('72.5')).toBeInTheDocument();
      expect(screen.getByText('Total Analyzed')).toBeInTheDocument();
      expect(screen.getByText('Avg Quality Score')).toBeInTheDocument();
    });
  });

  it('shows label counts', async () => {
    getStatistics.mockResolvedValue(mockStats);
    renderWithRouter(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(2);
    });
  });

  it('shows most common issue', async () => {
    getStatistics.mockResolvedValue(mockStats);
    renderWithRouter(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('BLUR')).toBeInTheDocument();
    });
  });

  it('shows recent analyses', async () => {
    getStatistics.mockResolvedValue(mockStats);
    renderWithRouter(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('img1.png')).toBeInTheDocument();
      expect(screen.getByText('img2.png')).toBeInTheDocument();
    });
  });

  it('shows empty state when no analyses', async () => {
    getStatistics.mockResolvedValue({
      ...mockStats,
      total_analyses: 0,
      recent_analyses: [],
      label_distribution: {},
      issue_distribution: {},
    });
    renderWithRouter(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText(/no analyses yet/i)).toBeInTheDocument();
    });
  });

  it('shows error state', async () => {
    getStatistics.mockRejectedValue(new Error('Network error'));
    renderWithRouter(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText(/failed to load statistics/i)).toBeInTheDocument();
    });
  });
});
