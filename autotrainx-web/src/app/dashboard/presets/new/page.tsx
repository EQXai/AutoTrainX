'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation, useQuery } from '@tanstack/react-query'
import { getApiClient } from '@/lib/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { 
  ArrowLeft,
  Plus,
  Save,
  Settings,
  Zap,
  Layers,
  Code2,
  FileText,
  AlertCircle,
  CheckCircle2,
  Info
} from 'lucide-react'
import { toast } from 'sonner'
import Link from 'next/link'

const api = getApiClient()

interface PresetForm {
  name: string
  description: string
  architecture: string
  basePreset: string
  category: 'custom'
  parameters: {
    // Training parameters
    learning_rate: number
    batch_size: number
    num_epochs: number
    resolution: number
    
    // Model specific
    rank: number
    alpha: number
    
    // Advanced
    gradient_accumulation_steps: number
    mixed_precision: string
    optimizer: string
    lr_scheduler: string
    warmup_steps: number
    
    // Custom parameters (JSON string)
    custom_json: string
  }
}

const defaultForm: PresetForm = {
  name: '',
  description: '',
  architecture: 'flux',
  basePreset: '',
  category: 'custom',
  parameters: {
    learning_rate: 0.0001,
    batch_size: 4,
    num_epochs: 100,
    resolution: 1024,
    rank: 32,
    alpha: 16,
    gradient_accumulation_steps: 1,
    mixed_precision: 'fp16',
    optimizer: 'adamw',
    lr_scheduler: 'cosine',
    warmup_steps: 100,
    custom_json: ''
  }
}

export default function NewPresetPage() {
  const router = useRouter()
  const [form, setForm] = useState<PresetForm>(defaultForm)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  // Fetch existing presets for base preset selection
  const { data: existingPresets } = useQuery({
    queryKey: ['presets-for-base'],
    queryFn: () => api.presets.list({ category: 'base' }),
  })

  // Create preset mutation
  const createPresetMutation = useMutation({
    mutationFn: async (data: PresetForm) => {
      // Validate custom JSON if provided
      let customParams = {}
      if (data.parameters.custom_json) {
        try {
          customParams = JSON.parse(data.parameters.custom_json)
        } catch (e) {
          throw new Error('Invalid JSON in custom parameters')
        }
      }

      // Combine all parameters
      const allParameters = {
        ...data.parameters,
        ...customParams
      }
      delete allParameters.custom_json

      return api.presets.create({
        name: data.name,
        description: data.description,
        architecture: data.architecture,
        parameters: allParameters,
        base_preset: data.basePreset || undefined
      })
    },
    onSuccess: () => {
      toast.success('Preset created successfully!')
      router.push('/dashboard/presets')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create preset')
    }
  })

  const updateFormField = (field: string, value: any) => {
    setForm(prev => ({ ...prev, [field]: value }))
    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  const updateParameterField = (field: string, value: any) => {
    setForm(prev => ({
      ...prev,
      parameters: { ...prev.parameters, [field]: value }
    }))
  }

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    if (!form.name.trim()) {
      errors.name = 'Preset name is required'
    } else if (!/^[a-zA-Z0-9_-]+$/.test(form.name)) {
      errors.name = 'Name can only contain letters, numbers, underscores, and hyphens'
    }

    if (!form.description.trim()) {
      errors.description = 'Description is required'
    }

    if (!form.architecture) {
      errors.architecture = 'Architecture is required'
    }

    if (form.parameters.custom_json) {
      try {
        JSON.parse(form.parameters.custom_json)
      } catch (e) {
        errors.custom_json = 'Invalid JSON format'
      }
    }

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      createPresetMutation.mutate(form)
    }
  }

  const getArchitectureIcon = (arch: string) => {
    switch (arch) {
      case 'flux': return <Zap className="h-4 w-4" />
      case 'sdxl': return <Layers className="h-4 w-4" />
      default: return <Settings className="h-4 w-4" />
    }
  }

  return (
    <div className="container py-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link href="/dashboard/presets">
          <Button variant="outline" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Plus className="h-8 w-8" />
            Create New Preset
          </h1>
          <p className="text-muted-foreground">
            Configure a custom training preset with your own parameters
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Basic Information
                </CardTitle>
                <CardDescription>
                  Define the basic properties of your preset
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="name">Preset Name *</Label>
                    <Input
                      id="name"
                      value={form.name}
                      onChange={(e) => updateFormField('name', e.target.value)}
                      placeholder="my-custom-preset"
                      className={validationErrors.name ? 'border-red-500' : ''}
                    />
                    {validationErrors.name && (
                      <p className="text-sm text-red-600 mt-1">{validationErrors.name}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="architecture">Architecture *</Label>
                    <Select
                      value={form.architecture}
                      onValueChange={(value) => updateFormField('architecture', value)}
                    >
                      <SelectTrigger className={validationErrors.architecture ? 'border-red-500' : ''}>
                        <SelectValue placeholder="Select architecture" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="flux">
                          <div className="flex items-center gap-2">
                            <Zap className="h-4 w-4" />
                            FLUX
                          </div>
                        </SelectItem>
                        <SelectItem value="sdxl">
                          <div className="flex items-center gap-2">
                            <Layers className="h-4 w-4" />
                            SDXL
                          </div>
                        </SelectItem>
                        <SelectItem value="custom">
                          <div className="flex items-center gap-2">
                            <Settings className="h-4 w-4" />
                            Custom
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    {validationErrors.architecture && (
                      <p className="text-sm text-red-600 mt-1">{validationErrors.architecture}</p>
                    )}
                  </div>
                </div>

                <div>
                  <Label htmlFor="description">Description *</Label>
                  <Textarea
                    id="description"
                    value={form.description}
                    onChange={(e) => updateFormField('description', e.target.value)}
                    placeholder="Describe your preset and its purpose..."
                    rows={3}
                    className={validationErrors.description ? 'border-red-500' : ''}
                  />
                  {validationErrors.description && (
                    <p className="text-sm text-red-600 mt-1">{validationErrors.description}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="basePreset">Base Preset (Optional)</Label>
                  <Select
                    value={form.basePreset}
                    onValueChange={(value) => updateFormField('basePreset', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Start from existing preset (optional)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">None (create from scratch)</SelectItem>
                      {existingPresets?.map((preset: any) => (
                        <SelectItem key={preset.name} value={preset.name}>
                          {preset.name} - {preset.description}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-muted-foreground mt-1">
                    Optional: Use an existing preset as starting point
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Parameters */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Training Parameters
                </CardTitle>
                <CardDescription>
                  Configure the training parameters for your preset
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="basic" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="basic">Basic</TabsTrigger>
                    <TabsTrigger value="model">Model</TabsTrigger>
                    <TabsTrigger value="advanced">Advanced</TabsTrigger>
                  </TabsList>

                  {/* Basic Parameters */}
                  <TabsContent value="basic" className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="learning_rate">Learning Rate</Label>
                        <Input
                          id="learning_rate"
                          type="number"
                          step="0.000001"
                          value={form.parameters.learning_rate}
                          onChange={(e) => updateParameterField('learning_rate', parseFloat(e.target.value))}
                        />
                      </div>

                      <div>
                        <Label htmlFor="batch_size">Batch Size</Label>
                        <Select
                          value={form.parameters.batch_size.toString()}
                          onValueChange={(value) => updateParameterField('batch_size', parseInt(value))}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {[1, 2, 4, 8, 16, 32].map(size => (
                              <SelectItem key={size} value={size.toString()}>{size}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <Label htmlFor="num_epochs">Number of Epochs</Label>
                        <Input
                          id="num_epochs"
                          type="number"
                          min="1"
                          value={form.parameters.num_epochs}
                          onChange={(e) => updateParameterField('num_epochs', parseInt(e.target.value))}
                        />
                      </div>

                      <div>
                        <Label htmlFor="resolution">Resolution</Label>
                        <Select
                          value={form.parameters.resolution.toString()}
                          onValueChange={(value) => updateParameterField('resolution', parseInt(value))}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {[512, 768, 1024, 1536, 2048].map(res => (
                              <SelectItem key={res} value={res.toString()}>{res}x{res}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </TabsContent>

                  {/* Model Parameters */}
                  <TabsContent value="model" className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="rank">LoRA Rank</Label>
                        <div className="space-y-2">
                          <Slider
                            value={[form.parameters.rank]}
                            onValueChange={(value) => updateParameterField('rank', value[0])}
                            max={128}
                            min={1}
                            step={1}
                          />
                          <div className="text-center text-sm text-muted-foreground">
                            {form.parameters.rank}
                          </div>
                        </div>
                      </div>

                      <div>
                        <Label htmlFor="alpha">LoRA Alpha</Label>
                        <div className="space-y-2">
                          <Slider
                            value={[form.parameters.alpha]}
                            onValueChange={(value) => updateParameterField('alpha', value[0])}
                            max={64}
                            min={1}
                            step={1}
                          />
                          <div className="text-center text-sm text-muted-foreground">
                            {form.parameters.alpha}
                          </div>
                        </div>
                      </div>
                    </div>
                  </TabsContent>

                  {/* Advanced Parameters */}
                  <TabsContent value="advanced" className="space-y-4 mt-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="optimizer">Optimizer</Label>
                        <Select
                          value={form.parameters.optimizer}
                          onValueChange={(value) => updateParameterField('optimizer', value)}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="adamw">AdamW</SelectItem>
                            <SelectItem value="adam">Adam</SelectItem>
                            <SelectItem value="sgd">SGD</SelectItem>
                            <SelectItem value="lion">Lion</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <Label htmlFor="lr_scheduler">LR Scheduler</Label>
                        <Select
                          value={form.parameters.lr_scheduler}
                          onValueChange={(value) => updateParameterField('lr_scheduler', value)}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="cosine">Cosine</SelectItem>
                            <SelectItem value="linear">Linear</SelectItem>
                            <SelectItem value="constant">Constant</SelectItem>
                            <SelectItem value="polynomial">Polynomial</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <Label htmlFor="mixed_precision">Mixed Precision</Label>
                        <Select
                          value={form.parameters.mixed_precision}
                          onValueChange={(value) => updateParameterField('mixed_precision', value)}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="fp16">FP16</SelectItem>
                            <SelectItem value="bf16">BF16</SelectItem>
                            <SelectItem value="fp32">FP32</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <Label htmlFor="warmup_steps">Warmup Steps</Label>
                        <Input
                          id="warmup_steps"
                          type="number"
                          min="0"
                          value={form.parameters.warmup_steps}
                          onChange={(e) => updateParameterField('warmup_steps', parseInt(e.target.value))}
                        />
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="custom_json">Custom Parameters (JSON)</Label>
                      <Textarea
                        id="custom_json"
                        value={form.parameters.custom_json}
                        onChange={(e) => updateParameterField('custom_json', e.target.value)}
                        placeholder='{"custom_param": "value", "another_param": 123}'
                        rows={4}
                        className={validationErrors.custom_json ? 'border-red-500' : ''}
                      />
                      {validationErrors.custom_json && (
                        <p className="text-sm text-red-600 mt-1">{validationErrors.custom_json}</p>
                      )}
                      <p className="text-sm text-muted-foreground mt-1">
                        Optional: Add custom parameters as JSON. These will override any conflicting parameters above.
                      </p>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Preview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code2 className="h-5 w-5" />
                  Preview
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    {getArchitectureIcon(form.architecture)}
                    <span className="font-medium">{form.name || 'Untitled Preset'}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {form.description || 'No description provided'}
                  </p>
                  <div className="flex gap-2">
                    <Badge variant="secondary">Custom</Badge>
                    {form.architecture && (
                      <Badge variant="outline">
                        {form.architecture.toUpperCase()}
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="pt-2 border-t">
                  <p className="text-sm font-medium mb-2">Key Parameters:</p>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span>Learning Rate:</span>
                      <code>{form.parameters.learning_rate}</code>
                    </div>
                    <div className="flex justify-between">
                      <span>Batch Size:</span>
                      <code>{form.parameters.batch_size}</code>
                    </div>
                    <div className="flex justify-between">
                      <span>Epochs:</span>
                      <code>{form.parameters.num_epochs}</code>
                    </div>
                    <div className="flex justify-between">
                      <span>Resolution:</span>
                      <code>{form.parameters.resolution}</code>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <Button 
                    type="submit" 
                    className="w-full"
                    disabled={createPresetMutation.isPending}
                  >
                    {createPresetMutation.isPending ? (
                      <>Creating...</>
                    ) : (
                      <>
                        <Save className="mr-2 h-4 w-4" />
                        Create Preset
                      </>
                    )}
                  </Button>
                  
                  <Link href="/dashboard/presets">
                    <Button variant="outline" className="w-full">
                      Cancel
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Help */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Info className="h-5 w-5" />
                  Tips
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <p>• Use lowercase names with underscores or hyphens</p>
                <p>• Start with a base preset to save time</p>
                <p>• Lower learning rates are usually safer</p>
                <p>• Higher LoRA ranks = more parameters to train</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </form>
    </div>
  )
}