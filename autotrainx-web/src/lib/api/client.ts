import axios, { AxiosInstance } from 'axios'
import { io, Socket } from 'socket.io-client'
import type {
  TrainingResponse,
  JobInfo,
  JobsListResponse,
  RunningJobsResponse,
  StatisticsResponse,
  SingleTrainingRequest,
  BatchTrainingRequest,
  VariationsTrainingRequest,
  Dataset,
  Preset,
  ProgressUpdate,
  ApiResponse,
  PaginatedResponse,
} from '@/types/api'

export class AutoTrainXClient {
  private http: AxiosInstance
  private ws: Socket | null = null
  private baseURL: string

  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || '/api/backend') {
    this.baseURL = baseURL
    this.http = axios.create({
      baseURL: typeof window !== 'undefined' ? '/api/backend' : 'http://localhost:8000/api/v1',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor for auth (future implementation)
    this.http.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.http.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized
          if (typeof window !== 'undefined') {
            localStorage.removeItem('auth_token')
            window.location.href = '/login'
          }
        }
        return Promise.reject(error)
      }
    )
  }

  // Jobs API - Read-only access to statistics
  jobs = {
    // Get job by ID
    get: async (id: string): Promise<JobInfo> => {
      const response = await this.http.get<JobInfo>(`/jobs/${id}`)
      return response.data
    },

    // List jobs with pagination
    list: async (params?: {
      page?: number
      page_size?: number
      status?: string
      mode?: string
    }): Promise<JobsListResponse> => {
      const response = await this.http.get<JobsListResponse>('/jobs', { params })
      return response.data
    },

    // Get running jobs
    getRunning: async (): Promise<RunningJobsResponse> => {
      const response = await this.http.get<RunningJobsResponse>('/jobs/running')
      return response.data
    },

    // Get statistics
    getStatistics: async (): Promise<StatisticsResponse> => {
      const response = await this.http.get<StatisticsResponse>('/jobs/statistics')
      return response.data
    },

    // Check health
    checkHealth: async () => {
      const response = await this.http.get<{
        status: string
        message: string
        total_jobs?: number
      }>('/jobs/health')
      return response.data
    },
  }

  // Training API - Execute CLI commands
  training = {
    // Single mode training
    single: async (data: SingleTrainingRequest): Promise<TrainingResponse> => {
      const response = await this.http.post<TrainingResponse>('/training/single', data)
      return response.data
    },

    // Batch mode training
    batch: async (data: BatchTrainingRequest): Promise<TrainingResponse> => {
      const response = await this.http.post<TrainingResponse>('/training/batch', data)
      return response.data
    },

    // Variations mode training
    variations: async (data: VariationsTrainingRequest): Promise<TrainingResponse> => {
      const response = await this.http.post<TrainingResponse>('/training/variations', data)
      return response.data
    },

    // Check health
    checkHealth: async () => {
      const response = await this.http.get<{
        status: string
        message: string
        cli_path?: string
      }>('/training/health')
      return response.data
    },
  }

  // Legacy APIs - Keep for compatibility but may not work with new backend
  
  // Datasets API (kept for UI compatibility)
  datasets = {
    list: async (params?: { page?: number; page_size?: number }) => {
      console.warn('Datasets API is legacy - may not work with CLI bridge')
      try {
        const response = await this.http.get<PaginatedResponse<Dataset>>('/datasets', { params })
        return response.data
      } catch (error) {
        // Return empty response if not available
        return {
          items: [],
          total_count: 0,
          page: 1,
          page_size: 20,
          total_pages: 0
        }
      }
    },

    get: async (name: string) => {
      console.warn('Datasets API is legacy - may not work with CLI bridge')
      const response = await this.http.get<ApiResponse<Dataset>>(`/datasets/${name}`)
      return response.data
    },

    prepare: async (sourcePath: string, datasetName?: string, repeats: number = 30, className: string = 'person') => {
      console.warn('Dataset preparation should be done through training API')
      // Redirect to training API
      const trainingResponse = await this.training.single({
        source_path: sourcePath,
        dataset_name: datasetName,
        repeats,
        class_name: className,
        generate_configs: false,
        auto_clean: false
      })
      
      return {
        success: trainingResponse.success,
        message: trainingResponse.command,
        timestamp: new Date().toISOString(),
        data: {
          name: datasetName || 'unknown',
          path: sourcePath,
          total_images: 0,
          total_texts: 0,
          has_sample_prompts: false
        }
      }
    },

    delete: async (name: string) => {
      console.warn('Dataset deletion not supported in CLI bridge mode')
      throw new Error('Dataset deletion must be done through CLI')
    },

    getSamplePrompts: async (name: string) => {
      console.warn('Sample prompts not available in CLI bridge mode')
      return { success: false, message: 'Not available', timestamp: new Date().toISOString(), data: [] }
    },
  }

  // Presets API (kept for UI compatibility)
  presets = {
    list: async (params?: { category?: string; architecture?: string }) => {
      console.warn('Presets API is legacy - may not work with CLI bridge')
      try {
        const response = await this.http.get<any>('/presets', { params })
        return response.data
      } catch (error) {
        return { presets: [] }
      }
    },

    get: async (name: string) => {
      console.warn('Presets API is legacy - may not work with CLI bridge')
      const response = await this.http.get<any>(`/presets/${name}`)
      return response.data
    },

    getParameters: async (name: string) => {
      console.warn('Preset parameters not available in CLI bridge mode')
      return {}
    },

    getCategories: async () => {
      console.warn('Preset categories not available in CLI bridge mode')
      return { categories: [] }
    },

    generateConfig: async (data: any) => {
      console.warn('Config generation should be done through training API')
      throw new Error('Use training API instead')
    },

    create: async (data: any) => {
      console.warn('Preset creation not supported in CLI bridge mode')
      throw new Error('Preset creation must be done through CLI')
    },

    update: async (name: string, data: any) => {
      console.warn('Preset update not supported in CLI bridge mode')
      throw new Error('Preset updates must be done through CLI')
    },

    delete: async (name: string) => {
      console.warn('Preset deletion not supported in CLI bridge mode')
      throw new Error('Preset deletion must be done through CLI')
    },

    checkHealth: async () => {
      return { status: 'unavailable', message: 'Presets API not available in CLI bridge mode' }
    },
  }

  // WebSocket methods (may need adjustment for new backend)
  connectToProgress(jobId?: string): Socket {
    console.warn('WebSocket progress may not be available in CLI bridge mode')
    
    if (this.ws?.connected) {
      return this.ws
    }

    this.ws = io(typeof window !== 'undefined' ? '' : 'http://localhost:8000', {
      path: '/ws',
      transports: ['websocket'],
    })

    if (jobId) {
      this.ws.emit('subscribe', { job_id: jobId })
    }

    return this.ws
  }

  subscribeToProgress(jobId: string, onUpdate: (update: ProgressUpdate) => void): () => void {
    const socket = this.connectToProgress(jobId)
    
    const handler = (data: ProgressUpdate) => {
      if (data.job_id === jobId) {
        onUpdate(data)
      }
    }

    socket.on('progress', handler)
    socket.on(`progress:${jobId}`, onUpdate)

    // Return cleanup function
    return () => {
      socket.off('progress', handler)
      socket.off(`progress:${jobId}`, onUpdate)
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.disconnect()
      this.ws = null
    }
  }

  // Settings API (kept for compatibility)
  settings = {
    get: async () => {
      console.warn('Settings API is legacy - may not work with CLI bridge')
      return {
        custom_output_path: null,
        active_profile: null,
        comfyui_path: null,
        google_sheets: {
          enabled: false,
          spreadsheet_id: null,
          credentials_path: null,
          sync_interval: 300,
          batch_size: 100
        },
        database_paths: []
      }
    },

    update: async (settings: any) => {
      console.warn('Settings updates not supported in CLI bridge mode')
      throw new Error('Settings must be configured through CLI')
    },

    listProfiles: async () => {
      return {}
    },

    saveProfile: async (name: string, custom_path?: string) => {
      throw new Error('Profile management must be done through CLI')
    },

    deleteProfile: async (name: string) => {
      throw new Error('Profile management must be done through CLI')
    },

    activateProfile: async (name: string) => {
      throw new Error('Profile management must be done through CLI')
    },

    validateComfyUI: async () => {
      throw new Error('ComfyUI validation must be done through CLI')
    },

    getDatabaseStats: async () => {
      // Redirect to jobs statistics
      const stats = await this.jobs.getStatistics()
      return {
        total_jobs: stats.job_statistics.total_jobs,
        job_statistics: stats.job_statistics,
        preset_statistics: stats.preset_statistics
      }
    },

    cleanupDatabase: async (daysToKeep: number = 30) => {
      throw new Error('Database cleanup must be done through CLI')
    },

    testSheetsConnection: async () => {
      throw new Error('Sheets connection must be tested through CLI')
    },
  }

  // Dataset Paths API (kept for compatibility)
  datasetPaths = {
    list: async () => {
      console.warn('Dataset paths API not available in CLI bridge mode')
      return []
    },

    add: async (path: string) => {
      throw new Error('Dataset paths must be managed through CLI')
    },

    remove: async (id: number) => {
      throw new Error('Dataset paths must be managed through CLI')
    },

    scan: async () => {
      console.warn('Dataset scanning not available in CLI bridge mode')
      return []
    },

    scanPath: async (id: number) => {
      console.warn('Dataset scanning not available in CLI bridge mode')
      return []
    },
  }

  // Health check
  async checkHealth() {
    const response = await this.http.get<{
      status: string
      services: Record<string, string>
      version: string
      mode?: string
    }>('/health')
    return response.data
  }
}

// Singleton instance
let clientInstance: AutoTrainXClient | null = null

export function getApiClient(): AutoTrainXClient {
  if (!clientInstance) {
    clientInstance = new AutoTrainXClient()
  }
  return clientInstance
}