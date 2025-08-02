'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Plus, 
  FolderOpen, 
  Trash2, 
  RefreshCw, 
  Package,
  Image as ImageIcon,
  AlertCircle,
  FileText,
  Calendar,
  HardDrive,
  Eye
} from 'lucide-react'
import { cn } from '@/lib/utils'
import Image from 'next/image'

interface ModelPath {
  id: string
  path: string
  added_at: string
  model_count: number
  last_scan: string
}

interface Model {
  id: string
  name: string
  path: string
  type: string
  size: number
  created_at: string
  modified_at: string
  has_preview: boolean
  preview_images?: string[]
  metadata?: {
    base_model?: string
    training_steps?: number
    dataset?: string
  }
}

export default function ModelsPage() {
  const [paths, setPaths] = useState<ModelPath[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [selectedModel, setSelectedModel] = useState<Model | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newPath, setNewPath] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPaths()
    fetchModels()
  }, [])

  const fetchPaths = async () => {
    try {
      const response = await fetch('/api/backend/models/paths')
      if (!response.ok) throw new Error('Failed to fetch paths')
      const data = await response.json()
      setPaths(data.paths)
      setError(null)
    } catch (err) {
      console.error('Error fetching paths:', err)
      setPaths([])
    }
  }

  const fetchModels = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/backend/models')
      if (!response.ok) throw new Error('Failed to fetch models')
      const data = await response.json()
      setModels(data.models)
      setError(null)
    } catch (err) {
      console.error('Error fetching models:', err)
      setModels([])
    } finally {
      setLoading(false)
    }
  }

  const addPath = async () => {
    if (!newPath.trim()) return

    try {
      const response = await fetch('/api/backend/models/paths', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: newPath })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || 'Failed to add path')
      }

      setNewPath('')
      setDialogOpen(false)
      await fetchPaths()
      await scanPath(newPath)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add path')
    }
  }

  const removePath = async (pathId: string) => {
    if (!confirm('Are you sure you want to remove this path?')) return

    try {
      const response = await fetch(`/api/backend/models/paths/${pathId}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('Failed to remove path')

      await fetchPaths()
      await fetchModels()
    } catch (err) {
      alert('Failed to remove path')
    }
  }

  const scanPath = async (path: string) => {
    try {
      setScanning(true)
      const response = await fetch('/api/backend/models/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      })

      if (!response.ok) throw new Error('Failed to scan path')

      await fetchModels()
    } catch (err) {
      console.error('Error scanning path:', err)
    } finally {
      setScanning(false)
    }
  }

  const rescanAll = async () => {
    setScanning(true)
    for (const path of paths) {
      await scanPath(path.path)
    }
    setScanning(false)
  }

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 B'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="container py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Trained Models</h1>
          <p className="text-muted-foreground">
            Manage and browse your trained models
          </p>
        </div>
        <div className="flex gap-2">
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Path
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Model Path</DialogTitle>
                <DialogDescription>
                  Add a directory path to scan for trained models
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label htmlFor="path">Directory Path</Label>
                  <Input
                    id="path"
                    value={newPath}
                    onChange={(e) => setNewPath(e.target.value)}
                    placeholder="/path/to/models"
                    onKeyPress={(e) => e.key === 'Enter' && addPath()}
                  />
                </div>
                <Button onClick={addPath} className="w-full">
                  <FolderOpen className="mr-2 h-4 w-4" />
                  Add Path
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          <Button 
            variant="outline" 
            onClick={rescanAll}
            disabled={scanning || paths.length === 0}
          >
            <RefreshCw className={cn("mr-2 h-4 w-4", scanning && "animate-spin")} />
            Rescan All
          </Button>
        </div>
      </div>

      {/* Model Paths */}
      {paths.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Model Paths</CardTitle>
            <CardDescription>
              Directories being monitored for models
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {paths.map((path) => (
                <div key={path.id} className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <FolderOpen className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-mono text-sm">{path.path}</p>
                      <p className="text-xs text-muted-foreground">
                        {path.model_count} models • Last scan: {new Date(path.last_scan).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removePath(path.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Models Grid */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-32 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              CLI Bridge Mode
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">{error}</p>
            <div className="space-y-2 text-sm">
              <p>To manage models, use the AutoTrainX CLI:</p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                <li>View models in the output directories</li>
                <li>Copy models to your preferred location</li>
                <li>Use ComfyUI or other tools to test models</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      ) : models.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Package className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Models Found</h3>
            <p className="text-muted-foreground text-center mb-4">
              Add a path above to start scanning for models
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {models.map((model) => (
            <Card 
              key={model.id} 
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setSelectedModel(model)}
            >
              <CardHeader>
                <div className="space-y-2">
                  <CardTitle className="text-lg truncate">{model.name}</CardTitle>
                  <CardDescription className="text-xs break-all">
                    {model.path}
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {model.has_preview && model.preview_images && model.preview_images[0] && (
                    <div className="aspect-video relative bg-muted rounded-md overflow-hidden mb-3">
                      <img
                        src={`/api/backend/models/${model.id}/preview/${model.preview_images[0]}`}
                        alt={`${model.name} preview`}
                        className="object-cover w-full h-full"
                      />
                    </div>
                  )}
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <HardDrive className="h-4 w-4" />
                      {formatFileSize(model.size)}
                    </div>
                    {model.has_preview && (
                      <Badge variant="secondary" className="text-xs">
                        <ImageIcon className="h-3 w-3 mr-1" />
                        {model.preview_images?.length || 0} images
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    {new Date(model.modified_at).toLocaleDateString()}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Model Details Dialog */}
      {selectedModel && (
        <Dialog open={!!selectedModel} onOpenChange={() => setSelectedModel(null)}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{selectedModel.name}</DialogTitle>
              <DialogDescription>{selectedModel.path}</DialogDescription>
            </DialogHeader>
            
            <Tabs defaultValue="info" className="mt-4">
              <TabsList>
                <TabsTrigger value="info">Information</TabsTrigger>
                {selectedModel.has_preview && <TabsTrigger value="preview">Preview Images</TabsTrigger>}
              </TabsList>
              
              <TabsContent value="info" className="mt-4">
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <Label>Type</Label>
                      <p className="text-sm">{selectedModel.type}</p>
                    </div>
                    <div>
                      <Label>Size</Label>
                      <p className="text-sm">{formatFileSize(selectedModel.size)}</p>
                    </div>
                    <div>
                      <Label>Created</Label>
                      <p className="text-sm">{new Date(selectedModel.created_at).toLocaleString()}</p>
                    </div>
                    <div>
                      <Label>Modified</Label>
                      <p className="text-sm">{new Date(selectedModel.modified_at).toLocaleString()}</p>
                    </div>
                  </div>
                  
                  {selectedModel.metadata && (
                    <div>
                      <Label>Metadata</Label>
                      <div className="mt-2 space-y-2">
                        {selectedModel.metadata.base_model && (
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Base Model:</span>
                            <span>{selectedModel.metadata.base_model}</span>
                          </div>
                        )}
                        {selectedModel.metadata.training_steps && (
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Training Steps:</span>
                            <span>{selectedModel.metadata.training_steps}</span>
                          </div>
                        )}
                        {selectedModel.metadata.dataset && (
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Dataset:</span>
                            <span>{selectedModel.metadata.dataset}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </TabsContent>
              
              {selectedModel.has_preview && (
                <TabsContent value="preview" className="mt-4">
                  <ScrollArea className="h-[500px]">
                    <div className="grid gap-4 md:grid-cols-2">
                      {selectedModel.preview_images?.map((image, idx) => (
                        <div key={idx} className="relative aspect-square bg-muted rounded-lg overflow-hidden">
                          <img
                            src={`/api/backend/models/${selectedModel.id}/preview/${image}`}
                            alt={`Preview ${idx + 1}`}
                            className="object-contain w-full h-full"
                          />
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </TabsContent>
              )}
            </Tabs>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}