'use client'

import { useState, useMemo, useEffect } from 'react'
import Link from 'next/link'
import { useJobs } from '@/lib/hooks/use-jobs'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { JobStatus, PipelineMode } from '@/types/api'
import { 
  Plus, 
  Search,
  Filter,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Clock 
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function JobsPage() {
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'all'>('all')
  const [modeFilter, setModeFilter] = useState<PipelineMode | 'all'>('all')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const pageSize = 10
  
  const { data: jobsData, isLoading, isFetching, dataUpdatedAt } = useJobs({ 
    page, 
    page_size: pageSize,
    status: statusFilter === 'all' ? undefined : statusFilter,
    mode: modeFilter === 'all' ? undefined : modeFilter,
  }, {
    refetchInterval: autoRefresh ? 5000 : false // Refresh every 5 seconds if enabled
  })

  // Client-side search filtering
  const filteredJobs = useMemo(() => {
    if (!jobsData?.items || !searchQuery) return jobsData?.items || []
    
    return jobsData.items.filter(job => 
      job.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.config.dataset_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.config.preset.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [jobsData?.items, searchQuery])

  const totalPages = jobsData?.total_pages || 1

  return (
    <div className="container py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Training Jobs</h1>
          <p className="text-muted-foreground">
            Manage and monitor your model training jobs
          </p>
        </div>
        <Button asChild>
          <Link href="/dashboard/jobs/new">
            <Plus className="mr-2 h-4 w-4" />
            New Training
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="space-y-4">
            {/* First row: Title and auto-refresh */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-center gap-4">
                <div>
                  <CardTitle>All Jobs</CardTitle>
                  <CardDescription className="flex items-center gap-4">
                    <span>Total: {jobsData?.total_count || 0} jobs</span>
                    {dataUpdatedAt && (
                      <span className="flex items-center gap-1 text-xs">
                        <Clock className="h-3 w-3" />
                        {new Date(dataUpdatedAt).toLocaleTimeString()}
                      </span>
                    )}
                  </CardDescription>
                </div>
                {isFetching && !isLoading && (
                  <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
              
              {/* Auto-refresh toggle */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setAutoRefresh(!autoRefresh)}
                className="gap-2"
              >
                <RefreshCw className={cn("h-4 w-4", autoRefresh && "animate-spin")} />
                {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
              </Button>
            </div>
            
            {/* Second row: Filters */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search jobs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-full sm:w-[200px]"
                />
              </div>
              
              {/* Status Filter */}
              <Select
                value={statusFilter}
                onValueChange={(value) => setStatusFilter(value as JobStatus | 'all')}
              >
                <SelectTrigger className="w-full sm:w-[140px]">
                  <Filter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value={JobStatus.PENDING}>Pending</SelectItem>
                  <SelectItem value={JobStatus.IN_QUEUE}>In Queue</SelectItem>
                  <SelectItem value={JobStatus.PREPARING_DATASET}>Preparing Dataset</SelectItem>
                  <SelectItem value={JobStatus.CONFIGURING_PRESET}>Configuring Preset</SelectItem>
                  <SelectItem value={JobStatus.READY_FOR_TRAINING}>Ready for Training</SelectItem>
                  <SelectItem value={JobStatus.TRAINING}>Training</SelectItem>
                  <SelectItem value={JobStatus.GENERATING_PREVIEW}>Generating Preview</SelectItem>
                  <SelectItem value={JobStatus.DONE}>Done</SelectItem>
                  <SelectItem value={JobStatus.FAILED}>Failed</SelectItem>
                  <SelectItem value={JobStatus.CANCELLED}>Cancelled</SelectItem>
                </SelectContent>
              </Select>
              
              {/* Mode Filter */}
              <Select
                value={modeFilter}
                onValueChange={(value) => setModeFilter(value as PipelineMode | 'all')}
              >
                <SelectTrigger className="w-full sm:w-[120px]">
                  <SelectValue placeholder="Mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Modes</SelectItem>
                  <SelectItem value={PipelineMode.SINGLE}>Single</SelectItem>
                  <SelectItem value={PipelineMode.BATCH}>Batch</SelectItem>
                  <SelectItem value={PipelineMode.VARIATIONS}>Variations</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Dataset</TableHead>
                  <TableHead>Preset</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Progress</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={8}>
                        <Skeleton className="h-10 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                ) : filteredJobs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      {searchQuery ? 'No jobs found matching your search' : 'No jobs found'}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredJobs.map((job) => (
                    <TableRow key={job.id}>
                      <TableCell className="font-medium">
                        <Link 
                          href={`/dashboard/jobs/${job.id}`}
                          className="hover:underline"
                        >
                          {job.name}
                        </Link>
                      </TableCell>
                      <TableCell>{job.config.dataset_name}</TableCell>
                      <TableCell>{job.config.preset}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {job.mode}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <JobStatusBadge status={job.status} />
                      </TableCell>
                      <TableCell>
                        {job.progress_percentage !== null && job.progress_percentage !== undefined ? (
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <div className="w-20 bg-secondary rounded-full h-2">
                                <div 
                                  className="bg-primary h-2 rounded-full transition-all duration-300"
                                  style={{ width: `${job.progress_percentage}%` }}
                                />
                              </div>
                              <span className="text-sm font-medium">
                                {Math.round(job.progress_percentage)}%
                              </span>
                            </div>
                            {job.current_step && (
                              <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                {job.current_step}
                              </p>
                            )}
                            {job.completed_steps !== undefined && job.total_steps && (
                              <p className="text-xs text-muted-foreground">
                                Step {job.completed_steps} of {job.total_steps}
                              </p>
                            )}
                          </div>
                        ) : (
                          <span className="text-sm text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {new Date(job.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button 
                          variant="ghost" 
                          size="icon"
                          disabled={job.status !== JobStatus.RUNNING}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">
                Showing page {page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function JobStatusBadge({ status }: { status: JobStatus }) {
  const config = {
    [JobStatus.PENDING]: { 
      label: 'Pending', 
      className: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100',
      icon: <Clock className="h-3 w-3 mr-1" />
    },
    [JobStatus.IN_QUEUE]: { 
      label: 'In Queue', 
      className: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100',
      icon: <Clock className="h-3 w-3 mr-1" />
    },
    [JobStatus.PREPARING_DATASET]: { 
      label: 'Preparing Dataset', 
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100',
      icon: <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
    },
    [JobStatus.CONFIGURING_PRESET]: { 
      label: 'Configuring Preset', 
      className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100',
      icon: <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
    },
    [JobStatus.READY_FOR_TRAINING]: { 
      label: 'Ready for Training', 
      className: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-100',
      icon: <Clock className="h-3 w-3 mr-1" />
    },
    [JobStatus.TRAINING]: { 
      label: 'Training', 
      className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100',
      icon: <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
    },
    [JobStatus.GENERATING_PREVIEW]: { 
      label: 'Generating Preview', 
      className: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-100',
      icon: <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
    },
    [JobStatus.DONE]: { 
      label: 'Done', 
      className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100' 
    },
    [JobStatus.FAILED]: { 
      label: 'Failed', 
      className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100' 
    },
    [JobStatus.CANCELLED]: { 
      label: 'Cancelled', 
      className: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100' 
    },
  }

  const { label, className, icon } = config[status] || config[JobStatus.PENDING]

  return (
    <Badge className={cn("font-medium inline-flex items-center", className)}>
      {icon}
      {label}
    </Badge>
  )
}