import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchJobs } from '../api';
import { Job, Filters, JobsResponse } from '../types';

export function useJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const retryCount = useRef(0);

  const loadJobs = useCallback(async (currentFilters: Filters, currentPage: number, append = false) => {
    setLoading(true);
    setError(null);
    try {
      const data: JobsResponse = await fetchJobs(currentFilters, currentPage, 30);
      if (append) {
        setJobs(prev => [...prev, ...data.jobs]);
      } else {
        setJobs(data.jobs);
      }
      setTotal(data.total);
      setHasMore(data.has_more);

      // If initial load returns 0 jobs and no filters are active, retry
      // The backend may still be loading data from agents
      if (data.total === 0 && !append && currentPage === 1 && retryCount.current < 5) {
        const noFilters = !currentFilters.role && !currentFilters.visa && !currentFilters.country &&
          !currentFilters.stage && !currentFilters.vc && !currentFilters.batch &&
          !currentFilters.level && !currentFilters.search && !currentFilters.founder_name &&
          !currentFilters.team_size_bucket;
        if (noFilters) {
          retryCount.current++;
          setTimeout(() => {
            loadJobs(currentFilters, 1, false);
          }, 2000);
          return;
        }
      }
      // Reset retry on successful load with data
      if (data.total > 0) {
        retryCount.current = 0;
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load jobs');
      // Also retry on network errors (backend may not be up yet)
      if (retryCount.current < 5) {
        retryCount.current++;
        setTimeout(() => {
          loadJobs(currentFilters, currentPage, append);
        }, 3000);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadJobs(filters, 1, false);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // When filters change → fresh fetch, page 1, REPLACE results
  const updateFilters = useCallback((newFilters: Filters) => {
    setFilters(newFilters);
    setPage(1);
    retryCount.current = 0;
    loadJobs(newFilters, 1, false);
  }, [loadJobs]);

  // Load more → append, same filters, next page
  const loadMore = useCallback(() => {
    const nextPage = page + 1;
    setPage(nextPage);
    loadJobs(filters, nextPage, true);
  }, [page, filters, loadJobs]);

  // Force refresh — reload all jobs from page 1
  const refresh = useCallback(() => {
    setPage(1);
    retryCount.current = 0;
    loadJobs(filters, 1, false);
  }, [filters, loadJobs]);

  return { jobs, total, loading, error, hasMore, filters, updateFilters, loadMore, refresh };
}
