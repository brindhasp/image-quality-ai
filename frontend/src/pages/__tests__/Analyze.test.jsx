import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Analyze from '../Analyze';

vi.mock('../../services/api', () => ({
  analyzeImage: vi.fn(),
}));

function renderWithRouter(ui) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('Analyze Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders upload zone initially', () => {
    renderWithRouter(<Analyze />);
    expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
    expect(screen.getByText(/browse/i)).toBeInTheDocument();
  });

  it('shows accepted file types hint', () => {
    renderWithRouter(<Analyze />);
    expect(screen.getByText(/jpg, png, webp/i)).toBeInTheDocument();
  });

  it('has a hidden file input', () => {
    renderWithRouter(<Analyze />);
    const input = document.querySelector('input[type="file"]');
    expect(input).toBeTruthy();
    expect(input.accept).toBe('.jpg,.jpeg,.png,.webp');
  });

  it('validates file type on selection', async () => {
    renderWithRouter(<Analyze />);
    const input = document.querySelector('input[type="file"]');
    const file = new File(['test'], 'test.txt', { type: 'text/plain' });
    Object.defineProperty(file, 'size', { value: 100 });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/invalid file type/i)).toBeInTheDocument();
    });
  });

  it('validates file size', async () => {
    renderWithRouter(<Analyze />);
    const input = document.querySelector('input[type="file"]');
    const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.png', { type: 'image/png' });
    Object.defineProperty(largeFile, 'size', { value: 11 * 1024 * 1024 });
    fireEvent.change(input, { target: { files: [largeFile] } });
    await waitFor(() => {
      expect(screen.getByText(/file too large/i)).toBeInTheDocument();
    });
  });

  it('shows preview when valid file is selected', async () => {
    renderWithRouter(<Analyze />);
    const input = document.querySelector('input[type="file"]');
    const file = new File(['dummy'], 'test.png', { type: 'image/png' });
    Object.defineProperty(file, 'size', { value: 1024 });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText('test.png')).toBeInTheDocument();
      expect(screen.getByText('1.0 KB')).toBeInTheDocument();
    });
  });

  it('shows analyze and remove buttons after file selection', async () => {
    renderWithRouter(<Analyze />);
    const input = document.querySelector('input[type="file"]');
    const file = new File(['dummy'], 'test.png', { type: 'image/png' });
    Object.defineProperty(file, 'size', { value: 1024 });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getAllByText('Analyze Image').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Remove')).toBeInTheDocument();
    });
  });

  it('removes file when remove button is clicked', async () => {
    renderWithRouter(<Analyze />);
    const input = document.querySelector('input[type="file"]');
    const file = new File(['dummy'], 'test.png', { type: 'image/png' });
    Object.defineProperty(file, 'size', { value: 1024 });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText('test.png')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Remove'));
    await waitFor(() => {
      expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
    });
  });
});
