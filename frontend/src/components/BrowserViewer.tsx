/* ═══════════════════════════════════════════════════════════════
   BrowserViewer — Real-time browser automation viewer panel
   Shows live browser viewport, mouse overlay, step log, and
   user intervention controls.
   ═══════════════════════════════════════════════════════════════ */
import { useState, useEffect, useRef, useCallback } from 'react';

/* ── Types ────────────────────────────────────────────────────── */
export interface AutomationStep {
  stepNumber: number;
  timestamp: string;    // mm:ss.SSS
  actionType: string;   // NAVIGATE, CLICK, TYPE, UPLOAD, SELECT, SUBMIT, SUCCESS, ERROR, MANUAL
  target: string;       // selector or URL
  value?: string;       // masked for passwords
  isActive?: boolean;
}

export interface BrowserSessionState {
  sessionId: string;
  jobId: string;
  companyName: string;
  roleTitle: string;
  currentUrl: string;
  pageTitle: string;
  favicon: string;
  status: 'connecting' | 'running' | 'paused' | 'captcha' | 'completed' | 'failed' | 'user_control';
  steps: AutomationStep[];
  elapsedMs: number;
  mouseX: number;
  mouseY: number;
  progress: { current: number; total: number };
  screenshotDataUrl?: string;
}

interface BrowserViewerProps {
  session: BrowserSessionState | null;
  onTakeControl?: () => void;
  onResumeAutomation?: () => void;
  onMarkSubmitted?: () => void;
  onStopAll?: () => void;
  compact?: boolean;
}

/* ── Action Colors ──────────────────────────────────────────── */
const ACTION_COLORS: Record<string, string> = {
  NAVIGATE: '#3b82f6',
  CLICK: '#f59e0b',
  TYPE: '#10b981',
  UPLOAD: '#8b5cf6',
  SELECT: '#06b6d4',
  SUBMIT: '#14b8a6',
  SUCCESS: '#059669',
  ERROR: '#ef4444',
  MANUAL: '#f97316',
  CAPTCHA: '#ec4899',
  WAIT: '#6b7280',
};

function formatElapsed(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  const remainder = ms % 1000;
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}.${String(remainder).padStart(3, '0')}`;
}

export default function BrowserViewer({
  session,
  onTakeControl,
  onResumeAutomation,
  onMarkSubmitted,
  onStopAll,
  compact = false,
}: BrowserViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const [clickRipples, setClickRipples] = useState<{ id: number; x: number; y: number }[]>([]);
  const [highlightEl, setHighlightEl] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const rippleIdRef = useRef(0);
  const wsRef = useRef<WebSocket | null>(null);
  const [wsStatus, setWsStatus] = useState<'connected' | 'connecting' | 'disconnected'>('disconnected');
  const [frameCount, setFrameCount] = useState(0);

  // Auto-scroll step log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session?.steps?.length]);

  // WebSocket connection for frame stream
  useEffect(() => {
    if (!session?.sessionId) return;

    const connectWs = () => {
      setWsStatus('connecting');
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/browser-stream/${session.sessionId}`;
      
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsStatus('connected');
        };

        ws.onmessage = (event) => {
          // Handle frame data
          if (event.data instanceof Blob) {
            const reader = new FileReader();
            reader.onload = () => {
              const img = new Image();
              img.onload = () => {
                const canvas = canvasRef.current;
                if (canvas) {
                  const ctx = canvas.getContext('2d');
                  if (ctx) {
                    canvas.width = img.width;
                    canvas.height = img.height;
                    ctx.drawImage(img, 0, 0);
                    setFrameCount(prev => prev + 1);
                  }
                }
              };
              img.src = reader.result as string;
            };
            reader.readAsDataURL(event.data);
          } else {
            // JSON control messages
            try {
              const msg = JSON.parse(event.data);
              if (msg.type === 'click') {
                addClickRipple(msg.x, msg.y);
              } else if (msg.type === 'highlight') {
                setHighlightEl({ x: msg.x, y: msg.y, w: msg.w, h: msg.h });
                setTimeout(() => setHighlightEl(null), 600);
              }
            } catch {}
          }
        };

        ws.onclose = () => {
          setWsStatus('disconnected');
          // Auto-reconnect after 2s
          setTimeout(connectWs, 2000);
        };

        ws.onerror = () => {
          setWsStatus('disconnected');
        };
      } catch {
        setWsStatus('disconnected');
      }
    };

    connectWs();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [session?.sessionId]);

  const addClickRipple = useCallback((x: number, y: number) => {
    const id = rippleIdRef.current++;
    setClickRipples(prev => [...prev, { id, x, y }]);
    setTimeout(() => {
      setClickRipples(prev => prev.filter(r => r.id !== id));
    }, 600);
  }, []);

  // If no session, show empty state
  if (!session) {
    return (
      <div className="bv-empty">
        <div className="bv-empty-icon">🖥️</div>
        <h3 className="bv-empty-title">No Active Session</h3>
        <p className="bv-empty-text">
          The browser automation viewer will appear here when an application
          is being processed. Select a job and click "Auto Apply" to begin.
        </p>
      </div>
    );
  }

  const isUserControl = session.status === 'user_control' || session.status === 'paused';
  const isCaptcha = session.status === 'captcha';
  const isComplete = session.status === 'completed';
  const isFailed = session.status === 'failed';

  return (
    <div className={`bv-container ${compact ? 'bv-compact' : ''}`}>
      {/* ── Header Bar ───────────────────────────────────── */}
      <div className="bv-header">
        <div className="bv-header-left">
          {session.favicon && (
            <img
              src={session.favicon}
              alt=""
              className="bv-favicon"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}
          <div className="bv-header-info">
            <div className="bv-page-title">{session.pageTitle || session.companyName}</div>
            <div className="bv-company-role">
              {session.companyName} — {session.roleTitle}
            </div>
          </div>
        </div>
        <div className="bv-header-right">
          {/* Elapsed Timer */}
          <div className="bv-timer">
            <span className="bv-timer-icon">⏱️</span>
            <span className="bv-timer-value">{formatElapsed(session.elapsedMs)}</span>
          </div>

          {/* Progress */}
          {session.progress.total > 0 && (
            <div className="bv-progress-badge">
              Step {session.progress.current} of {session.progress.total}
            </div>
          )}

          {/* Status Badge */}
          <div className={`bv-status-badge bv-status-${session.status}`}>
            {session.status === 'running' && <span className="bv-status-dot pulse" />}
            {session.status === 'paused' && <span className="bv-status-dot paused" />}
            {session.status === 'captcha' && '🔐'}
            {session.status === 'completed' && '✅'}
            {session.status === 'failed' && '❌'}
            {session.status === 'user_control' && '🎮'}
            {session.status === 'connecting' && '🔄'}
            <span>{session.status.replace('_', ' ').toUpperCase()}</span>
          </div>

          {/* Control Buttons */}
          {session.status === 'running' && onTakeControl && (
            <button className="bv-control-btn bv-take-control" onClick={onTakeControl}>
              🎮 Take Control
            </button>
          )}
          {(isUserControl || isCaptcha) && onResumeAutomation && (
            <button className="bv-control-btn bv-resume" onClick={onResumeAutomation}>
              ▶ Resume Automation
            </button>
          )}
          {isUserControl && onMarkSubmitted && (
            <button className="bv-control-btn bv-mark-done" onClick={onMarkSubmitted}>
              ✅ Mark as Submitted
            </button>
          )}
          {onStopAll && !isComplete && !isFailed && (
            <button className="bv-control-btn bv-stop-all" onClick={onStopAll}>
              ⏹ Stop
            </button>
          )}
        </div>
      </div>

      {/* ── URL Bar ──────────────────────────────────────── */}
      <div className="bv-url-bar">
        <span className="bv-url-lock">🔒</span>
        <input
          className="bv-url-input"
          value={session.currentUrl}
          readOnly
          onClick={(e) => (e.target as HTMLInputElement).select()}
        />
        <span className={`bv-ws-indicator ${wsStatus}`} title={`Stream: ${wsStatus}`}>
          {wsStatus === 'connected' ? '🟢' : wsStatus === 'connecting' ? '🟡' : '🔴'}
        </span>
      </div>

      {/* ── User Control Banner ──────────────────────────── */}
      {isUserControl && (
        <div className="bv-user-banner">
          🎮 You are in control — Automation is paused
        </div>
      )}
      {isCaptcha && (
        <div className="bv-captcha-banner">
          🔐 CAPTCHA detected — please complete it manually, then click "Continue Automation"
        </div>
      )}

      {/* ── Main Content (Viewport + Log) ───────────────── */}
      <div className="bv-main">
        {/* Browser Viewport */}
        <div className="bv-viewport-wrapper">
          <div className="bv-viewport">
            <canvas
              ref={canvasRef}
              className="bv-canvas"
              width={1280}
              height={800}
            />

            {/* Static screenshot fallback */}
            {session.screenshotDataUrl && frameCount === 0 && (
              <img
                src={session.screenshotDataUrl}
                alt="Browser screenshot"
                className="bv-screenshot-fallback"
              />
            )}

            {/* Animated Cursor Overlay */}
            {session.status === 'running' && (
              <div
                className="bv-cursor"
                style={{
                  transform: `translate(${session.mouseX}px, ${session.mouseY}px)`,
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M5 3l14 9-6 1-4 6z" fill="#14b8a6" stroke="#0d9488" strokeWidth="1.5"/>
                </svg>
              </div>
            )}

            {/* Click Ripples */}
            {clickRipples.map(r => (
              <div
                key={r.id}
                className="bv-click-ripple"
                style={{ left: r.x, top: r.y }}
              />
            ))}

            {/* Element Highlight Ring */}
            {highlightEl && (
              <div
                className="bv-highlight-ring"
                style={{
                  left: highlightEl.x,
                  top: highlightEl.y,
                  width: highlightEl.w,
                  height: highlightEl.h,
                }}
              />
            )}

            {/* Completion / Failed overlay */}
            {isComplete && (
              <div className="bv-viewport-overlay bv-overlay-success">
                <span className="bv-overlay-icon">🎉</span>
                <span className="bv-overlay-text">Application Submitted Successfully</span>
              </div>
            )}
            {isFailed && (
              <div className="bv-viewport-overlay bv-overlay-error">
                <span className="bv-overlay-icon">❌</span>
                <span className="bv-overlay-text">Application Failed</span>
              </div>
            )}

            {/* Reconnecting overlay */}
            {wsStatus === 'disconnected' && session.status === 'running' && (
              <div className="bv-viewport-overlay bv-overlay-reconnect">
                <div className="bv-reconnect-spinner" />
                <span className="bv-overlay-text">Reconnecting to stream…</span>
              </div>
            )}
          </div>
        </div>

        {/* ── Step Log ───────────────────────────────────── */}
        <div className="bv-steplog">
          <div className="bv-steplog-header">
            <span className="bv-steplog-title">📋 Action Log</span>
            <span className="bv-steplog-count">{session.steps.length} steps</span>
          </div>
          <div className="bv-steplog-list">
            {session.steps.length === 0 ? (
              <div className="bv-steplog-empty">Waiting for automation to start…</div>
            ) : (
              session.steps.map((step, i) => (
                <div
                  key={i}
                  className={`bv-step-entry ${step.isActive ? 'bv-step-active' : ''} ${step.actionType === 'ERROR' ? 'bv-step-error' : ''}`}
                >
                  <span className="bv-step-num">
                    [{String(step.stepNumber).padStart(2, '0')}]
                  </span>
                  <span className="bv-step-time">{step.timestamp}</span>
                  <span
                    className="bv-step-action"
                    style={{ color: ACTION_COLORS[step.actionType] || '#9ca3af' }}
                  >
                    {step.actionType}
                  </span>
                  <span className="bv-step-arrow">→</span>
                  <span className="bv-step-target">
                    {step.target}
                    {step.value && (
                      <span className="bv-step-value"> = "{step.value}"</span>
                    )}
                  </span>
                  {step.isActive && <span className="bv-step-pulse" />}
                </div>
              ))
            )}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>

      {/* ── Progress Bar ─────────────────────────────────── */}
      {session.progress.total > 0 && (
        <div className="bv-progress-bar-wrapper">
          <div
            className="bv-progress-bar-fill"
            style={{
              width: `${(session.progress.current / session.progress.total) * 100}%`,
            }}
          />
        </div>
      )}
    </div>
  );
}
