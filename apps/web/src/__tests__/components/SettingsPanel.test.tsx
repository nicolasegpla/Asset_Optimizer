/**
 * Tests for SettingsPanel — preset, format, quality, dimensions, and naming controls.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { SettingsPanel } from '../../components/SettingsPanel';
import type { OutputFormat } from '../../constants/outputFormat';

describe('SettingsPanel', () => {
  const defaultProps = {
    outputFormat: 'webp' as OutputFormat,
    quality: 80,
    maxWidth: '',
    maxHeight: '',
    zipName: '',
    outputPrefix: '',
    outputSuffix: '',
    outputStem: '',
    selectedCount: 2,
    showZipName: true,
    showOutputStem: false, // single-file mode by default
    isProcessing: false,
    avifAvailable: true,
    onOutputFormatChange: vi.fn(),
    onQualityChange: vi.fn(),
    onMaxWidthChange: vi.fn(),
    onMaxHeightChange: vi.fn(),
    onZipNameChange: vi.fn(),
    onOutputPrefixChange: vi.fn(),
    onOutputSuffixChange: vi.fn(),
    onOutputStemChange: vi.fn(),
    onOptimize: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders all input groups: preset, format, quality, dimensions, naming, button', () => {
    render(<SettingsPanel {...defaultProps} />);
    expect(screen.getByText('Transformation settings')).toBeTruthy();
    expect(screen.getByText('Preset')).toBeTruthy();
    expect(screen.getByText('Output format')).toBeTruthy();
    expect(screen.getByText('Quality')).toBeTruthy();
    expect(screen.getByText('Max width')).toBeTruthy();
    expect(screen.getByText('Max height')).toBeTruthy();
    // single-file mode: prefix/suffix shown
    expect(screen.getByText('Output prefix')).toBeTruthy();
    expect(screen.getByText('Output suffix')).toBeTruthy();
    expect(screen.getByRole('button', { name: /optimize/i })).toBeTruthy();
  });

  it('naming fields default to empty strings (single-file mode)', () => {
    render(<SettingsPanel {...defaultProps} />);
    const inputs = screen.getAllByRole('textbox');
    const namingInputs = inputs.filter((input) => {
      const label = input.closest('label');
      if (!label) return false;
      const span = label.querySelector('span');
      if (!span) return false;
      return ['Output prefix', 'Output suffix'].includes(span.textContent ?? '');
    });
    expect(namingInputs).toHaveLength(2);
    namingInputs.forEach((input) => {
      expect((input as HTMLInputElement).value).toBe('');
    });
  });

  it('batch mode: shows output stem instead of prefix/suffix', () => {
    render(<SettingsPanel {...defaultProps} showOutputStem={true} />);
    expect(screen.getByText('Output stem')).toBeTruthy();
    // prefix and suffix must not appear in batch mode
    expect(screen.queryByText('Output prefix')).toBeNull();
    expect(screen.queryByText('Output suffix')).toBeNull();
  });

  it('batch mode: shows ZIP name too', () => {
    render(<SettingsPanel {...defaultProps} showOutputStem={true} showZipName={true} />);
    expect(screen.getByText('ZIP name')).toBeTruthy();
    expect(screen.getByText('Output stem')).toBeTruthy();
  });

  it('calls onZipNameChange when ZIP name field is edited', () => {
    render(<SettingsPanel {...defaultProps} showZipName={true} />);
    const zipInput = screen.getByPlaceholderText('optimized-assets');
    fireEvent.change(zipInput, { target: { value: 'my-assets' } });
    expect(defaultProps.onZipNameChange).toHaveBeenCalledWith('my-assets');
  });

  it('calls onOutputPrefixChange when output prefix field is edited (single-file)', () => {
    render(<SettingsPanel {...defaultProps} showOutputStem={false} />);
    const prefixInput = screen.getByPlaceholderText('e.g. optimized_');
    fireEvent.change(prefixInput, { target: { value: 'opt_' } });
    expect(defaultProps.onOutputPrefixChange).toHaveBeenCalledWith('opt_');
  });

  it('calls onOutputSuffixChange when output suffix field is edited (single-file)', () => {
    render(<SettingsPanel {...defaultProps} showOutputStem={false} />);
    const suffixInput = screen.getByPlaceholderText('e.g. _final');
    fireEvent.change(suffixInput, { target: { value: '_final' } });
    expect(defaultProps.onOutputSuffixChange).toHaveBeenCalledWith('_final');
  });

  it('calls onOutputStemChange when output stem field is edited (batch)', () => {
    render(<SettingsPanel {...defaultProps} showOutputStem={true} />);
    const stemInput = screen.getByPlaceholderText(/results in file-1, file-2/);
    fireEvent.change(stemInput, { target: { value: 'catalog' } });
    expect(defaultProps.onOutputStemChange).toHaveBeenCalledWith('catalog');
  });

  it('naming fields default to empty strings', () => {
    render(<SettingsPanel {...defaultProps} />);
    const inputs = screen.getAllByRole('textbox');
    const namingInputs = inputs.filter((input) => {
      // Filter to the three naming text inputs by finding ones with empty value and matching labels
      const label = input.closest('label');
      if (!label) return false;
      const span = label.querySelector('span');
      if (!span) return false;
      return ['ZIP name', 'Output prefix', 'Output suffix'].includes(span.textContent ?? '');
    });
    expect(namingInputs).toHaveLength(3);
    namingInputs.forEach((input) => {
      expect((input as HTMLInputElement).value).toBe('');
    });
  });

  it('calls onZipNameChange when ZIP name field is edited', () => {
    render(<SettingsPanel {...defaultProps} />);
    const zipInput = screen.getByPlaceholderText('optimized-assets');
    fireEvent.change(zipInput, { target: { value: 'my-assets' } });
    expect(defaultProps.onZipNameChange).toHaveBeenCalledWith('my-assets');
  });

  it('calls onOutputPrefixChange when output prefix field is edited', () => {
    render(<SettingsPanel {...defaultProps} />);
    const prefixInput = screen.getByPlaceholderText('e.g. optimized_');
    fireEvent.change(prefixInput, { target: { value: 'opt_' } });
    expect(defaultProps.onOutputPrefixChange).toHaveBeenCalledWith('opt_');
  });

  it('calls onOutputSuffixChange when output suffix field is edited', () => {
    render(<SettingsPanel {...defaultProps} />);
    const suffixInput = screen.getByPlaceholderText('e.g. _final');
    fireEvent.change(suffixInput, { target: { value: '_final' } });
    expect(defaultProps.onOutputSuffixChange).toHaveBeenCalledWith('_final');
  });

  it('hides ZIP name when batch zip naming is not applicable', () => {
    render(<SettingsPanel {...defaultProps} showZipName={false} />);
    expect(screen.queryByText('ZIP name')).toBeNull();
    expect(screen.queryByPlaceholderText('optimized-assets')).toBeNull();
  });

  it('disables Optimize button when isProcessing is true', () => {
    render(<SettingsPanel {...defaultProps} isProcessing={true} />);
    expect(screen.getByRole('button', { name: /processing/i })).toHaveProperty('disabled', true);
  });

  it('disables Optimize button when selectedCount is 0', () => {
    render(<SettingsPanel {...defaultProps} selectedCount={0} />);
    expect(screen.getByRole('button', { name: /optimize/i })).toHaveProperty('disabled', true);
  });

  it('calls onOptimize when Optimize button is clicked', () => {
    render(<SettingsPanel {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /optimize/i }));
    expect(defaultProps.onOptimize).toHaveBeenCalledTimes(1);
  });

  it('renders AVIF option as unavailable when avifAvailable is false', () => {
    render(<SettingsPanel {...defaultProps} avifAvailable={false} />);
    const avifOption = screen.getByRole('option', { name: /avif \(unavailable\)/i });
    expect(avifOption).toBeTruthy();
    expect(avifOption).toHaveProperty('disabled', true);
    expect(avifOption.getAttribute('title')).toBe('AVIF requires a server dependency — currently not installed');
  });

  it('shows preset rationale hint when a preset is active', () => {
    render(<SettingsPanel {...defaultProps} outputFormat="webp" quality={80} maxWidth="1200" maxHeight="1200" />);
    expect(screen.getByText('WebP — best compression for product images')).toBeTruthy();
  });

  it('does not show rationale hint when Custom is active', () => {
    render(<SettingsPanel {...defaultProps} outputFormat="png" quality={90} maxWidth="999" maxHeight="999" />);
    expect(screen.queryByText(/—/)).toBeNull();
  });

  it('renders FormatGuide below the format selector', () => {
    render(<SettingsPanel {...defaultProps} outputFormat="jpg" />);
    expect(screen.getByText('Format guidance: JPG')).toBeTruthy();
  });

  it('FormatGuide summary is clickable and expands', () => {
    render(<SettingsPanel {...defaultProps} outputFormat="webp" />);
    const summary = screen.getByText('Format guidance: WebP');
    fireEvent.click(summary);
    expect(screen.getByText(/Best for:/)).toBeTruthy();
  });
});
