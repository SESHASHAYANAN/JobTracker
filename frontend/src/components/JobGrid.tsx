import { motion } from 'framer-motion';
import { Job } from '../types';
import JobCard from './JobCard';
import SkeletonCard from './SkeletonCard';

interface JobGridProps {
  jobs: Job[];
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  onLoadMore: () => void;
}

export default function JobGrid({ jobs, loading, error, hasMore, onLoadMore }: JobGridProps) {
  // Loading state — show skeletons
  if (loading && jobs.length === 0) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 p-4">
        {Array.from({ length: 9 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
            Failed to load jobs
          </p>
          <p className="text-sm" style={{ color: 'var(--color-muted)' }}>
            {error}. The backend might still be loading data from agents.
          </p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!loading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-5xl mb-4">🔍</p>
          <p className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
            No jobs found
          </p>
          <p className="text-sm" style={{ color: 'var(--color-muted)' }}>
            Try adjusting your filters or wait for agents to finish scraping.
          </p>
        </div>
      </div>
    );
  }

  // Split into recommended and regular
  const recommendedJobs = jobs.filter(j => (j.match_score ?? 0) >= 80);
  const regularJobs = jobs.filter(j => (j.match_score ?? 0) < 80);

  return (
    <div className="p-4">
      {/* Recommended Section */}
      {recommendedJobs.length > 0 && (
        <div className="recommended-section mb-8">
          <div className="recommended-section-header">
            <h2 className="recommended-section-title">⭐ Recommended for You</h2>
            <span className="recommended-section-count">{recommendedJobs.length} matches</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {recommendedJobs.map((job, i) => (
              <JobCard key={job.id || i} job={job} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Regular Job Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {regularJobs.map((job, i) => (
          <JobCard key={job.id || i} job={job} index={i + recommendedJobs.length} />
        ))}
      </div>

      {/* Load More */}
      {hasMore && (
        <div className="flex justify-center mt-8 mb-4">
          <motion.button
            id="load-more"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={onLoadMore}
            disabled={loading}
            className="px-6 py-3 rounded-xl text-sm font-semibold cursor-pointer"
            style={{
              backgroundColor: 'var(--color-accent)',
              color: '#fff',
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Loading...
              </span>
            ) : (
              'Load more jobs'
            )}
          </motion.button>
        </div>
      )}

      {/* Loading more indicator */}
      {loading && jobs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mt-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={`loading-${i}`} />
          ))}
        </div>
      )}
    </div>
  );
}
