'use client'

import { useQuery } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'

const api = getApiClient()

export const presetsKeys = {
  all: ['presets'] as const,
  lists: () => [...presetsKeys.all, 'list'] as const,
  details: () => [...presetsKeys.all, 'detail'] as const,
  detail: (name: string) => [...presetsKeys.details(), name] as const,
  parameters: (name: string) => [...presetsKeys.detail(name), 'parameters'] as const,
}

export function usePresets() {
  return useQuery({
    queryKey: presetsKeys.lists(),
    queryFn: () => api.presets.list(),
  })
}

export function usePreset(name: string) {
  return useQuery({
    queryKey: presetsKeys.detail(name),
    queryFn: () => api.presets.get(name),
    enabled: !!name,
  })
}

export function usePresetParameters(name: string) {
  return useQuery({
    queryKey: presetsKeys.parameters(name),
    queryFn: () => api.presets.getParameters(name),
    enabled: !!name,
  })
}