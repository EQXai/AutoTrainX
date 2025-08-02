'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  ArrowLeft, 
  FolderOpen,
  Loader2,
  AlertCircle,
  InfoIcon
} from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

export default function PrepareDatasetPage() {
  const router = useRouter()
  const api = getApiClient()
  const [sourcePath, setSourcePath] = useState('')
  const [datasetName, setDatasetName] = useState('')
  const [repeats, setRepeats] = useState(30)
  const [className, setClassName] = useState('person')

  const prepareDatasetMutation = useMutation({
    mutationFn: async (data: {
      sourcePath: string
      datasetName: string
      repeats: number
      className: string
    }) => {
      // Use the full path to the workspace/input directory
      const fullPath = `workspace/input/${data.sourcePath}`
      return api.datasets.prepare(fullPath, data.datasetName, data.repeats, data.className)
    },
    onSuccess: () => {
      toast.success('Dataset prepared successfully!')
      router.push('/dashboard/datasets')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to prepare dataset')
    }
  })

  const handlePrepare = () => {
    if (!sourcePath.trim()) {
      toast.error('Please enter a source folder name')
      return
    }

    prepareDatasetMutation.mutate({
      sourcePath: sourcePath.trim(),
      datasetName: datasetName.trim() || sourcePath.trim(),
      repeats,
      className
    })
  }

  return (
    <div className="container max-w-2xl py-6">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/datasets">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Prepare Dataset</h1>
          <p className="text-muted-foreground">
            Prepare an existing dataset for training
          </p>
        </div>
      </div>

      <div className="space-y-6">
        {/* Instructions */}
        <Alert>
          <InfoIcon className="h-4 w-4" />
          <AlertDescription>
            <p className="font-medium mb-2">How to prepare a dataset:</p>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              <li>Place your images and caption files in <code className="bg-muted px-1 rounded">workspace/input/[folder-name]</code></li>
              <li>Each image should have a corresponding .txt file with the same name</li>
              <li>Enter the folder name below (without the full path)</li>
              <li>Click "Prepare Dataset" to process the files</li>
            </ol>
          </AlertDescription>
        </Alert>

        {/* Dataset Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Dataset Configuration</CardTitle>
            <CardDescription>
              Configure how your dataset will be prepared for training
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="source-path">Source Folder Name</Label>
              <div className="flex items-center gap-2">
                <FolderOpen className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">workspace/input/</span>
                <Input
                  id="source-path"
                  placeholder="my-dataset"
                  value={sourcePath}
                  onChange={(e) => setSourcePath(e.target.value)}
                  disabled={prepareDatasetMutation.isPending}
                  className="flex-1"
                />
              </div>
              <p className="text-sm text-muted-foreground">
                The folder name inside workspace/input/ containing your images and captions
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="dataset-name">Dataset Name (Optional)</Label>
              <Input
                id="dataset-name"
                placeholder="Leave empty to use source folder name"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                disabled={prepareDatasetMutation.isPending}
              />
              <p className="text-sm text-muted-foreground">
                The name for the prepared dataset (defaults to source folder name)
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="repeats">Repeats</Label>
                <Input
                  id="repeats"
                  type="number"
                  min="1"
                  max="100"
                  value={repeats}
                  onChange={(e) => setRepeats(parseInt(e.target.value) || 30)}
                  disabled={prepareDatasetMutation.isPending}
                />
                <p className="text-sm text-muted-foreground">
                  Number of times to repeat each sample
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="class-name">Class Name</Label>
                <Input
                  id="class-name"
                  placeholder="person"
                  value={className}
                  onChange={(e) => setClassName(e.target.value)}
                  disabled={prepareDatasetMutation.isPending}
                />
                <p className="text-sm text-muted-foreground">
                  Class name for the training
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Error Display */}
        {prepareDatasetMutation.isError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {prepareDatasetMutation.error?.response?.data?.message || 
               'Failed to prepare dataset. Please check that the folder exists.'}
            </AlertDescription>
          </Alert>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => router.push('/dashboard/datasets')}
            disabled={prepareDatasetMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handlePrepare}
            disabled={prepareDatasetMutation.isPending || !sourcePath.trim()}
          >
            {prepareDatasetMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Preparing...
              </>
            ) : (
              'Prepare Dataset'
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}