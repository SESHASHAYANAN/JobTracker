import ScanPanel from './agents/ScanPanel';
import ScorePanel from './agents/ScorePanel';
import TailorPanel from './agents/TailorPanel';
import BatchPanel from './agents/BatchPanel';
import TrackerPanel from './agents/TrackerPanel';
import '../agents.css';

type AgentView = 'scan' | 'score' | 'tailor' | 'batch' | 'tracker';

const VIEW_META: Record<AgentView, { icon: string; label: string }> = {
  scan: { icon: '🔍', label: 'Scan Agent' },
  score: { icon: '📊', label: 'Score Agent' },
  tailor: { icon: '✂️', label: 'Tailor CV Agent' },
  batch: { icon: '⚡', label: 'Batch Agent' },
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
        {view === 'scan' && <ScanPanel />}
        {view === 'score' && <ScorePanel />}
        {view === 'tailor' && <TailorPanel />}
        {view === 'batch' && <BatchPanel />}
        {view === 'tracker' && <TrackerPanel />}
      </div>
    </div>
  );
}
