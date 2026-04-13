import { useState, useCallback } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import JobGrid from './components/JobGrid';
import ResumeUpload from './components/ResumeUpload';
import AgentToolbar from './components/AgentToolbar';
import AgentFullPage from './components/AgentFullPage';
import type { AgentTab } from './components/AgentToolbar';
import { useJobs } from './hooks/useJobs';
import { useTheme } from './hooks/useTheme';
import { Filters } from './types';
import './index.css';

type AppView = 'dashboard' | 'resume' | AgentTab;

export default function App() {
  const { dark, toggle } = useTheme();
  const { jobs, total, loading, error, hasMore, filters, updateFilters, loadMore } = useJobs();
  const [searchDebounce, setSearchDebounce] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [activeView, setActiveView] = useState<AppView>('dashboard');

  const handleSearch = useCallback(
    (val: string) => {
      if (searchDebounce) clearTimeout(searchDebounce);
      const timeout = setTimeout(() => {
        updateFilters({ ...filters, search: val || undefined });
      }, 400);
      setSearchDebounce(timeout);
    },
    [filters, updateFilters, searchDebounce]
  );

  const handleFilterChange = useCallback(
    (newFilters: Filters) => {
      updateFilters(newFilters);
    },
    [updateFilters]
  );

  const handleResumeUpload = () => {
    setActiveView('resume');
  };

  const handleAgentTab = (tab: AgentTab) => {
    setActiveView(prev => prev === tab ? 'dashboard' : tab);
  };

  const goToDashboard = () => {
    setActiveView('dashboard');
  };

  const isAgentView = ['scan', 'score', 'tailor', 'batch', 'tracker'].includes(activeView);

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      <Navbar
        dark={dark}
        onToggleTheme={toggle}
        search={filters.search || ''}
        onSearch={handleSearch}
        onResumeUpload={handleResumeUpload}
      />
      {/* Agent Toolbar — always visible */}
      <AgentToolbar
        onTabChange={handleAgentTab}
        activeTab={isAgentView ? (activeView as AgentTab) : null}
      />

      {/* Dashboard View */}
      {activeView === 'dashboard' && (
        <div className="flex">
          <Sidebar
            filters={filters}
            onFilterChange={handleFilterChange}
            total={total}
          />
          <main className="flex-1 min-w-0">
            <JobGrid
              jobs={jobs}
              loading={loading}
              error={error}
              hasMore={hasMore}
              onLoadMore={loadMore}
            />
          </main>
        </div>
      )}

      {/* Agent Full-Page Views */}
      {isAgentView && (
        <AgentFullPage
          view={activeView as AgentTab}
          onBack={goToDashboard}
        />
      )}

      {/* Resume Full-Page View */}
      {activeView === 'resume' && (
        <ResumeUpload
          open={true}
          onClose={goToDashboard}
          mode="page"
        />
      )}
    </div>
  );
}
