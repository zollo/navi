import { useId, useRef, useState } from "react";
import { LuCheck, LuImagePlus, LuRotateCcw } from "react-icons/lu";
import { api } from "../api/client";
import {
  AVATAR_BORDER_KINDS,
  AVATAR_SHAPES,
  BUTTON_SHAPES,
  BUTTON_STYLES,
  COLOR_PRESETS,
  DEFAULT_THEME,
  FONTS,
  GRADIENT_PRESETS,
  THEME_PRESETS,
  themeStyle,
  withAvatarBorderKind,
  withBackgroundKind,
} from "../lib/theme";
import type {
  AvatarBorder,
  Background,
  BackgroundKind,
  ContentPanel,
  FontName,
  PageTheme,
  ThemeBackground,
} from "../types";

// A row of toggle buttons for picking one of a few options.
function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={value === o.value ? "on" : ""}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// Gradient preset swatches.
function GradientPresets({ onPick }: { onPick: (from: string, to: string) => void }) {
  return (
    <div className="gradient-presets">
      {GRADIENT_PRESETS.map(([a, b]) => (
        <button
          key={a + b}
          type="button"
          className="swatch wide"
          style={{ background: `linear-gradient(135deg, ${a}, ${b})` }}
          aria-label={`Gradient ${a} to ${b}`}
          onClick={() => onPick(a, b)}
        />
      ))}
    </div>
  );
}

// A color picker with a hex field. With `auto`, null means "pick for me".
function ColorField({
  label,
  value,
  onChange,
  auto = false,
  fallback = "#ffffff",
}: {
  label: string;
  value: string | null;
  onChange: (v: string | null) => void;
  auto?: boolean;
  fallback?: string;
}) {
  const id = useId();
  const [text, setText] = useState<string | null>(null);
  const shown = value ?? fallback;
  return (
    <div className="field color-field">
      <label htmlFor={id}>{label}</label>
      <div className="row">
        {auto && (
          <label className="check">
            <input type="checkbox" checked={value === null} onChange={(e) => onChange(e.target.checked ? null : fallback)} />
            Automatic
          </label>
        )}
        {(!auto || value !== null) && (
          <>
            <input
              id={id}
              type="color"
              value={shown}
              onChange={(e) => {
                setText(null);
                onChange(e.target.value);
              }}
            />
            <input
              type="text"
              className="hex"
              aria-label={`${label} (hex)`}
              maxLength={7}
              value={text ?? shown}
              onChange={(e) => {
                const v = e.target.value.trim();
                setText(v);
                if (/^#[0-9a-fA-F]{6}$/.test(v)) onChange(v.toLowerCase());
              }}
              onBlur={() => setText(null)}
            />
          </>
        )}
      </div>
    </div>
  );
}

function Swatches({ colors, onPick, label }: { colors: string[]; onPick: (c: string) => void; label: string }) {
  return (
    <div className="swatches" aria-label={label}>
      {colors.map((c) => (
        <button key={c} type="button" className="swatch" style={{ background: c }} aria-label={c} title={c} onClick={() => onPick(c)} />
      ))}
    </div>
  );
}

const BACKGROUND_KINDS: { value: BackgroundKind; label: string }[] = [
  { value: "default", label: "Default" },
  { value: "solid", label: "Color" },
  { value: "gradient", label: "Gradient" },
  { value: "image", label: "Image" },
  { value: "curated", label: "Gallery" },
];

interface Props {
  theme: PageTheme;
  onChange: (theme: PageTheme) => void;
  // The page's own uploaded background image, if any.
  customBackgroundUrl: string | null;
  onUploadBackground: (file: File) => void;
  onRemoveBackground: () => void;
  uploading: boolean;
  gallery: Background[];
}

// The "Appearance" card of the editor: presets, background, content panel, fonts,
// colors, button shapes and the profile photo's shape and border. Changes show in the live preview and save with the page.
export default function ThemeEditor({
  theme,
  onChange,
  customBackgroundUrl,
  onUploadBackground,
  onRemoveBackground,
  uploading,
  gallery,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const bg = theme.background;
  const set = (patch: Partial<PageTheme>) => onChange({ ...theme, ...patch });
  const setBg = (patch: Partial<ThemeBackground>) => onChange({ ...theme, background: { ...bg, ...patch } });
  const border = theme.avatar_border;
  const setBorder = (patch: Partial<AvatarBorder>) => onChange({ ...theme, avatar_border: { ...border, ...patch } });
  const panel = theme.content;
  const setPanel = (patch: Partial<ContentPanel>) => onChange({ ...theme, content: { ...panel, ...patch } });

  const pickKind = (kind: BackgroundKind) => {
    if (kind === "image" && !customBackgroundUrl) {
      fileRef.current?.click();
      return;
    }
    if (kind === "curated" && !bg.curated_id && gallery.length) {
      const first = gallery[0];
      onChange({ ...theme, background: { ...bg, kind, curated_id: first.id, image_dark: first.dark } });
      return;
    }
    onChange(withBackgroundKind(theme, kind));
  };

  return (
    <div className="card theme-editor">
      <div className="card-head">
        <h2>Appearance</h2>
        <button type="button" className="btn ghost small" onClick={() => onChange(DEFAULT_THEME)}>
          <LuRotateCcw aria-hidden /> Reset
        </button>
      </div>

      <h3>Themes</h3>
      <div className="preset-grid">
        {THEME_PRESETS.map((p) => (
          <button
            key={p.name}
            type="button"
            className="preset"
            onClick={() => onChange(p.theme)}
            style={themeStyle(p.theme, null)}
          >
            <span className="preset-bg" aria-hidden />
            <span className="preset-btn" aria-hidden />
            <span className="preset-btn" aria-hidden />
            <span className="preset-name">{p.name}</span>
          </button>
        ))}
      </div>

      <h3>Background</h3>
      <Segmented
        label="Background"
        options={BACKGROUND_KINDS.filter((k) => k.value !== "curated" || gallery.length > 0 || bg.kind === "curated")}
        value={bg.kind}
        onChange={pickKind}
      />
      <input
        ref={fileRef}
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onUploadBackground(f);
          e.target.value = "";
        }}
      />

      {bg.kind === "solid" && (
        <div className="theme-sub">
          <ColorField label="Color" value={bg.color} onChange={(color) => setBg({ color })} />
          <Swatches label="Suggested colors" colors={COLOR_PRESETS} onPick={(color) => setBg({ color })} />
        </div>
      )}

      {bg.kind === "gradient" && (
        <div className="theme-sub">
          <GradientPresets onPick={(gradient_from, gradient_to) => setBg({ gradient_from, gradient_to })} />
          <div className="grid two">
            <ColorField label="From" value={bg.gradient_from} onChange={(gradient_from) => setBg({ gradient_from })} />
            <ColorField label="To" value={bg.gradient_to} onChange={(gradient_to) => setBg({ gradient_to })} />
          </div>
          <div className="field">
            <label htmlFor="gradient-angle">Direction: {bg.gradient_angle}°</label>
            <input
              id="gradient-angle"
              type="range"
              min={0}
              max={360}
              step={5}
              value={bg.gradient_angle}
              onChange={(e) => setBg({ gradient_angle: Number(e.target.value) })}
            />
          </div>
        </div>
      )}

      {bg.kind === "image" && (
        <div className="theme-sub">
          <div className="bg-upload">
            {customBackgroundUrl && (
              <img className="bg-thumb" src={api.baseUrl + customBackgroundUrl} alt="Your background" />
            )}
            <div className="row">
              <button type="button" className="btn secondary small" disabled={uploading} onClick={() => fileRef.current?.click()}>
                <LuImagePlus aria-hidden /> {uploading ? "Uploading…" : customBackgroundUrl ? "Replace image" : "Upload image"}
              </button>
              {customBackgroundUrl && (
                <button type="button" className="btn ghost small" onClick={onRemoveBackground}>
                  Remove
                </button>
              )}
            </div>
          </div>
          <p className="muted small">Large photos are resized in your browser before upload.</p>
          <label className="check">
            <input type="checkbox" checked={bg.image_dark} onChange={(e) => setBg({ image_dark: e.target.checked })} />
            Dark image (use light text)
          </label>
        </div>
      )}

      {bg.kind === "curated" && (
        <div className="theme-sub">
          {gallery.length === 0 ? (
            <p className="muted small">The gallery is empty.</p>
          ) : (
            <div className="gallery-grid" role="radiogroup" aria-label="Gallery backgrounds">
              {gallery.map((g) => (
                <button
                  key={g.id}
                  type="button"
                  role="radio"
                  aria-checked={bg.curated_id === g.id}
                  className={`gallery-item ${bg.curated_id === g.id ? "on" : ""}`}
                  onClick={() => setBg({ curated_id: g.id, image_dark: g.dark })}
                >
                  <img src={api.baseUrl + g.image_url} alt="" loading="lazy" />
                  <span>{g.name}</span>
                  {bg.curated_id === g.id && <LuCheck className="tick" aria-hidden />}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <h3>Content panel</h3>
      <label className="check">
        <input type="checkbox" checked={panel.enabled} onChange={(e) => setPanel({ enabled: e.target.checked })} />
        Show a panel behind your profile and links
      </label>
      {panel.enabled && (
        <div className="theme-sub">
          <ColorField label="Panel color" value={panel.color} onChange={(color) => setPanel({ color: color ?? "#ffffff" })} />
          <Swatches label="Suggested panel colors" colors={COLOR_PRESETS} onPick={(color) => setPanel({ color })} />
          <div className="field">
            <label htmlFor="panel-opacity">Opacity: {panel.opacity}%</label>
            <input
              id="panel-opacity"
              type="range"
              min={0}
              max={100}
              step={5}
              value={panel.opacity}
              onChange={(e) => setPanel({ opacity: Number(e.target.value) })}
            />
            <p className="muted small">Lower it to let the page background show through.</p>
          </div>
        </div>
      )}

      <h3>Text</h3>
      <div className="grid two">
        <div className="field">
          <label htmlFor="theme-font">Font</label>
          <select id="theme-font" value={theme.font} onChange={(e) => set({ font: e.target.value as FontName })}>
            {(Object.keys(FONTS) as FontName[]).map((f) => (
              <option key={f} value={f} style={{ fontFamily: FONTS[f].stack }}>
                {FONTS[f].label}
              </option>
            ))}
          </select>
        </div>
        <ColorField label="Text color" auto value={theme.text_color} onChange={(text_color) => set({ text_color })} fallback="#111318" />
      </div>

      <h3>Link buttons</h3>
      <div className="field">
        <label>Style</label>
        <Segmented label="Button style" options={BUTTON_STYLES} value={theme.button_style} onChange={(button_style) => set({ button_style })} />
      </div>
      <div className="field">
        <label>Shape</label>
        <Segmented label="Button shape" options={BUTTON_SHAPES} value={theme.button_shape} onChange={(button_shape) => set({ button_shape })} />
      </div>
      <div className="grid two">
        <ColorField
          label={theme.button_style === "outline" ? "Border color" : "Button color"}
          auto
          value={theme.button_color}
          onChange={(button_color) => set({ button_color })}
        />
        <ColorField
          label="Button text"
          auto
          value={theme.button_text_color}
          onChange={(button_text_color) => set({ button_text_color })}
          fallback="#111318"
        />
      </div>

      <h3>Profile photo</h3>
      <div className="field">
        <label>Shape</label>
        <Segmented label="Profile photo shape" options={AVATAR_SHAPES} value={theme.avatar_shape} onChange={(avatar_shape) => set({ avatar_shape })} />
      </div>
      <div className="field">
        <label>Border</label>
        <Segmented
          label="Profile photo border"
          options={AVATAR_BORDER_KINDS}
          value={border.kind}
          onChange={(kind) => onChange(withAvatarBorderKind(theme, kind))}
        />
      </div>
      {border.kind !== "none" && (
        <div className="theme-sub">
          {border.kind === "solid" && (
            <>
              <ColorField label="Border color" value={border.color} onChange={(color) => setBorder({ color })} />
              <Swatches label="Suggested border colors" colors={COLOR_PRESETS} onPick={(color) => setBorder({ color })} />
            </>
          )}
          {border.kind === "gradient" && (
            <>
              <GradientPresets onPick={(gradient_from, gradient_to) => setBorder({ gradient_from, gradient_to })} />
              <div className="grid two">
                <ColorField label="From" value={border.gradient_from} onChange={(gradient_from) => setBorder({ gradient_from })} />
                <ColorField label="To" value={border.gradient_to} onChange={(gradient_to) => setBorder({ gradient_to })} />
              </div>
              <div className="field">
                <label htmlFor="border-angle">Direction: {border.gradient_angle}°</label>
                <input
                  id="border-angle"
                  type="range"
                  min={0}
                  max={360}
                  step={5}
                  value={border.gradient_angle}
                  onChange={(e) => setBorder({ gradient_angle: Number(e.target.value) })}
                />
              </div>
            </>
          )}
          <div className="field">
            <label htmlFor="border-width">Thickness: {border.width}px</label>
            <input
              id="border-width"
              type="range"
              min={1}
              max={12}
              step={1}
              value={border.width}
              onChange={(e) => setBorder({ width: Number(e.target.value) })}
            />
          </div>
        </div>
      )}
    </div>
  );
}
