'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'

const api = getApiClient()

export const datasetsKeys = {
  all: ['datasets'] as const,
  lists: () => [...datasetsKeys.all, 'list'] as const,
  list: (filters?: any) => [...datasetsKeys.lists(), filters] as const,
  details: () => [...datasetsKeys.all, 'detail'] as const,
  detail: (name: string) => [...datasetsKeys.details(), name] as const,
}

export function useDatasets(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: datasetsKeys.list(params),
    queryFn: () => api.datasets.list(params),
  })
}

export function useDataset(name: string) {
  return useQuery({
    queryKey: datasetsKeys.detail(name),
    queryFn: () => api.datasets.get(name),
    enabled: !!name,
  })
}

export function usePrepareDataset() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ sourcePath, datasetName }: { 
      sourcePath: string
      datasetName?: string 
    }) => api.datasets.prepare(sourcePath, datasetName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetsKeys.lists() })
    },
  })
}

export function useDeleteDataset() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (name: string) => api.datasets.delete(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetsKeys.lists() })
    },
  })
}