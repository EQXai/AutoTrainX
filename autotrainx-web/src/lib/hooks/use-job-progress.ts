'use client'

import { useEffect, useState } from 'react'
import { getApiClient } from '@/lib/api/client'
import type { ProgressUpdate } from '@/types/api'

export function useJobProgress(jobId: string | null) {
  const [progress, setProgress] = useState<ProgressUpdate | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    if (!jobId) return

    const api = getApiClient()
    
    // Subscribe to progress updates
    const unsubscribe = api.subscribeToProgress(jobId, (update) => {
      setProgress(update)
    })

    // Set up connection status
    const socket = api.connectToProgress(jobId)
    
    socket.on('connect', () => setIsConnected(true))
    socket.on('disconnect', () => setIsConnected(false))

    // Cleanup
    return () => {
      unsubscribe()
      setIsConnected(false)
    }
  }, [jobId])

  return { progress, isConnected }
}