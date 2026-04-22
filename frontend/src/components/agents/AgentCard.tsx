import { useState, type ReactNode } from 'react';
import type { AgentStatus } from '../../types/agentTypes';

interface AgentCardProps {
  title: string;
  description: string;
  icon: string;
  accentColor: string;
  children: ReactNode;
  defaultExpanded?: boolean;
}

export default function AgentCard({
  title,
  description,
  icon,
  accentColor,
  children,
  defaultExpanded = false,
}: AgentCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div
      className="ag-card ag-glass"
      style={{ '--card-accent': accentColor } as React.CSSProperties}
    >
      {/* Header */}
      <div
        className="ag-card-header"
        style={{ cursor: 'pointer' }}
        onClick={() => setExpanded(!expanded)}
      >
        <div
          className="ag-card-icon"
          style={{ background: `${accentColor}20`, color: accentColor }}
        >
          {icon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="ag-card-title">{title}</span>
            <span style={{
              fontSize: '0.75rem',
              color: 'var(--ag-text-muted)',
              transition: 'transform 0.2s ease',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}>
              ▾
            </span>
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="ag-card-desc">{description}</p>

      {/* Expandable Content */}
      {expanded && (
        <div style={{ animation: 'ag-fade-in 0.3s ease' }}>
          {children}
        </div>
      )}
    </div>
  );
}
