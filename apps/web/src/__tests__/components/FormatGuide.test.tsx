/**
 * Tests for FormatGuide component — disclosure rendering, format swaps, AVIF cautions, JPG transparency warning.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { FormatGuide } from '../../components/FormatGuide';
import type { OutputFormat } from '../../constants/outputFormat';

describe('FormatGuide', () => {
  beforeEach(() => {
    cleanup();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders collapsed by default with format guidance summary', () => {
    render(<FormatGuide outputFormat="webp" />);
    const summary = screen.getByText('Format guidance: WebP');
    expect(summary).toBeTruthy();
  });

  it('shows best-for, transparency, browser support when expanded', () => {
    render(<FormatGuide outputFormat="webp" />);
    const summary = screen.getByText('Format guidance: WebP');
    fireEvent.click(summary);

    expect(screen.getByText(/Best for:/)).toBeTruthy();
    expect(screen.getByText('Transparency ✦')).toBeTruthy();
    expect(screen.getByText(/Browser support:/)).toBeTruthy();
  });

  it('shows "No transparency" badge for JPG format', () => {
    render(<FormatGuide outputFormat="jpg" />);
    const summary = screen.getByText('Format guidance: JPG');
    fireEvent.click(summary);
    expect(screen.getByText('No transparency')).toBeTruthy();
  });

  it('shows transparency badge for PNG format', () => {
    render(<FormatGuide outputFormat="png" />);
    const summary = screen.getByText('Format guidance: PNG');
    fireEvent.click(summary);
    expect(screen.getByText('Transparency ✦')).toBeTruthy();
  });

  it('JPG shows caution about transparent areas becoming white', () => {
    render(<FormatGuide outputFormat="jpg" />);
    const summary = screen.getByText('Format guidance: JPG');
    fireEvent.click(summary);
    expect(screen.getByText(/transparent areas become solid white/i)).toBeTruthy();
  });

  it('PNG shows no cautions', () => {
    render(<FormatGuide outputFormat="png" />);
    const summary = screen.getByText('Format guidance: PNG');
    fireEvent.click(summary);
    expect(screen.queryByText(/caution/i)).toBeNull();
  });

  it('AVIF shows encoding and browser support cautions when expanded', () => {
    render(<FormatGuide outputFormat="avif" />);
    const summary = screen.getByText('Format guidance: AVIF');
    fireEvent.click(summary);
    expect(screen.getByText(/Encoding is slower/i)).toBeTruthy();
    expect(screen.getByText(/Browser support is growing/i)).toBeTruthy();
  });

  it('content updates when format prop changes', () => {
    const { rerender } = render(<FormatGuide outputFormat="webp" />);
    expect(screen.getByText('Format guidance: WebP')).toBeTruthy();

    rerender(<FormatGuide outputFormat="jpg" />);
    expect(screen.getByText('Format guidance: JPG')).toBeTruthy();
  });
});
