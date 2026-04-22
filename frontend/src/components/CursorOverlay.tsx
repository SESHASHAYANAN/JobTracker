/* ═══════════════════════════════════════════════════════════════
   CursorOverlay — Animated cursor, click ripple, and element
   highlight overlay for the BrowserViewer automation panel.
   Renders on top of the browser viewport canvas to visualise
   where the automation agent is clicking and typing.
   ═══════════════════════════════════════════════════════════════ */
import { useState, useCallback, useRef } from 'react';

/* ── Types ────────────────────────────────────────────────────── */
export interface CursorPosition {
  x: number;
  y: number;
}

export interface ClickRipple {
  id: number;
  x: number;
  y: number;
}

export interface HighlightRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface CursorOverlayProps {
  /** Current cursor x/y inside the viewport (px) */
  cursorX: number;
  cursorY: number;
  /** Whether the cursor should be visible (automation running) */
  visible: boolean;
  /** Active click ripples */
  ripples: ClickRipple[];
  /** Optional element highlight rectangle */
  highlight: HighlightRect | null;
  /** Cursor color accent */
  accentColor?: string;
}

/* ── Component ────────────────────────────────────────────────── */
export default function CursorOverlay({
  cursorX,
  cursorY,
  visible,
  ripples,
  highlight,
  accentColor = '#14b8a6',
}: CursorOverlayProps) {
  return (
    <div className="cursor-overlay" style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
      {/* ── Animated Cursor ──────────────────────────────── */}
      {visible && (
        <div
          className="cursor-overlay-pointer"
          style={{
            position: 'absolute',
            transform: `translate(${cursorX}px, ${cursorY}px)`,
            transition: 'transform 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
            zIndex: 10,
            willChange: 'transform',
          }}
        >
          {/* SVG Cursor Arrow */}
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path
              d="M5 3l14 9-6 1-4 6z"
              fill={accentColor}
              stroke={darkenColor(accentColor)}
              strokeWidth="1.5"
            />
          </svg>
          {/* Glow ring around cursor */}
          <div
            style={{
              position: 'absolute',
              top: -4,
              left: -4,
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: `radial-gradient(circle, ${accentColor}33 0%, transparent 70%)`,
              animation: 'cursorGlow 1.5s ease-in-out infinite',
            }}
          />
        </div>
      )}

      {/* ── Click Ripples ────────────────────────────────── */}
      {ripples.map((r) => (
        <div
          key={r.id}
          className="cursor-overlay-ripple"
          style={{
            position: 'absolute',
            left: r.x,
            top: r.y,
            width: 0,
            height: 0,
            borderRadius: '50%',
            border: `2px solid ${accentColor}`,
            transform: 'translate(-50%, -50%)',
            animation: 'clickRippleExpand 0.6s ease-out forwards',
            pointerEvents: 'none',
            zIndex: 8,
          }}
        />
      ))}

      {/* ── Element Highlight Ring ────────────────────────── */}
      {highlight && (
        <div
          className="cursor-overlay-highlight"
          style={{
            position: 'absolute',
            left: highlight.x,
            top: highlight.y,
            width: highlight.w,
            height: highlight.h,
            borderRadius: 4,
            border: `2px solid ${accentColor}`,
            background: `${accentColor}0d`,
            animation: 'highlightPulse 0.6s ease-out forwards',
            pointerEvents: 'none',
            zIndex: 7,
          }}
        />
      )}

      {/* ── Inline Keyframes (scoped via style tag) ─────── */}
      <style>{`
        @keyframes cursorGlow {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50%      { opacity: 0.8; transform: scale(1.2); }
        }
        @keyframes clickRippleExpand {
          0%   { width: 0; height: 0; opacity: 1; }
          100% { width: 40px; height: 40px; opacity: 0; }
        }
        @keyframes highlightPulse {
          0%   { opacity: 1; box-shadow: 0 0 0 0 ${accentColor}40; }
          100% { opacity: 0; box-shadow: 0 0 0 8px ${accentColor}00; }
        }
      `}</style>
    </div>
  );
}

/* ── Hooks for managing ripples ───────────────────────────────── */

/** Hook to manage click ripple state with auto-cleanup */
export function useClickRipples(duration = 600) {
  const [ripples, setRipples] = useState<ClickRipple[]>([]);
  const idRef = useRef(0);

  const addRipple = useCallback(
    (x: number, y: number) => {
      const id = idRef.current++;
      setRipples((prev) => [...prev, { id, x, y }]);
      setTimeout(() => {
        setRipples((prev) => prev.filter((r) => r.id !== id));
      }, duration);
    },
    [duration],
  );

  const clearRipples = useCallback(() => setRipples([]), []);

  return { ripples, addRipple, clearRipples };
}

/** Hook to manage the element highlight rect with auto-dismiss */
export function useHighlight(duration = 600) {
  const [highlight, setHighlight] = useState<HighlightRect | null>(null);

  const showHighlight = useCallback(
    (rect: HighlightRect) => {
      setHighlight(rect);
      setTimeout(() => setHighlight(null), duration);
    },
    [duration],
  );

  const clearHighlight = useCallback(() => setHighlight(null), []);

  return { highlight, showHighlight, clearHighlight };
}

/* ── Helpers ──────────────────────────────────────────────────── */

/** Darken a hex color slightly for the cursor stroke */
function darkenColor(hex: string): string {
  try {
    const h = hex.replace('#', '');
    const r = Math.max(0, parseInt(h.substring(0, 2), 16) - 20);
    const g = Math.max(0, parseInt(h.substring(2, 4), 16) - 20);
    const b = Math.max(0, parseInt(h.substring(4, 6), 16) - 20);
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  } catch {
    return hex;
  }
}
