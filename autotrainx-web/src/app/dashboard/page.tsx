'use client'

import { useJobs } from '@/lib/hooks/use-jobs'
import { JobStatus } from '@/types/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Database,
  FolderOpen,
  Settings,
  TrendingUp,
  Calendar,
  Zap,
  PlayCircle,
  PauseCircle,
  RotateCcw,
  AlertTriangle,
  BarChart3,
  Timer,
  HardDrive,
  Cpu,
  MemoryStick
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

const api = getApiClient()

export default function DashboardPage() {
  const [currentTime, setCurrentTime] = useState<Date | null>(null)
  const [isClient, setIsClient] = useState(false)
  const { data: jobsData, isLoading: jobsLoading } = useJobs({ page_size: 50 })
  
  // System health data
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: () => api.checkHealth(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Datasets data
  const { data: datasetsData, isLoading: datasetsLoading } = useQuery({
    queryKey: ['datasets-stats'],
    queryFn: async () => {
      const response = await api.datasets.list({ page_size: 100 })
      return response
    },
    refetchInterval: 60000, // Refresh every minute
  })

  // Models data
  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['models-stats'],
    queryFn: async () => {
      const response = await fetch('/api/backend/models/paths')
      if (!response.ok) throw new Error('Failed to fetch models')
      return response.json()
    },
    refetchInterval: 60000,
  })

  // Initialize client-side only
  useEffect(() => {
    setIsClient(true)
    setCurrentTime(new Date())
  }, [])

  // Update time every second (only on client)
  useEffect(() => {
    if (!isClient) return
    
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [isClient])

  const jobStats = {
    total: jobsData?.total_count || 0,
    pending: jobsData?.items.filter(job => job.status === JobStatus.PENDING).length || 0,
    preparing: jobsData?.items.filter(job => job.status === JobStatus.PREPARING).length || 0,
    training: jobsData?.items.filter(job => job.status === JobStatus.TRAINING).length || 0,
    done: jobsData?.items.filter(job => job.status === JobStatus.DONE).length || 0,
    failed: jobsData?.items.filter(job => job.status === JobStatus.FAILED).length || 0,
    cancelled: jobsData?.items.filter(job => job.status === JobStatus.CANCELLED).length || 0,
  }

  const successRate = jobStats.total > 0 ? Math.round((jobStats.done / jobStats.total) * 100) : 0
  const activeJobs = jobStats.preparing + jobStats.training
  const completedJobs = jobStats.done + jobStats.failed + jobStats.cancelled

  return (
    <motion.div 
      className="container py-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Header */}
      <motion.div 
        className="flex items-center justify-between mb-8"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <div>
          <h1 className="text-3xl font-bold">AutoTrainX Dashboard</h1>
          <p className="text-muted-foreground">
            {currentTime ? `${currentTime.toLocaleDateString('en-US')} • ${currentTime.toLocaleTimeString('en-US')}` : ''}
          </p>
        </div>
        <motion.div 
          className="flex gap-2"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Link href="/dashboard/jobs/new">
            <Button>
              <PlayCircle className="mr-2 h-4 w-4" />
              New Training
            </Button>
          </Link>
          <Link href="/dashboard/settings">
            <Button variant="outline">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
          </Link>
        </motion.div>
      </motion.div>

      {/* System Status */}
      <motion.div 
        className="grid gap-4 md:grid-cols-4 mb-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <SystemStatusCard
            title="System Status"
            status={healthData?.status || 'unknown'}
            icon={Activity}
            isLoading={healthLoading}
          />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <StatsCard
            title="Active Jobs"
            value={activeJobs}
            icon={Zap}
            isLoading={jobsLoading}
            className="text-blue-600"
            trend={activeJobs > 0 ? 'up' : 'stable'}
          />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
        >
          <StatsCard
            title="Success Rate"
            value={`${successRate}%`}
            icon={TrendingUp}
            isLoading={jobsLoading}
            className={successRate >= 80 ? "text-green-600" : successRate >= 60 ? "text-yellow-600" : "text-red-600"}
          />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.7 }}
        >
          <StatsCard
            title="Total Datasets"
            value={datasetsData?.total_count || 0}
            icon={Database}
            isLoading={datasetsLoading}
            className="text-purple-600"
          />
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.8 }}
      >
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="jobs">Jobs</TabsTrigger>
            <TabsTrigger value="resources">Resources</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* Job Statistics */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Training Jobs Overview
                </CardTitle>
                <CardDescription>Current status of all training jobs</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{jobStats.training}</div>
                    <div className="text-sm text-muted-foreground">Training</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-yellow-600">{jobStats.preparing}</div>
                    <div className="text-sm text-muted-foreground">Preparing</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">{jobStats.done}</div>
                    <div className="text-sm text-muted-foreground">Completed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-600">{jobStats.failed}</div>
                    <div className="text-sm text-muted-foreground">Failed</div>
                  </div>
                </div>
                
                {jobStats.total > 0 && (
                  <div className="mt-4">
                    <div className="flex justify-between text-sm text-muted-foreground mb-2">
                      <span>Progress</span>
                      <span>{completedJobs}/{jobStats.total} jobs completed</span>
                    </div>
                    <Progress value={(completedJobs / jobStats.total) * 100} className="h-2" />
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Link href="/dashboard/jobs/new">
                  <Button className="w-full" size="sm">
                    <PlayCircle className="mr-2 h-4 w-4" />
                    Start New Training
                  </Button>
                </Link>
                <Link href="/dashboard/datasets">
                  <Button variant="outline" className="w-full" size="sm">
                    <Database className="mr-2 h-4 w-4" />
                    Manage Datasets
                  </Button>
                </Link>
                <Link href="/dashboard/models">
                  <Button variant="outline" className="w-full" size="sm">
                    <FolderOpen className="mr-2 h-4 w-4" />
                    View Models
                  </Button>
                </Link>
                <Link href="/dashboard/presets">
                  <Button variant="outline" className="w-full" size="sm">
                    <Zap className="mr-2 h-4 w-4" />
                    Training Presets
                  </Button>
                </Link>
                <Link href="/dashboard/database">
                  <Button variant="outline" className="w-full" size="sm">
                    <HardDrive className="mr-2 h-4 w-4" />
                    Database
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Recent Activity
              </CardTitle>
              <CardDescription>Latest training jobs and system events</CardDescription>
            </CardHeader>
            <CardContent>
              {jobsLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="flex items-center space-x-4">
                      <Skeleton className="h-10 w-10 rounded-full" />
                      <div className="space-y-2">
                        <Skeleton className="h-4 w-[250px]" />
                        <Skeleton className="h-4 w-[200px]" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {jobsData?.items.slice(0, 8).map((job) => (
                    <Link key={job.id} href={`/dashboard/jobs/${job.id}`}>
                      <div className="flex items-center space-x-4 p-3 rounded-lg border hover:bg-muted/50 transition-colors cursor-pointer">
                        <div className="flex-shrink-0">
                          <JobStatusIcon status={job.status} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{job.name}</p>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span>{job.config.dataset_name}</span>
                            <span>•</span>
                            <span>{job.config.preset}</span>
                            <span>•</span>
                            <span>{new Date(job.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <div className="flex-shrink-0">
                          <JobStatusBadge status={job.status} />
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="jobs" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatsCard title="Total Jobs" value={jobStats.total} icon={Activity} isLoading={jobsLoading} />
            <StatsCard title="Pending" value={jobStats.pending} icon={Clock} isLoading={jobsLoading} className="text-gray-600" />
            <StatsCard title="Training" value={jobStats.training} icon={PlayCircle} isLoading={jobsLoading} className="text-blue-600" />
            <StatsCard title="Completed" value={jobStats.done} icon={CheckCircle2} isLoading={jobsLoading} className="text-green-600" />
          </div>

          {/* Detailed Jobs Table */}
          <Card>
            <CardHeader>
              <CardTitle>All Jobs</CardTitle>
              <CardDescription>Complete list of training jobs with detailed status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {jobsData?.items.map((job) => (
                  <Link key={job.id} href={`/dashboard/jobs/${job.id}`}>
                    <div className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors cursor-pointer">
                      <div className="flex items-center space-x-4">
                        <JobStatusIcon status={job.status} />
                        <div>
                          <p className="font-medium">{job.name}</p>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span>{job.config.dataset_name}</span>
                            <span>•</span>
                            <span>{job.config.preset}</span>
                            <span>•</span>
                            <span>{formatDate(job.created_at)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        {job.started_at && (
                          <div className="text-right text-sm text-muted-foreground">
                            <div className="flex items-center gap-1">
                              <Timer className="h-3 w-3" />
                              {formatDuration(job.started_at, job.ended_at)}
                            </div>
                          </div>
                        )}
                        <JobStatusBadge status={job.status} />
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="resources" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Datasets
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{datasetsData?.total_count || 0}</div>
                <p className="text-sm text-muted-foreground">Available datasets</p>
                <Link href="/dashboard/datasets">
                  <Button variant="outline" size="sm" className="mt-2">
                    View All
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FolderOpen className="h-5 w-5" />
                  Models
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{Array.isArray(modelsData) ? modelsData.length : 0}</div>
                <p className="text-sm text-muted-foreground">Trained models</p>
                <Link href="/dashboard/models">
                  <Button variant="outline" size="sm" className="mt-2">
                    View All
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  System
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm">Status</span>
                    <Badge variant={healthData?.status === 'healthy' ? 'default' : 'destructive'}>
                      {healthData?.status || 'unknown'}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Version</span>
                    <span className="text-sm text-muted-foreground">{healthData?.version || '1.0.0'}</span>
                  </div>
                </div>
                <Link href="/dashboard/settings">
                  <Button variant="outline" size="sm" className="mt-2">
                    Configure
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Success Rate Analysis</CardTitle>
                <CardDescription>Training job success statistics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-center">
                  <div className="text-4xl font-bold text-green-600">{successRate}%</div>
                  <p className="text-sm text-muted-foreground">Overall Success Rate</p>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Successful ({jobStats.done})</span>
                    <span>{jobStats.total > 0 ? Math.round((jobStats.done / jobStats.total) * 100) : 0}%</span>
                  </div>
                  <Progress value={jobStats.total > 0 ? (jobStats.done / jobStats.total) * 100 : 0} className="h-2 bg-green-100" />
                  
                  <div className="flex justify-between text-sm">
                    <span>Failed ({jobStats.failed})</span>
                    <span>{jobStats.total > 0 ? Math.round((jobStats.failed / jobStats.total) * 100) : 0}%</span>
                  </div>
                  <Progress value={jobStats.total > 0 ? (jobStats.failed / jobStats.total) * 100 : 0} className="h-2 bg-red-100" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Activity Summary</CardTitle>
                <CardDescription>Recent system activity metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">{activeJobs}</div>
                    <p className="text-sm text-muted-foreground">Active Jobs</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold">{completedJobs}</div>
                    <p className="text-sm text-muted-foreground">Completed Jobs</p>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Active</span>
                    <span className="text-blue-600">{activeJobs} jobs</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Completed Today</span>
                    <span className="text-green-600">
                      {jobsData?.items.filter(job => 
                        job.status === JobStatus.DONE && 
                        new Date(job.created_at).toDateString() === new Date().toDateString()
                      ).length || 0} jobs
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
      </motion.div>
    </motion.div>
  )
}

// Helper functions
function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(startDate: string, endDate?: string) {
  const start = new Date(startDate)
  const end = endDate ? new Date(endDate) : new Date()
  const diff = end.getTime() - start.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  
  if (hours > 0 && endDate) {
    return `${hours}h ${minutes % 60}m`
  } else if (minutes > 0) {
    return endDate ? `${minutes}m` : `${minutes}m (running)`
  } else {
    return endDate ? '<1m' : 'Just started'
  }
}

function StatsCard({
  title,
  value,
  icon: Icon,
  isLoading,
  className,
  trend,
}: {
  title: string
  value: number | string
  icon: React.ComponentType<{ className?: string }>
  isLoading: boolean
  className?: string
  trend?: 'up' | 'down' | 'stable'
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className="flex items-center gap-1">
          {trend === 'up' && <TrendingUp className="h-3 w-3 text-green-600" />}
          {trend === 'down' && <TrendingUp className="h-3 w-3 text-red-600 rotate-180" />}
          <Icon className={cn("h-4 w-4 text-muted-foreground", className)} />
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <div className="text-2xl font-bold">{value}</div>
        )}
      </CardContent>
    </Card>
  )
}

function SystemStatusCard({
  title,
  status,
  icon: Icon,
  isLoading,
}: {
  title: string
  status: string
  icon: React.ComponentType<{ className?: string }>
  isLoading: boolean
}) {
  const statusConfig = {
    healthy: { color: 'text-green-600', bg: 'bg-green-100', label: 'Healthy' },
    unhealthy: { color: 'text-red-600', bg: 'bg-red-100', label: 'Unhealthy' },
    unknown: { color: 'text-gray-600', bg: 'bg-gray-100', label: 'Unknown' },
  }

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.unknown

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-20" />
        ) : (
          <div className="flex items-center gap-2">
            <div className={cn("w-2 h-2 rounded-full", config.bg)} />
            <span className={cn("font-medium", config.color)}>{config.label}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function JobStatusIcon({ status }: { status: JobStatus }) {
  const iconConfig = {
    [JobStatus.PENDING]: { icon: Clock, className: 'text-gray-500' },
    [JobStatus.PREPARING]: { icon: RotateCcw, className: 'text-yellow-500' },
    [JobStatus.TRAINING]: { icon: PlayCircle, className: 'text-blue-500' },
    [JobStatus.DONE]: { icon: CheckCircle2, className: 'text-green-500' },
    [JobStatus.FAILED]: { icon: XCircle, className: 'text-red-500' },
    [JobStatus.CANCELLED]: { icon: PauseCircle, className: 'text-gray-500' },
  }

  const config = iconConfig[status] || iconConfig[JobStatus.PENDING]
  const Icon = config.icon

  return <Icon className={cn("h-5 w-5", config.className)} />
}

function JobStatusBadge({ status }: { status: JobStatus }) {
  const config = {
    [JobStatus.PENDING]: { label: 'Pending', className: 'bg-gray-100 text-gray-800' },
    [JobStatus.PREPARING]: { label: 'Preparing', className: 'bg-yellow-100 text-yellow-800' },
    [JobStatus.TRAINING]: { label: 'Training', className: 'bg-blue-100 text-blue-800' },
    [JobStatus.DONE]: { label: 'Completed', className: 'bg-green-100 text-green-800' },
    [JobStatus.FAILED]: { label: 'Failed', className: 'bg-red-100 text-red-800' },
    [JobStatus.CANCELLED]: { label: 'Cancelled', className: 'bg-gray-100 text-gray-800' },
  }

  const { label, className } = config[status] || config[JobStatus.PENDING]

  return (
    <span className={cn("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium", className)}>
      {label}
    </span>
  )
}