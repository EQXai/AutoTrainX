'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'

const api = getApiClient()

// Query keys
export const datasetPathsKeys = {
  all: ['datasetPaths'] as const,
  paths: () => [...datasetPathsKeys.all, 'paths'] as const,
  scan: () => [...datasetPathsKeys.all, 'scan'] as const,
}

// Types
export interface DatasetPath {
  id: number
  path: string
  added_at: string
  dataset_count: number
}

export interface ScannedDataset {
  name: string
  path: string
  image_count: number
  caption_count: number
  has_valid_structure: boolean
  parent_path: string
}

// Hooks
export function useDatasetPaths() {
  return useQuery({
    queryKey: datasetPathsKeys.paths(),
    queryFn: () => api.datasetPaths.list(),
  })
}

export function useAddDatasetPath() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (path: string) => api.datasetPaths.add(path),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetPathsKeys.paths() })
      queryClient.invalidateQueries({ queryKey: datasetPathsKeys.scan() })
    },
  })
}

export function useRemoveDatasetPath() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: number) => api.datasetPaths.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetPathsKeys.paths() })
      queryClient.invalidateQueries({ queryKey: datasetPathsKeys.scan() })
    },
  })
}

export function useScannedDatasets() {
  return useQuery({
    queryKey: datasetPathsKeys.scan(),
    queryFn: () => api.datasetPaths.scan(),
  })
}

export function useScanDatasetPath() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: number) => api.datasetPaths.scanPath(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetPathsKeys.scan() })
    },
  })
}