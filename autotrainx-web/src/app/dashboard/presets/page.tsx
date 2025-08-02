'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  Settings,
  Plus,
  Edit,
  Trash2,
  Copy,
  FileText,
  Zap,
  Cpu,
  Database,
  Filter,
  Search,
  Download,
  Upload,
  Eye,
  Code2,
  Layers,
  Sparkles
} from 'lucide-react'
import { toast } from 'sonner'
import Link from 'next/link'

const api = getApiClient()

interface Preset {
  name: string
  description: string
  category: string
  architecture: string | null
  config_files: string[]
}

interface PresetDetails {
  name: string
  description: string
  parameters: Record<string, any>
  config_content?: string
}

export default function PresetsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [selectedArchitecture, setSelectedArchitecture] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPreset, setSelectedPreset] = useState<Preset | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showDetailsDialog, setShowDetailsDialog] = useState(false)
  const queryClient = useQueryClient()

  // Fetch presets
  const { data: presetsData, isLoading: presetsLoading } = useQuery({
    queryKey: ['presets', selectedCategory, selectedArchitecture],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (selectedCategory !== 'all') params.append('category', selectedCategory)
      if (selectedArchitecture !== 'all') params.append('architecture', selectedArchitecture)
      
      const response = await api.presets.list()
      return response
    },
    refetchInterval: 30000,
  })

  // Fetch preset categories
  const { data: categoriesData } = useQuery({
    queryKey: ['preset-categories'],
    queryFn: async () => {
      const response = await fetch('/api/backend/presets/categories')
      if (!response.ok) throw new Error('Failed to fetch categories')
      return response.json()
    },
  })

  // Fetch preset details
  const { data: presetDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ['preset-details', selectedPreset?.name],
    queryFn: async () => {
      if (!selectedPreset) return null
      const response = await api.presets.get(selectedPreset.name)
      return response
    },
    enabled: !!selectedPreset && showDetailsDialog,
  })

  // Filter presets based on search
  const presetsList = presetsData?.presets || []
  const filteredPresets = presetsList.filter((preset: Preset) =>
    preset.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    preset.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getArchitectureIcon = (architecture: string | null) => {
    switch (architecture) {
      case 'flux': return <Zap className="h-4 w-4" />
      case 'sdxl': return <Layers className="h-4 w-4" />
      default: return <Settings className="h-4 w-4" />
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

  const openPresetDetails = (preset: Preset) => {
    setSelectedPreset(preset)
    setShowDetailsDialog(true)
  }

  return (
    <div className="container py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Settings className="h-8 w-8" />
            Training Presets
          </h1>
          <p className="text-muted-foreground">
            Manage and configure training presets for different model architectures
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Preset
          </Button>
        </div>
      </div>

      {/* Stats and Filters */}
      <div className="grid gap-4 md:grid-cols-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Presets</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{presetsData?.length || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Base Presets</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {presetsList.filter((p: Preset) => p.category === 'base').length || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Custom Presets</CardTitle>
            <Sparkles className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {presetsList.filter((p: Preset) => p.category === 'custom').length || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Architectures</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Set(presetsList.map((p: Preset) => p.architecture).filter(Boolean)).size || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters & Search
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <Label htmlFor="search">Search Presets</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search by name or description..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
            
            <div className="md:w-48">
              <Label htmlFor="category">Category</Label>
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger>
                  <SelectValue placeholder="All categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  <SelectItem value="base">Base Presets</SelectItem>
                  <SelectItem value="custom">Custom Presets</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="md:w-48">
              <Label htmlFor="architecture">Architecture</Label>
              <Select value={selectedArchitecture} onValueChange={setSelectedArchitecture}>
                <SelectTrigger>
                  <SelectValue placeholder="All architectures" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Architectures</SelectItem>
                  <SelectItem value="flux">FLUX</SelectItem>
                  <SelectItem value="sdxl">SDXL</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Presets Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {presetsLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-full" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          filteredPresets.map((preset: Preset) => (
            <Card key={preset.name} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {getArchitectureIcon(preset.architecture)}
                      {preset.name}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {preset.description}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <Badge className={getCategoryColor(preset.category)}>
                      {preset.category}
                    </Badge>
                    {preset.architecture && (
                      <Badge className={getArchitectureColor(preset.architecture)}>
                        {preset.architecture.toUpperCase()}
                      </Badge>
                    )}
                  </div>

                  <div className="text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      {preset.config_files.length} config file(s)
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openPresetDetails(preset)}
                      className="flex-1"
                    >
                      <Eye className="mr-2 h-3 w-3" />
                      View
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        // Copy preset functionality
                        toast.success('Preset copied to clipboard')
                      }}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                    {preset.category === 'custom' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          // Edit preset functionality
                          toast.info('Edit functionality coming soon')
                        }}
                      >
                        <Edit className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {filteredPresets.length === 0 && !presetsLoading && (
        <Card>
          <CardContent className="text-center py-8">
            <Settings className="mx-auto h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold">No presets found</h3>
            <p className="text-muted-foreground">
              Try adjusting your filters or create a new preset.
            </p>
            <Button className="mt-4" onClick={() => setShowCreateDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Your First Preset
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Create Preset Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-[625px]">
          <DialogHeader>
            <DialogTitle>Create New Preset</DialogTitle>
            <DialogDescription>
              Create a custom training preset with your own parameters.
            </DialogDescription>
          </DialogHeader>
          <CreatePresetForm onClose={() => setShowCreateDialog(false)} />
        </DialogContent>
      </Dialog>

      {/* Preset Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="sm:max-w-[800px] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedPreset && getArchitectureIcon(selectedPreset.architecture)}
              {selectedPreset?.name}
            </DialogTitle>
            <DialogDescription>
              {selectedPreset?.description}
            </DialogDescription>
          </DialogHeader>
          {detailsLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : (
            <PresetDetailsContent preset={selectedPreset} details={presetDetails} />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

function CreatePresetForm({ onClose }: { onClose: () => void }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    architecture: '',
    basePreset: '',
    parameters: ''
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement preset creation
    toast.success('Preset creation functionality coming soon!')
    onClose()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="name">Preset Name</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="my-custom-preset"
            required
          />
        </div>
        <div>
          <Label htmlFor="architecture">Architecture</Label>
          <Select
            value={formData.architecture}
            onValueChange={(value) => setFormData({ ...formData, architecture: value })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select architecture" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="flux">FLUX</SelectItem>
              <SelectItem value="sdxl">SDXL</SelectItem>
              <SelectItem value="custom">Custom</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <Label htmlFor="description">Description</Label>
        <Input
          id="description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Description of your preset..."
        />
      </div>

      <div>
        <Label htmlFor="basePreset">Base Preset (Optional)</Label>
        <Select
          value={formData.basePreset}
          onValueChange={(value) => setFormData({ ...formData, basePreset: value })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Start from existing preset" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="FluxLORA">FluxLORA</SelectItem>
            <SelectItem value="FluxCheckpoint">FluxCheckpoint</SelectItem>
            <SelectItem value="SDXLCheckpoint">SDXLCheckpoint</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="parameters">Custom Parameters (JSON)</Label>
        <Textarea
          id="parameters"
          value={formData.parameters}
          onChange={(e) => setFormData({ ...formData, parameters: e.target.value })}
          placeholder='{"learning_rate": 0.0001, "batch_size": 4}'
          rows={6}
        />
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit">
          <Plus className="mr-2 h-4 w-4" />
          Create Preset
        </Button>
      </DialogFooter>
    </form>
  )
}

function PresetDetailsContent({ 
  preset, 
  details 
}: { 
  preset: Preset | null
  details: any 
}) {
  if (!preset || !details) return null

  return (
    <Tabs defaultValue="overview" className="w-full">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="parameters">Parameters</TabsTrigger>
        <TabsTrigger value="config">Configuration</TabsTrigger>
      </TabsList>

      <TabsContent value="overview" className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Category</Label>
            <Badge className={`mt-1 ${preset.category === 'base' ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'}`}>
              {preset.category}
            </Badge>
          </div>
          <div>
            <Label>Architecture</Label>
            {preset.architecture && (
              <Badge className={`mt-1 ${preset.architecture === 'flux' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'}`}>
                {preset.architecture.toUpperCase()}
              </Badge>
            )}
          </div>
        </div>

        <div>
          <Label>Configuration Files</Label>
          <div className="mt-2 space-y-2">
            {preset.config_files.map((file) => (
              <div key={file} className="flex items-center gap-2 p-2 bg-muted rounded">
                <FileText className="h-4 w-4" />
                <span className="font-mono text-sm">{file}</span>
              </div>
            ))}
          </div>
        </div>
      </TabsContent>

      <TabsContent value="parameters" className="space-y-4">
        <div className="bg-muted p-4 rounded-lg">
          <pre className="text-sm overflow-x-auto">
            {JSON.stringify(details.parameters || {}, null, 2)}
          </pre>
        </div>
      </TabsContent>

      <TabsContent value="config" className="space-y-4">
        <div className="bg-muted p-4 rounded-lg">
          <code className="text-sm whitespace-pre-wrap">
            {details.config_content || 'Configuration content not available'}
          </code>
        </div>
      </TabsContent>
    </Tabs>
  )
}