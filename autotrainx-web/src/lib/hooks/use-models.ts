'use client'

import { useQuery } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'

const api = getApiClient()

export const modelsKeys = {
  all: ['models'] as const,
  lists: () => [...modelsKeys.all, 'list'] as const,
  details: () => [...modelsKeys.all, 'detail'] as const,
  detail: (path: string) => [...modelsKeys.details(), path] as const,
}

export function useModels() {
  return useQuery({
    queryKey: modelsKeys.lists(),
    queryFn: () => api.models.list(),
  })
}

export function useModel(path: string) {
  return useQuery({
    queryKey: modelsKeys.detail(path),
    queryFn: () => api.models.get(path),
    enabled: !!path,
  })
}