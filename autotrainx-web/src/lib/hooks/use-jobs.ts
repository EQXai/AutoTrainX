'use client'

import { useQuery } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'
import type { JobInfo, JobsListResponse, RunningJobsResponse, StatisticsResponse } from '@/types/api'
import { toast } from 'sonner'

const api = getApiClient()

// Query keys
export const jobsKeys = {
  all: ['jobs'] as const,
  lists: () => [...jobsKeys.all, 'list'] as const,
  list: (filters?: { status?: string; mode?: string; page?: number; page_size?: number }) => 
    [...jobsKeys.lists(), filters] as const,
  details: () => [...jobsKeys.all, 'detail'] as const,
  detail: (id: string) => [...jobsKeys.details(), id] as const,
  running: () => [...jobsKeys.all, 'running'] as const,
  statistics: () => [...jobsKeys.all, 'statistics'] as const,
}

// Get job list with filters
export function useJobs(filters?: { 
  status?: string
  mode?: string
  page?: number
  page_size?: number 
}, options?: {
  refetchInterval?: number | false
}) {
  return useQuery<JobsListResponse>({
    queryKey: jobsKeys.list(filters),
    queryFn: async () => {
      const response = await api.jobs.list(filters)
      // Transform the API response to match frontend expectations
      return {
        items: response.jobs.map(job => ({
          id: job.job_id,
          name: job.dataset_name || job.job_id,
          status: job.status,
          mode: job.pipeline_mode,
          progress_percentage: job.progress_percentage,
          created_at: job.created_at,
          updated_at: job.end_time || job.created_at,
          config: {
            dataset_name: job.dataset_name || 'Unknown',
            preset: job.preset,
            mode: job.pipeline_mode
          },
          current_step: job.error_message ? 'Error' : (job.status === 'done' ? 'Completed' : 'Processing'),
          completed_steps: job.status === 'done' ? 1 : 0,
          total_steps: 1
        })),
        total_count: response.total,
        page: response.page,
        page_size: response.page_size,
        total_pages: Math.ceil(response.total / response.page_size)
      }
    },
    refetchInterval: options?.refetchInterval ?? 5000, // Default 5 seconds
    refetchIntervalInBackground: true,
  })
}

// Get single job by ID
export function useJob(id: string) {
  return useQuery<JobInfo>({
    queryKey: jobsKeys.detail(id),
    queryFn: () => api.jobs.get(id),
    enabled: !!id,
    refetchInterval: 2000, // Refresh every 2 seconds
  })
}

// Get running jobs
export function useRunningJobs(options?: {
  refetchInterval?: number | false
}) {
  return useQuery<RunningJobsResponse>({
    queryKey: jobsKeys.running(),
    queryFn: () => api.jobs.getRunning(),
    refetchInterval: options?.refetchInterval ?? 3000, // Default 3 seconds
    refetchIntervalInBackground: true,
  })
}

// Get job statistics
export function useJobStatistics(options?: {
  refetchInterval?: number | false
}) {
  return useQuery<StatisticsResponse>({
    queryKey: jobsKeys.statistics(),
    queryFn: () => api.jobs.getStatistics(),
    refetchInterval: options?.refetchInterval ?? 30000, // Default 30 seconds
  })
}

// Note: Job cancellation is no longer supported in CLI bridge mode
// Jobs must be cancelled through the CLI directly
export function useCancelJob() {
  return {
    mutate: (id: string) => {
      toast.error('Job cancellation must be done through CLI')
      console.warn(`Job cancellation requested for ${id} - not supported in CLI bridge mode`)
    },
    isLoading: false,
    error: null,
  }
}

// Note: Job logs are no longer available in the new architecture
export function useJobLogs(id: string) {
  return {
    data: null,
    error: new Error('Job logs not available in CLI bridge mode'),
    isLoading: false,
  }
}

// Utility function to check if a job is in a terminal state
export function isJobComplete(status: string): boolean {
  return ['done', 'failed', 'cancelled'].includes(status.toLowerCase())
}

// Utility function to check if a job is running
export function isJobRunning(status: string): boolean {
  return ['training', 'preparing_dataset', 'configuring_preset', 'generating_preview'].includes(status.toLowerCase())
}