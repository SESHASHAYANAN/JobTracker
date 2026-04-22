import { useState, useCallback, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import JobGrid from './components/JobGrid';
import ResumeUpload from './components/ResumeUpload';
import AgentToolbar from './components/AgentToolbar';
import AgentFullPage from './components/AgentFullPage';
import type { AgentTab } from './components/AgentToolbar';
import { useJobs } from './hooks/useJobs';
import { useTheme } from './hooks/useTheme';
import { refreshJobs, getRefreshStatus } from './api';

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

  const isAgentView = ['tailor', 'tracker'].includes(activeView);

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      <Navbar
        dark={dark}
        onToggleTheme={toggle}
        search={filters.search || ''}
        onSearch={handleSearch}
        onResumeUpload={handleResumeUpload}
      />

      {/* Hero Banner */}
      <div className="hero-banner">
        <img src="/hero-banner.jpg" alt="AI Job Platform" className="hero-banner-img" />
        <div className="hero-banner-overlay">
          <h1 className="hero-banner-title">AI-Powered Job Intelligence</h1>
          <p className="hero-banner-subtitle">
            Real-time job listings with direct application URLs • AI-powered matching • Automated applying
          </p>
          {needsRefresh && (
            <button
              onClick={handleRefreshJobs}
              disabled={refreshing}
              className="hero-refresh-btn"
            >
              {refreshing ? '🔄 Fetching Real Jobs...' : '⚡ Load Real Jobs'}
            </button>
          )}
          {refreshMsg && (
            <p className="hero-refresh-msg">{refreshMsg}</p>
          )}
        </div>
      </div>

      {/* Agent Toolbar — always visible, with smart filter pills */}
      <AgentToolbar
        onTabChange={handleAgentTab}
        activeTab={isAgentView ? (activeView as AgentTab) : null}
        filters={filters}
        onFilterChange={handleFilterChange}
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
