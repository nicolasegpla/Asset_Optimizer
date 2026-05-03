import type { OutputFormat } from '../constants/outputFormat';
import { PRESET_CATALOG, PRESET_IDS, applyPreset, matchPresetOrCustom } from '../hooks/usePresets';
import type { PresetId } from '../hooks/usePresets';
import { FormatGuide } from './FormatGuide';

const MAX_DIMENSION_DIGITS = 6;

function sanitizeDimensionInput(value: string): string {
  return value.replace(/\D/g, '').slice(0, MAX_DIMENSION_DIGITS);
}

interface SettingsPanelProps {
  outputFormat: OutputFormat;
  quality: number;
  maxWidth: string;
  maxHeight: string;
  zipName: string;
  outputPrefix: string;
  outputSuffix: string;
  outputStem: string;
  selectedCount: number;
  showZipName: boolean;
  showOutputStem: boolean;
  isProcessing: boolean;
  avifAvailable: boolean;
  onOutputFormatChange: (format: OutputFormat) => void;
  onQualityChange: (quality: number) => void;
  onMaxWidthChange: (width: string) => void;
  onMaxHeightChange: (height: string) => void;
  onZipNameChange: (name: string) => void;
  onOutputPrefixChange: (prefix: string) => void;
  onOutputSuffixChange: (suffix: string) => void;
  onOutputStemChange: (stem: string) => void;
  onOptimize: () => void;
}

export function SettingsPanel({
  outputFormat,
  quality,
  maxWidth,
  maxHeight,
  zipName,
  outputPrefix,
  outputSuffix,
  outputStem,
  selectedCount,
  showZipName,
  showOutputStem,
  isProcessing,
  avifAvailable,
  onOutputFormatChange,
  onQualityChange,
  onMaxWidthChange,
  onMaxHeightChange,
  onZipNameChange,
  onOutputPrefixChange,
  onOutputSuffixChange,
  onOutputStemChange,
  onOptimize,
}: SettingsPanelProps) {
  const activePreset = matchPresetOrCustom(outputFormat, quality, maxWidth, maxHeight);

  const handlePresetChange = (presetId: PresetId) => {
    if (presetId === PRESET_IDS.CUSTOM) return;
    const applied = applyPreset(presetId);
    if (!applied) return;
    onOutputFormatChange(applied.outputFormat);
    onQualityChange(applied.quality);
    onMaxWidthChange(applied.maxWidth);
    onMaxHeightChange(applied.maxHeight);
  };

  return (
    <div className="column">
      <h2>Transformation settings</h2>

      <label>
        <span>Preset</span>
        <select
          value={activePreset}
          onChange={(event) => handlePresetChange(event.target.value as PresetId)}
        >
          <option value={PRESET_IDS.CUSTOM}>Custom</option>
          {PRESET_CATALOG.map((preset) => (
            <option key={preset.id} value={preset.id}>
              {preset.label}
            </option>
          ))}
        </select>
      </label>

      {activePreset !== PRESET_IDS.CUSTOM && (() => {
        const matched = PRESET_CATALOG.find((p) => p.id === activePreset);
        return matched?.rationale ? (
          <small className="preset-rationale-hint">{matched.rationale}</small>
        ) : null;
      })()}

      <label>
        <span>Output format</span>
        <select
          value={outputFormat}
          onChange={(event) => {
            onOutputFormatChange(event.target.value as OutputFormat);
          }}
        >
          <option value="jpg">JPG</option>
          <option value="png">PNG</option>
          <option value="webp">WEBP</option>
          {avifAvailable ? (
            <option value="avif">AVIF</option>
          ) : (
            <option value="avif" disabled title="AVIF requires a server dependency — currently not installed">
              AVIF (unavailable)
            </option>
          )}
        </select>
        <FormatGuide outputFormat={outputFormat} />
      </label>

      <label>
        <span>Quality</span>
        <input
          max={100}
          min={1}
          type="range"
          value={quality}
          onChange={(event) => onQualityChange(Number(event.target.value))}
        />
        <small>{quality}%</small>
      </label>

      <div className="dimension-grid">
        <label>
          <span>Max width</span>
          <input
            inputMode="numeric"
            maxLength={MAX_DIMENSION_DIGITS}
            pattern="[0-9]*"
            placeholder="1200"
            type="text"
            value={maxWidth}
            onChange={(event) => onMaxWidthChange(sanitizeDimensionInput(event.target.value))}
          />
        </label>

        <label>
          <span>Max height</span>
          <input
            inputMode="numeric"
            maxLength={MAX_DIMENSION_DIGITS}
            pattern="[0-9]*"
            placeholder="1200"
            type="text"
            value={maxHeight}
            onChange={(event) => onMaxHeightChange(sanitizeDimensionInput(event.target.value))}
          />
        </label>
      </div>

      <div className="naming-grid">
        {showZipName && (
          <label>
            <span>ZIP name</span>
            <input
              type="text"
              placeholder="optimized-assets"
              value={zipName}
              onChange={(event) => onZipNameChange(event.target.value)}
            />
          </label>
        )}

        {showOutputStem ? (
          <label>
            <span>Output stem</span>
            <input
              type="text"
              placeholder="e.g. file (results in file-1, file-2...)"
              value={outputStem}
              onChange={(event) => onOutputStemChange(event.target.value)}
            />
          </label>
        ) : (
          <>
            <label>
              <span>Output prefix</span>
              <input
                type="text"
                placeholder="e.g. optimized_"
                value={outputPrefix}
                onChange={(event) => onOutputPrefixChange(event.target.value)}
              />
            </label>

            <label>
              <span>Output suffix</span>
              <input
                type="text"
                placeholder="e.g. _final"
                value={outputSuffix}
                onChange={(event) => onOutputSuffixChange(event.target.value)}
              />
            </label>
          </>
        )}
      </div>

      <button
        className="primary-button"
        type="button"
        disabled={!selectedCount || isProcessing}
        onClick={onOptimize}
      >
        {isProcessing ? 'Processing…' : 'Optimize & Download'}
      </button>
    </div>
  );
}
