'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useJob, useJobLogs, useCancelJob } from '@/lib/hooks/use-jobs'
import { useJobProgress } from '@/lib/hooks/use-job-progress'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  ArrowLeft, 
  Play, 
  Pause, 
  X, 
  Download,
  Clock,
  Calendar,
  Cpu,
  Database,
  FileText,
  AlertCircle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Terminal,
  Image
} from 'lucide-react'
import Link from 'next/link'
import { JobStatus } from '@/types/api'
import { cn } from '@/lib/utils'
import { formatDistanceToNow, format } from 'date-fns'

export default function JobDetailPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.id as string
  const [autoRefresh, setAutoRefresh] = useState(true)

  const { data: job, isLoading: isLoadingJob, refetch: refetchJob } = useJob(jobId)
  const { data: logs, isLoading: isLoadingLogs, refetch: refetchLogs } = useJobLogs(jobId)
  const { progress, isConnected } = useJobProgress(jobId)
  const cancelJobMutation = useCancelJob()

  // Auto-refresh logs and job data for active jobs
  useEffect(() => {
    if (!job || !autoRefresh) return
    
    const isActive = [
      JobStatus.IN_QUEUE,
      JobStatus.PREPARING_DATASET,
      JobStatus.CONFIGURING_PRESET,
      JobStatus.READY_FOR_TRAINING,
      JobStatus.TRAINING,
      JobStatus.GENERATING_PREVIEW
    ].includes(job.status)

    if (isActive) {
      const interval = setInterval(() => {
        refetchJob()
        refetchLogs()
      }, 3000) // Refresh every 3 seconds

      return () => clearInterval(interval)
    }
  }, [job, autoRefresh, refetchJob, refetchLogs])

  const handleCancel = async () => {
    if (confirm('Are you sure you want to cancel this job?')) {
      await cancelJobMutation.mutateAsync(jobId)
    }
  }

  if (isLoadingJob) {
    return <JobDetailSkeleton />
  }

  if (!job) {
    return (
      <div className="container py-6">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-medium">Job not found</p>
            <Button variant="outline" className="mt-4" onClick={() => router.back()}>
              Go Back
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const jobData = job
  const currentProgress = progress || {
    progress_percentage: jobData.progress_percentage || 0,
    current_step: jobData.current_step || 'Waiting...',
    message: '',
  }

  return (
    <div className="container py-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/jobs">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{jobData.name}</h1>
          <p className="text-muted-foreground">{jobData.description}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className="gap-2"
          >
            <RefreshCw className={cn("h-4 w-4", autoRefresh && "animate-spin")} />
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </Button>
          {[JobStatus.TRAINING, JobStatus.PREPARING_DATASET, JobStatus.CONFIGURING_PRESET, JobStatus.GENERATING_PREVIEW].includes(jobData.status) && (
            <Button 
              variant="destructive" 
              onClick={handleCancel}
              disabled={cancelJobMutation.isPending}
            >
              {cancelJobMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <X className="mr-2 h-4 w-4" />
              )}
              Cancel
            </Button>
          )}
          {jobData.status === JobStatus.DONE && jobData.results?.output_path && (
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Download Model
            </Button>
          )}
        </div>
      </div>

      {/* Status and Progress */}
      <div className="grid gap-6 mb-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Training Progress</CardTitle>
              <div className="flex items-center gap-2">
                <JobStatusBadge status={jobData.status} />
                {isConnected && [JobStatus.TRAINING, JobStatus.PREPARING_DATASET, JobStatus.CONFIGURING_PRESET, JobStatus.GENERATING_PREVIEW].includes(jobData.status) && (
                  <Badge variant="outline" className="gap-1">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                    </span>
                    Live
                  </Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Overall Progress</span>
                <span className="font-medium">{Math.round(currentProgress.progress_percentage || 0)}%</span>
              </div>
              <Progress value={currentProgress.progress_percentage || 0} className="h-3" />
            </div>

            {/* Current Step */}
            {currentProgress.current_step && (
              <div className="flex items-center gap-2 text-sm">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="text-muted-foreground">Current:</span>
                <span>{currentProgress.current_step}</span>
              </div>
            )}

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
              <StatsItem
                icon={Calendar}
                label="Created"
                value={format(new Date(jobData.created_at), 'MMM d, yyyy')}
              />
              <StatsItem
                icon={Clock}
                label="Duration"
                value={jobData.started_at ? 
                  formatDistanceToNow(new Date(jobData.started_at), { addSuffix: false }) : 
                  '-'
                }
              />
              <StatsItem
                icon={Database}
                label="Dataset"
                value={jobData.config.dataset_name}
              />
              <StatsItem
                icon={Cpu}
                label="Preset"
                value={jobData.config.preset}
              />
            </div>
          </CardContent>
        </Card>

        {/* Tabs for Details */}
        <Tabs defaultValue="logs" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="logs">Logs</TabsTrigger>
            <TabsTrigger value="config">Configuration</TabsTrigger>
            <TabsTrigger value="results">Results</TabsTrigger>
          </TabsList>

          {/* Logs Tab */}
          <TabsContent value="logs">
            <Card>
              <CardHeader>
                <CardTitle>Training Logs</CardTitle>
                <CardDescription>
                  Output from SD-Scripts training and ComfyUI preview generation
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="training" className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="training">
                      <Terminal className="mr-2 h-4 w-4" />
                      Training Log
                    </TabsTrigger>
                    <TabsTrigger value="preview">
                      <Image className="mr-2 h-4 w-4" />
                      Preview Log
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="training" className="mt-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-medium">SD-Scripts Training Output</h3>
                        {logs?.training_log && (
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => {
                              const blob = new Blob([logs.training_log], { type: 'text/plain' })
                              const url = URL.createObjectURL(blob)
                              const a = document.createElement('a')
                              a.href = url
                              a.download = `training_${jobId}.log`
                              a.click()
                              URL.revokeObjectURL(url)
                            }}
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Download
                          </Button>
                        )}
                      </div>
                      <ScrollArea className="h-[400px] w-full rounded-md border p-4 bg-muted/50">
                        {isLoadingLogs ? (
                          <div className="space-y-2">
                            {Array.from({ length: 10 }).map((_, i) => (
                              <Skeleton key={i} className="h-4 w-full" />
                            ))}
                          </div>
                        ) : logs?.training_log ? (
                          <pre className="text-xs font-mono whitespace-pre-wrap">
                            {logs.training_log}
                          </pre>
                        ) : (
                          <p className="text-muted-foreground text-center py-8">
                            No training log available
                          </p>
                        )}
                      </ScrollArea>
                    </div>
                  </TabsContent>

                  <TabsContent value="preview" className="mt-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-medium">ComfyUI Preview Generation</h3>
                        {logs?.preview_log && (
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => {
                              const blob = new Blob([logs.preview_log], { type: 'text/plain' })
                              const url = URL.createObjectURL(blob)
                              const a = document.createElement('a')
                              a.href = url
                              a.download = `preview_${jobId}.log`
                              a.click()
                              URL.revokeObjectURL(url)
                            }}
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Download
                          </Button>
                        )}
                      </div>
                      <ScrollArea className="h-[400px] w-full rounded-md border p-4 bg-muted/50">
                        {isLoadingLogs ? (
                          <div className="space-y-2">
                            {Array.from({ length: 10 }).map((_, i) => (
                              <Skeleton key={i} className="h-4 w-full" />
                            ))}
                          </div>
                        ) : logs?.preview_log ? (
                          <pre className="text-xs font-mono whitespace-pre-wrap">
                            {logs.preview_log}
                          </pre>
                        ) : (
                          <p className="text-muted-foreground text-center py-8">
                            No preview generation log available
                          </p>
                        )}
                      </ScrollArea>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Configuration Tab */}
          <TabsContent value="config">
            <Card>
              <CardHeader>
                <CardTitle>Job Configuration</CardTitle>
                <CardDescription>
                  Parameters used for this training job
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <ConfigItem label="Job ID" value={jobData.id} />
                  <ConfigItem label="Pipeline Mode" value={jobData.mode} />
                  <ConfigItem label="Dataset" value={jobData.config.dataset_name} />
                  <ConfigItem label="Preset" value={jobData.config.preset} />
                  {jobData.config.parameters && (
                    <div>
                      <p className="text-sm font-medium mb-2">Custom Parameters:</p>
                      <pre className="text-sm bg-muted p-3 rounded-md overflow-auto">
                        {JSON.stringify(jobData.config.parameters, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Results Tab */}
          <TabsContent value="results">
            <Card>
              <CardHeader>
                <CardTitle>Training Results</CardTitle>
                <CardDescription>
                  Output and metrics from the completed training
                </CardDescription>
              </CardHeader>
              <CardContent>
                {jobData.status === JobStatus.DONE ? (
                  <div className="space-y-4">
                    {jobData.results?.output_path && (
                      <ConfigItem label="Output Path" value={jobData.results.output_path} />
                    )}
                    {jobData.results?.metrics && (
                      <div>
                        <p className="text-sm font-medium mb-2">Training Metrics:</p>
                        <pre className="text-sm bg-muted p-3 rounded-md overflow-auto">
                          {JSON.stringify(jobData.results.metrics, null, 2)}
                        </pre>
                      </div>
                    )}
                    <Button className="w-full">
                      <Download className="mr-2 h-4 w-4" />
                      Download Trained Model
                    </Button>
                  </div>
                ) : jobData.status === JobStatus.FAILED ? (
                  <div className="flex flex-col items-center py-8">
                    <AlertCircle className="h-12 w-12 text-destructive mb-4" />
                    <p className="text-lg font-medium mb-2">Training Failed</p>
                    {jobData.error_message && (
                      <p className="text-sm text-muted-foreground text-center">
                        {jobData.error_message}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-muted-foreground text-center py-8">
                    Results will be available once training is complete
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

function JobDetailSkeleton() {
  return (
    <div className="container py-6">
      <div className="flex items-center gap-4 mb-6">
        <Skeleton className="h-10 w-10" />
        <div className="flex-1">
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-96" />
        </div>
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    </div>
  )
}

function StatsItem({ 
  icon: Icon, 
  label, 
  value 
}: { 
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string 
}) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium">{value}</p>
      </div>
    </div>
  )
}

function ConfigItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-2 border-b last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  )
}

function JobStatusBadge({ status }: { status: JobStatus }) {
  const config = {
    [JobStatus.PENDING]: { 
      label: 'Pending', 
      icon: Clock,
      className: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100' 
    },
    [JobStatus.IN_QUEUE]: { 
      label: 'In Queue', 
      icon: Clock,
      className: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100'
    },
    [JobStatus.PREPARING_DATASET]: { 
      label: 'Preparing Dataset', 
      icon: Loader2,
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100' 
    },
    [JobStatus.CONFIGURING_PRESET]: { 
      label: 'Configuring Preset', 
      icon: Loader2,
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100' 
    },
    [JobStatus.READY_FOR_TRAINING]: { 
      label: 'Ready for Training', 
      icon: Clock,
      className: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-100'
    },
    [JobStatus.TRAINING]: { 
      label: 'Training', 
      icon: Loader2,
      className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100' 
    },
    [JobStatus.GENERATING_PREVIEW]: { 
      label: 'Generating Preview', 
      icon: Loader2,
      className: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-100'
    },
    [JobStatus.DONE]: { 
      label: 'Done', 
      icon: CheckCircle2,
      className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100' 
    },
    [JobStatus.FAILED]: { 
      label: 'Failed', 
      icon: AlertCircle,
      className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100' 
    },
    [JobStatus.CANCELLED]: { 
      label: 'Cancelled', 
      icon: X,
      className: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100' 
    },
  }

  const { label, icon: Icon, className } = config[status] || config[JobStatus.PENDING]
  
  const isAnimated = [
    JobStatus.PREPARING_DATASET,
    JobStatus.CONFIGURING_PRESET,
    JobStatus.TRAINING,
    JobStatus.GENERATING_PREVIEW
  ].includes(status)

  return (
    <Badge className={cn("font-medium gap-1", className)}>
      <Icon className={cn("h-3 w-3", isAnimated && "animate-spin")} />
      {label}
    </Badge>
  )
}