'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useDatasets } from '@/lib/hooks/use-datasets'
import { useDatasetPaths, useAddDatasetPath, useRemoveDatasetPath, useScannedDatasets } from '@/lib/hooks/use-dataset-paths'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { 
  Database, 
  FolderOpen, 
  Image, 
  FileText, 
  Plus,
  Trash2,
  RefreshCw,
  HardDrive,
  Upload,
  FolderSearch,
  AlertCircle,
  CheckCircle
} from 'lucide-react'
import { toast } from 'sonner'

export default function DatasetsPage() {
  const { data: datasetsData, isLoading: isLoadingWorkspace } = useDatasets()
  const { data: datasetPaths, isLoading: isLoadingPaths } = useDatasetPaths()
  const { data: scannedDatasets, isLoading: isLoadingScanned } = useScannedDatasets()
  const addPathMutation = useAddDatasetPath()
  const removePathMutation = useRemoveDatasetPath()
  
  const [showAddPathDialog, setShowAddPathDialog] = useState(false)
  const [newPath, setNewPath] = useState('')

  const handleAddPath = async () => {
    if (!newPath.trim()) {
      toast.error('Please enter a path')
      return
    }

    try {
      await addPathMutation.mutateAsync(newPath.trim())
      toast.success('Path added successfully')
      setShowAddPathDialog(false)
      setNewPath('')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add path')
    }
  }

  const handleRemovePath = async (id: number) => {
    if (confirm('Are you sure you want to remove this path?')) {
      try {
        await removePathMutation.mutateAsync(id)
        toast.success('Path removed successfully')
      } catch (error: any) {
        toast.error(error.response?.data?.detail || 'Failed to remove path')
      }
    }
  }

  return (
    <div className="container py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Datasets</h1>
          <p className="text-muted-foreground">
            Manage your training datasets
          </p>
        </div>
        <Button asChild>
          <Link href="/dashboard/datasets/upload">
            <Upload className="mr-2 h-4 w-4" />
            Upload Dataset
          </Link>
        </Button>
      </div>

      <Tabs defaultValue="workspace" className="space-y-4">
        <TabsList>
          <TabsTrigger value="workspace">
            <FolderOpen className="mr-2 h-4 w-4" />
            Workspace Datasets
          </TabsTrigger>
          <TabsTrigger value="external">
            <HardDrive className="mr-2 h-4 w-4" />
            External Datasets
          </TabsTrigger>
        </TabsList>

        <TabsContent value="workspace" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Workspace Datasets</CardTitle>
              <CardDescription>
                Datasets in your workspace/input directory
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingWorkspace ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Card key={i}>
                      <CardHeader>
                        <Skeleton className="h-4 w-32" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-20 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : datasetsData?.items.length === 0 ? (
                <div className="text-center py-8">
                  <Database className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No datasets found in workspace</p>
                  <Button asChild className="mt-4">
                    <Link href="/dashboard/datasets/upload">
                      <Upload className="mr-2 h-4 w-4" />
                      Upload your first dataset
                    </Link>
                  </Button>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {datasetsData?.items.map((dataset) => (
                    <Link key={dataset.path} href={`/dashboard/datasets/${dataset.name}`}>
                      <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <Database className="h-5 w-5 text-muted-foreground" />
                            <Badge variant="secondary">Workspace</Badge>
                          </div>
                          <CardTitle className="mt-2">{dataset.name}</CardTitle>
                          <CardDescription className="truncate" title={dataset.path}>
                            {dataset.path}
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div className="flex items-center gap-2">
                              <Image className="h-4 w-4 text-muted-foreground" />
                              <span>{dataset.image_count} images</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <FileText className="h-4 w-4 text-muted-foreground" />
                              <span>{dataset.caption_count} captions</span>
                            </div>
                          </div>
                          {dataset.prepared && (
                            <Badge className="mt-3" variant="default">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Prepared
                            </Badge>
                          )}
                        </CardContent>
                      </Card>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="external" className="space-y-4">
          {/* Dataset Paths Management */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Dataset Search Paths</CardTitle>
                  <CardDescription>
                    Add directories to scan for datasets
                  </CardDescription>
                </div>
                <Button
                  onClick={() => setShowAddPathDialog(true)}
                  size="sm"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Path
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {isLoadingPaths ? (
                <div className="space-y-2">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : datasetPaths?.length === 0 ? (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    No dataset paths configured. Add paths to scan for datasets in external directories.
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="space-y-2">
                  {datasetPaths?.map((path) => (
                    <div
                      key={path.id}
                      className="flex items-center justify-between p-3 rounded-lg border"
                    >
                      <div className="flex items-center gap-3">
                        <FolderSearch className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">{path.path}</p>
                          <p className="text-xs text-muted-foreground">
                            {path.dataset_count} datasets found
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemovePath(path.id)}
                        disabled={removePathMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Scanned Datasets */}
          <Card>
            <CardHeader>
              <CardTitle>Discovered Datasets</CardTitle>
              <CardDescription>
                Datasets found in your configured paths
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingScanned ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Card key={i}>
                      <CardHeader>
                        <Skeleton className="h-4 w-32" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-20 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : scannedDatasets?.length === 0 ? (
                <div className="text-center py-8">
                  <FolderSearch className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No datasets found in external paths</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Add paths above to scan for datasets
                  </p>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {scannedDatasets?.map((dataset, index) => (
                    <Card key={`${dataset.path}-${index}`} className="cursor-default">
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <Database className="h-5 w-5 text-muted-foreground" />
                          <Badge variant="outline">External</Badge>
                        </div>
                        <CardTitle className="mt-2">{dataset.name}</CardTitle>
                        <CardDescription className="text-xs truncate" title={dataset.path}>
                          {dataset.parent_path}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div className="flex items-center gap-2">
                            <Image className="h-4 w-4 text-muted-foreground" />
                            <span>{dataset.image_count} images</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                            <span>{dataset.caption_count} captions</span>
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground mt-3">
                          Use path in training: <code className="bg-muted px-1 rounded">{dataset.path}</code>
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add Path Dialog */}
      <Dialog open={showAddPathDialog} onOpenChange={setShowAddPathDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Dataset Search Path</DialogTitle>
            <DialogDescription>
              Add a directory path to scan for datasets. The system will recursively search for valid dataset structures.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="path">Directory Path</Label>
              <Input
                id="path"
                placeholder="/path/to/datasets"
                value={newPath}
                onChange={(e) => setNewPath(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !addPathMutation.isPending) {
                    handleAddPath()
                  }
                }}
              />
              <p className="text-sm text-muted-foreground">
                Enter the full path to a directory containing dataset folders
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowAddPathDialog(false)
                setNewPath('')
              }}
              disabled={addPathMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleAddPath}
              disabled={addPathMutation.isPending || !newPath.trim()}
            >
              {addPathMutation.isPending ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Adding...
                </>
              ) : (
                'Add Path'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}