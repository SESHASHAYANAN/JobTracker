import TailorPanel from './agents/TailorPanel';
import TrackerPanel from './agents/TrackerPanel';
import '../agents.css';

type AgentView = 'tailor' | 'tracker';

const VIEW_META: Record<AgentView, { icon: string; label: string }> = {
  tailor: { icon: '✂️', label: 'Tailor CV Agent' },
  tracker: { icon: '📋', label: 'Tracker Agent' },
};

interface AgentFullPageProps {
  view: AgentView;
  onBack: () => void;
}

export default function AgentFullPage({ view, onBack }: AgentFullPageProps) {
  const meta = VIEW_META[view];

  return (
    <div className="agent-fullpage">
      <div className="agent-fullpage-header">
        <button className="agent-fullpage-back" onClick={onBack}>
          ← Back to Dashboard
        </button>
        <h2 className="agent-fullpage-title">
          {meta.icon} {meta.label}
        </h2>
      </div>
      <div className="agent-fullpage-content">
        {view === 'tailor' && <TailorPanel />}
        {view === 'tracker' && <TrackerPanel />}
      </div>
    </div>
  );
}
