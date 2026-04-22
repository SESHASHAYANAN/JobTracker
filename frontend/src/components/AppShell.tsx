import App from '../App';

/**
 * AppShell — Thin wrapper around App.
 * Agent Suite features are now embedded directly in the main dashboard
 * via AgentToolbar, so no view toggling is needed.
 */
export default function AppShell() {
  return <App />;
}
