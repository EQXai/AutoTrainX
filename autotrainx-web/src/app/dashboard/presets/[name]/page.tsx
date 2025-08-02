'use client'

import { use } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { 
  ArrowLeft,
  Settings,
  Zap,
  Layers,
  Edit,
  Trash2,
  Copy,
  Download,
  FileText,
  Code2,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  Play,
  Info
} from 'lucide-react'
import { toast } from 'sonner'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

const api = getApiClient()

interface PageProps {
  params: Promise<{ name: string }>
}

export default function PresetDetailsPage({ params }: PageProps) {
  const { name } = use(params)
  const router = useRouter()
  const queryClient = useQueryClient()
  const decodedName = decodeURIComponent(name)

  // Fetch preset details
  const { data: preset, isLoading, error } = useQuery({
    queryKey: ['preset-details', decodedName],
    queryFn: () => api.presets.get(decodedName),
  })

  // Fetch preset parameters
  const { data: parameters, isLoading: parametersLoading } = useQuery({
    queryKey: ['preset-parameters', decodedName],
    queryFn: () => api.presets.getParameters(decodedName),
    enabled: !!preset,
  })

  // Delete preset mutation
  const deletePresetMutation = useMutation({
    mutationFn: () => api.presets.delete(decodedName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['presets'] })
      toast.success('Preset deleted successfully')
      router.push('/dashboard/presets')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete preset')
    }
  })

  // Copy preset mutation (clone)
  const copyPresetMutation = useMutation({
    mutationFn: async () => {
      const newName = `${decodedName}_copy_${Date.now()}`
      return api.presets.create({
        name: newName,
        description: `Copy of ${preset?.description || decodedName}`,
        architecture: preset?.architecture || 'custom',
        parameters: parameters || {},
        base_preset: decodedName
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['presets'] })
      toast.success('Preset copied successfully')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to copy preset')
    }
  })

  const getArchitectureIcon = (architecture: string | null) => {
    switch (architecture) {
      case 'flux': return <Zap className="h-5 w-5" />
      case 'sdxl': return <Layers className="h-5 w-5" />
      default: return <Settings className="h-5 w-5" />
    }
  }

  const getArchitectureColor = (architecture: string | null) => {
    switch (architecture) {
      case 'flux': return 'bg-blue-100 text-blue-800'
      case 'sdxl': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'base': return 'bg-green-100 text-green-800'
      case 'custom': return 'bg-orange-100 text-orange-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const handleDeletePreset = () => {
    if (confirm(`Are you sure you want to delete the preset "${decodedName}"? This action cannot be undone.`)) {
      deletePresetMutation.mutate()
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  if (error) {
    return (
      <div className="container py-6">
        <Card>
          <CardContent className="text-center py-8">
            <AlertTriangle className="mx-auto h-12 w-12 text-red-500" />
            <h3 className="mt-4 text-lg font-semibold">Preset Not Found</h3>
            <p className="text-muted-foreground">
              The preset "{decodedName}" could not be found.
            </p>
            <Link href="/dashboard/presets">
              <Button className="mt-4">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Presets
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/presets">
            <Button variant="outline" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-4 w-48" />
              </div>
            ) : (
              <>
                <h1 className="text-3xl font-bold flex items-center gap-2">
                  {getArchitectureIcon(preset?.architecture)}
                  {decodedName}
                </h1>
                <p className="text-muted-foreground">
                  {preset?.description || 'No description available'}
                </p>
              </>
            )}
          </div>
        </div>

        {!isLoading && preset && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => copyPresetMutation.mutate()}
              disabled={copyPresetMutation.isPending}
            >
              <Copy className="mr-2 h-4 w-4" />
              Copy
            </Button>
            
            {preset.category === 'custom' && (
              <>
                <Button variant="outline">
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </Button>
                
                <Button
                  variant="destructive"
                  onClick={handleDeletePreset}
                  disabled={deletePresetMutation.isPending}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-5 w-5" />
                Overview
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-8 w-1/2" />
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-sm font-medium mb-2">Category</h4>
                      <Badge className={getCategoryColor(preset?.category || 'unknown')}>
                        {preset?.category || 'Unknown'}
                      </Badge>
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-medium mb-2">Architecture</h4>
                      {preset?.architecture ? (
                        <Badge className={getArchitectureColor(preset.architecture)}>
                          {preset.architecture.toUpperCase()}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">Not specified</span>
                      )}
                    </div>
                  </div>

                  {preset?.config_files && preset.config_files.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium mb-2">Configuration Files</h4>
                      <div className="space-y-2">
                        {preset.config_files.map((file: string) => (
                          <div key={file} className="flex items-center gap-2 p-2 bg-muted rounded">
                            <FileText className="h-4 w-4" />
                            <span className="font-mono text-sm">{file}</span>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyToClipboard(file)}
                              className="ml-auto"
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Parameters */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Parameters
              </CardTitle>
              <CardDescription>
                Training parameters and configuration values
              </CardDescription>
            </CardHeader>
            <CardContent>
              {parametersLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="flex justify-between">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-4 w-20" />
                    </div>
                  ))}
                </div>
              ) : parameters ? (
                <Tabs defaultValue="table" className="w-full">
                  <TabsList>
                    <TabsTrigger value="table">Table View</TabsTrigger>
                    <TabsTrigger value="json">JSON View</TabsTrigger>
                  </TabsList>

                  <TabsContent value="table" className="mt-4">
                    <div className="space-y-3">
                      {Object.entries(parameters).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between py-2 border-b">
                          <div>
                            <span className="font-medium">{key}</span>
                            <p className="text-sm text-muted-foreground">
                              {getParameterDescription(key)}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <code className="bg-muted px-2 py-1 rounded text-sm">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </code>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyToClipboard(String(value))}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </TabsContent>

                  <TabsContent value="json" className="mt-4">
                    <div className="relative">
                      <Button
                        variant="outline"
                        size="sm"
                        className="absolute top-2 right-2 z-10"
                        onClick={() => copyToClipboard(JSON.stringify(parameters, null, 2))}
                      >
                        <Copy className="h-3 w-3 mr-1" />
                        Copy
                      </Button>
                      <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                        <code>{JSON.stringify(parameters, null, 2)}</code>
                      </pre>
                    </div>
                  </TabsContent>
                </Tabs>
              ) : (
                <p className="text-muted-foreground">No parameters available</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Link href={`/dashboard/jobs/new?preset=${encodeURIComponent(decodedName)}`}>
                <Button className="w-full">
                  <Play className="mr-2 h-4 w-4" />
                  Use for Training
                </Button>
              </Link>
              
              <Button
                variant="outline"
                className="w-full"
                onClick={() => copyPresetMutation.mutate()}
                disabled={copyPresetMutation.isPending}
              >
                <Copy className="mr-2 h-4 w-4" />
                Create Copy
              </Button>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => copyToClipboard(JSON.stringify(parameters, null, 2))}
              >
                <Download className="mr-2 h-4 w-4" />
                Export JSON
              </Button>
            </CardContent>
          </Card>

          {/* Key Parameters Summary */}
          {!parametersLoading && parameters && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Key Parameters
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {getKeyParameters(parameters).map(({ key, value, label }) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-sm font-medium">{label}:</span>
                    <code className="text-sm">{value}</code>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Usage Stats */}
          <Card>
            <CardHeader>
              <CardTitle>Usage Statistics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm">Times Used:</span>
                  <span className="text-sm font-medium">-</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Success Rate:</span>
                  <span className="text-sm font-medium">-</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Last Used:</span>
                  <span className="text-sm font-medium">-</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Usage statistics coming soon
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

// Helper functions
function getParameterDescription(key: string): string {
  const descriptions: Record<string, string> = {
    learning_rate: 'Controls how fast the model learns',
    batch_size: 'Number of samples processed together',
    num_epochs: 'Number of complete passes through the dataset',
    resolution: 'Image resolution for training',
    rank: 'LoRA rank parameter',
    alpha: 'LoRA alpha scaling parameter',
    optimizer: 'Optimization algorithm used',
    mixed_precision: 'Precision format for training',
    lr_scheduler: 'Learning rate scheduling strategy',
    warmup_steps: 'Number of warmup steps for learning rate',
  }
  return descriptions[key] || 'Training parameter'
}

function getKeyParameters(parameters: Record<string, any>) {
  const keyParams = [
    { key: 'learning_rate', label: 'Learning Rate' },
    { key: 'batch_size', label: 'Batch Size' },
    { key: 'num_epochs', label: 'Epochs' },
    { key: 'resolution', label: 'Resolution' },
    { key: 'rank', label: 'LoRA Rank' },
    { key: 'alpha', label: 'LoRA Alpha' },
  ]

  return keyParams
    .filter(param => parameters[param.key] !== undefined)
    .map(param => ({
      ...param,
      value: String(parameters[param.key])
    }))
}