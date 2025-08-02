'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useDropzone } from 'react-dropzone'
import { useMutation } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  ArrowLeft, 
  Upload, 
  File, 
  FileText,
  X, 
  CheckCircle2,
  AlertCircle,
  FolderOpen,
  Image as ImageIcon,
  Loader2
} from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import axios from 'axios'

interface FileWithPreview extends File {
  preview?: string
}

export default function UploadDatasetPage() {
  const router = useRouter()
  const api = getApiClient()
  const [files, setFiles] = useState<FileWithPreview[]>([])
  const [datasetName, setDatasetName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [prepareAfterUpload, setPrepareAfterUpload] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => 
      Object.assign(file, {
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
      })
    )
    setFiles(prev => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
      'text/plain': ['.txt']
    }
  })

  const removeFile = (index: number) => {
    setFiles(prev => {
      const newFiles = [...prev]
      const removed = newFiles.splice(index, 1)
      // Revoke object URL to avoid memory leaks
      if (removed[0].preview) {
        URL.revokeObjectURL(removed[0].preview)
      }
      return newFiles
    })
  }

  const uploadDatasetMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await axios.post('/api/backend/upload/dataset', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1))
          setUploadProgress(percentCompleted * 0.8) // 80% for upload
        }
      })
      return response.data
    },
    onSuccess: async (data) => {
      setUploadProgress(80)
      
      if (prepareAfterUpload) {
        try {
          // Prepare the dataset after upload
          await api.datasets.prepare(
            `workspace/input/${datasetName}`,
            datasetName,
            30,
            'person'
          )
          setUploadProgress(100)
          toast.success('Dataset uploaded and prepared successfully!')
          router.push('/dashboard/datasets')
        } catch (error: any) {
          toast.error('Upload succeeded but preparation failed. You can prepare it later.')
          console.error('Preparation error:', error)
          router.push('/dashboard/datasets')
        }
      } else {
        setUploadProgress(100)
        toast.success('Dataset uploaded successfully! You can now use it for training.')
        router.push('/dashboard/datasets')
      }
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || error.message || 'Failed to upload dataset'
      toast.error(message)
      setUploadProgress(0)
    }
  })

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error('Please select at least one file')
      return
    }

    if (!datasetName.trim()) {
      toast.error('Please enter a dataset name')
      return
    }

    // Validate files
    const imageFiles = files.filter(f => f.type.startsWith('image/'))
    const textFiles = files.filter(f => f.name.endsWith('.txt'))
    
    if (imageFiles.length === 0) {
      toast.error('Please include at least one image file')
      return
    }

    setUploading(true)
    const formData = new FormData()
    formData.append('dataset_name', datasetName.trim())
    
    files.forEach((file) => {
      formData.append('files', file)
    })

    try {
      await uploadDatasetMutation.mutateAsync(formData)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="container max-w-4xl py-6">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/datasets">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Upload Dataset</h1>
          <p className="text-muted-foreground">
            Upload images and captions for training
          </p>
        </div>
      </div>

      <div className="space-y-6">
        {/* Dataset Name */}
        <Card>
          <CardHeader>
            <CardTitle>Dataset Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="dataset-name">Dataset Name</Label>
              <Input
                id="dataset-name"
                placeholder="e.g., my-character-dataset"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                disabled={uploading}
              />
              <p className="text-sm text-muted-foreground">
                Choose a unique name for your dataset (no spaces or special characters)
              </p>
            </div>

            <div className="mt-4 flex items-center space-x-2">
              <input
                type="checkbox"
                id="prepare-after-upload"
                checked={prepareAfterUpload}
                onChange={(e) => setPrepareAfterUpload(e.target.checked)}
                disabled={uploading}
                className="h-4 w-4 rounded border-gray-300"
              />
              <Label 
                htmlFor="prepare-after-upload" 
                className="text-sm font-normal cursor-pointer"
              >
                Automatically prepare dataset after upload (Warning: This will start a training job)
              </Label>
            </div>
          </CardContent>
        </Card>

        {/* File Upload */}
        <Card>
          <CardHeader>
            <CardTitle>Upload Files</CardTitle>
            <CardDescription>
              Drag and drop your images and caption files, or click to browse
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...getRootProps()}
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
                isDragActive && "border-primary bg-primary/5",
                uploading && "cursor-not-allowed opacity-50"
              )}
            >
              <input {...getInputProps()} disabled={uploading} />
              <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              {isDragActive ? (
                <p className="text-lg">Drop the files here...</p>
              ) : (
                <>
                  <p className="text-lg mb-2">Drag & drop files here, or click to select</p>
                  <p className="text-sm text-muted-foreground">
                    Supports: JPG, PNG, WebP images and TXT caption files
                  </p>
                </>
              )}
            </div>

            {/* File List */}
            {files.length > 0 && (
              <div className="mt-6">
                <h4 className="text-sm font-medium mb-3">
                  Selected Files ({files.length})
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {files.map((file, index) => (
                    <div
                      key={`${file.name}-${index}`}
                      className="relative group border rounded-lg p-2"
                    >
                      <div className="aspect-square flex items-center justify-center bg-muted rounded mb-2">
                        {file.preview ? (
                          <img
                            src={file.preview}
                            alt={file.name}
                            className="h-full w-full object-cover rounded"
                          />
                        ) : file.name.endsWith('.txt') ? (
                          <FileText className="h-10 w-10 text-muted-foreground" />
                        ) : (
                          <File className="h-10 w-10 text-muted-foreground" />
                        )}
                      </div>
                      <p className="text-xs truncate" title={file.name}>
                        {file.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {(file.size / 1024).toFixed(1)} KB
                      </p>
                      <button
                        onClick={() => removeFile(index)}
                        className="absolute top-1 right-1 bg-background rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                        disabled={uploading}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Upload Progress */}
        {uploading && (
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Uploading files...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="h-2" />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Info Alert */}
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <p className="font-medium mb-1">File naming convention:</p>
            <p className="text-sm">Each image should have a corresponding .txt file with the same name containing the caption.</p>
            <p className="text-sm mt-1">Example: image001.jpg → image001.txt</p>
          </AlertDescription>
        </Alert>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => router.push('/dashboard/datasets')}
            disabled={uploading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            disabled={uploading || files.length === 0 || !datasetName.trim()}
          >
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload Dataset
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}