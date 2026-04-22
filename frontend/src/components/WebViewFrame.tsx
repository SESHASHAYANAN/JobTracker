/**
 * WebViewFrame — Live in-app WebView that renders company job pages.
 *
 * Strategy:
 * 1. First attempts direct iframe load of the job URL
 * 2. If blocked (X-Frame-Options / CSP), falls back to backend CORS proxy
 * 3. If proxy also fails, shows a styled fallback with "Open in New Tab"
 *
 * No mocks. No placeholders. Real-time page rendering only.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { getProxyPageUrl, verifyUrlLive } from '../api';

interface WebViewFrameProps {
  url: string;
  onPageTitleChange?: (title: string) => void;
  onLoadStateChange?: (state: 'loading' | 'loaded' | 'proxy' | 'failed') => void;
}

export default function WebViewFrame({ url, onPageTitleChange, onLoadStateChange }: WebViewFrameProps) {
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'proxy' | 'failed'>('loading');
  const [useProxy, setUseProxy] = useState(false);
  const [pageTitle, setPageTitle] = useState('');
  const [canIframe, setCanIframe] = useState<boolean | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const loadTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const updateState = useCallback((state: 'loading' | 'loaded' | 'proxy' | 'failed') => {
    setLoadState(state);
    onLoadStateChange?.(state);
  }, [onLoadStateChange]);

  // Pre-check if URL can be iframed
  useEffect(() => {
    if (!url) return;
    let cancelled = false;

    (async () => {
      try {
        const result = await verifyUrlLive(url);
        if (cancelled) return;

        if (result.page_title) {
          setPageTitle(result.page_title);
          onPageTitleChange?.(result.page_title);
        }

        if (result.reachable && result.can_iframe) {
          setCanIframe(true);
          setUseProxy(false);
        } else if (result.reachable) {
          // Page is reachable but blocks iframes — use proxy
          setCanIframe(false);
          setUseProxy(true);
          updateState('proxy');
        } else {
          // Not reachable at all
          setCanIframe(false);
          updateState('failed');
        }
      } catch {
        if (!cancelled) {
          // Verification failed, try direct load anyway
          setCanIframe(true);
          setUseProxy(false);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [url, onPageTitleChange, updateState]);

  // Fallback timer — if iframe doesn't fire onLoad in 8 seconds, switch to proxy
  useEffect(() => {
    if (loadState === 'loading' && !useProxy) {
      loadTimerRef.current = setTimeout(() => {
        setUseProxy(true);
        updateState('proxy');
      }, 8000);
    }
    return () => {
      if (loadTimerRef.current) clearTimeout(loadTimerRef.current);
    };
  }, [loadState, useProxy, updateState]);

  const handleIframeLoad = () => {
    if (loadTimerRef.current) clearTimeout(loadTimerRef.current);
    if (loadState === 'loading') {
      updateState(useProxy ? 'proxy' : 'loaded');
    }
  };

  const handleIframeError = () => {
    if (loadTimerRef.current) clearTimeout(loadTimerRef.current);
    if (!useProxy) {
      setUseProxy(true);
      updateState('proxy');
    } else {
      updateState('failed');
    }
  };

  const iframeSrc = useProxy ? getProxyPageUrl(url) : url;

  if (!url) {
    return (
      <div className="webview-empty">
        <div className="webview-empty-icon">🌐</div>
        <p className="webview-empty-title">No URL to display</p>
        <p className="webview-empty-sub">Click "Start AI Apply" to begin</p>
      </div>
    );
  }

  if (canIframe === false && !useProxy && loadState === 'failed') {
    return (
      <div className="webview-fallback">
        <div className="webview-fallback-icon">🔒</div>
        <h3 className="webview-fallback-title">Page cannot be embedded</h3>
        <p className="webview-fallback-text">
          This site blocks inline previews. Open the exact job listing directly:
        </p>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="webview-fallback-link"
        >
          🔗 Open {new URL(url).hostname} in new tab →
        </a>
      </div>
    );
  }

  return (
    <div className="webview-container">
      {/* Loading overlay */}
      {loadState === 'loading' && (
        <div className="webview-loading">
          <div className="webview-loading-spinner" />
          <p>Loading live page…</p>
        </div>
      )}

      {/* Proxy indicator */}
      {useProxy && loadState !== 'loading' && (
        <div className="webview-proxy-badge">
          🔄 Rendered via secure proxy
        </div>
      )}

      <iframe
        ref={iframeRef}
        src={iframeSrc}
        className="webview-iframe"
        onLoad={handleIframeLoad}
        onError={handleIframeError}
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
        title="Job Application Page"
        style={{
          opacity: loadState === 'loading' ? 0.3 : 1,
          transition: 'opacity 0.4s ease',
        }}
      />

      {/* Direct link fallback always available */}
      <div className="webview-direct-link">
        <a href={url} target="_blank" rel="noopener noreferrer">
          Open original page ↗
        </a>
      </div>
    </div>
  );
}
