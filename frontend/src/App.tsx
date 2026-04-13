import { useState, useCallback } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import JobGrid from './components/JobGrid';
import ResumeUpload from './components/ResumeUpload';
import AgentToolbar from './components/AgentToolbar';
import { useJobs } from './hooks/useJobs';
import { useTheme } from './hooks/useTheme';
import { Filters } from './types';
import './index.css';

export default function App() {
  const { dark, toggle } = useTheme();
  const { jobs, total, loading, error, hasMore, filters, updateFilters, loadMore } = useJobs();
  const [searchDebounce, setSearchDebounce] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [resumeOpen, setResumeOpen] = useState(false);

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

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
      <Navbar
        dark={dark}
        onToggleTheme={toggle}
        search={filters.search || ''}
        onSearch={handleSearch}
        onResumeUpload={() => setResumeOpen(true)}
      />
      {/* Agent Toolbar — embedded directly in the main dashboard */}
      <AgentToolbar />
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
      <ResumeUpload open={resumeOpen} onClose={() => setResumeOpen(false)} />
    </div>
  );
}
