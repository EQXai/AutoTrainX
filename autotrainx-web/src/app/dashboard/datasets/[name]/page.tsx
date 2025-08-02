'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { ArrowLeft, Image as ImageIcon, FileText, AlertCircle, Loader2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

interface ImageDetails {
  filename: string
  path: string
  width: number
  height: number
  size: number
  has_caption: boolean
  caption?: string
}

interface DatasetDetails {
  name: string
  path: string
  total_images: number
  total_texts: number
  images_with_captions: number
  images_without_captions: number
  images: ImageDetails[]
  stats: {
    min_width: number
    max_width: number
    min_height: number
    max_height: number
    avg_width: number
    avg_height: number
    total_size_mb: number
  }
}

export default function DatasetDetailsPage() {
  const params = useParams()
  const datasetName = params.name as string
  const [dataset, setDataset] = useState<DatasetDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedImage, setSelectedImage] = useState<ImageDetails | null>(null)

  useEffect(() => {
    fetchDatasetDetails()
  }, [datasetName])

  const fetchDatasetDetails = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/backend/datasets/${datasetName}/details`)
      if (!response.ok) {
        throw new Error('Failed to fetch dataset details')
      }
      const data = await response.json()
      setDataset(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="container py-6">
        <div className="mb-6">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-96 mt-2" />
        </div>
        <div className="grid gap-4 md:grid-cols-4 mb-6">
          {[1, 2, 3, 4].map(i => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error || !dataset) {
    return (
      <div className="container py-6">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Error Loading Dataset
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error || 'Dataset not found'}</p>
            <Button asChild className="mt-4">
              <Link href="/dashboard/datasets">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Datasets
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/dashboard/datasets">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <h1 className="text-3xl font-bold">{dataset.name}</h1>
          </div>
          <p className="text-muted-foreground">
            {dataset.path}
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Images</CardTitle>
            <ImageIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dataset.total_images}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">With Captions</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dataset.images_with_captions}</div>
            <p className="text-xs text-muted-foreground">
              {dataset.images_without_captions > 0 && (
                <span className="text-destructive">
                  {dataset.images_without_captions} missing
                </span>
              )}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Resolution Range</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm">
              <div>{dataset.stats.min_width}x{dataset.stats.min_height}</div>
              <div className="text-muted-foreground">to</div>
              <div>{dataset.stats.max_width}x{dataset.stats.max_height}</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Size</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dataset.stats.total_size_mb.toFixed(1)} MB</div>
          </CardContent>
        </Card>
      </div>

      {/* Image Gallery */}
      <Card>
        <CardHeader>
          <CardTitle>Image Gallery</CardTitle>
          <CardDescription>
            Click on any image to view details and caption
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {dataset.images.map((image) => (
              <div
                key={image.filename}
                className={cn(
                  "relative group cursor-pointer rounded-lg overflow-hidden border-2 transition-all",
                  selectedImage?.filename === image.filename
                    ? "border-primary"
                    : "border-transparent hover:border-muted-foreground/50"
                )}
                onClick={() => setSelectedImage(image)}
              >
                <div className="aspect-square relative bg-muted">
                  <img
                    src={`/api/backend/datasets/${datasetName}/images/${image.filename}`}
                    alt={image.filename}
                    className="object-cover w-full h-full"
                  />
                  {!image.has_caption && (
                    <Badge 
                      variant="destructive" 
                      className="absolute top-2 right-2"
                    >
                      No Caption
                    </Badge>
                  )}
                </div>
                <div className="p-2">
                  <p className="text-xs font-medium truncate">{image.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {image.width}x{image.height}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Selected Image Details */}
      {selectedImage && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Selected Image: {selectedImage.filename}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <img
                  src={`/api/datasets/${datasetName}/images/${selectedImage.filename}`}
                  alt={selectedImage.filename}
                  className="w-full rounded-lg"
                />
              </div>
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">Image Details</h4>
                  <dl className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">Resolution:</dt>
                      <dd>{selectedImage.width}x{selectedImage.height}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">File Size:</dt>
                      <dd>{(selectedImage.size / 1024 / 1024).toFixed(2)} MB</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">Has Caption:</dt>
                      <dd>
                        <Badge variant={selectedImage.has_caption ? "default" : "destructive"}>
                          {selectedImage.has_caption ? "Yes" : "No"}
                        </Badge>
                      </dd>
                    </div>
                  </dl>
                </div>
                
                {selectedImage.has_caption && (
                  <div>
                    <h4 className="font-semibold mb-2">Caption</h4>
                    <ScrollArea className="h-[200px] w-full rounded-md border p-4">
                      <p className="text-sm">{selectedImage.caption}</p>
                    </ScrollArea>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}