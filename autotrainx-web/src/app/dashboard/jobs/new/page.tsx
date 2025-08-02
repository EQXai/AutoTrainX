'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { getApiClient } from '@/lib/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { 
  ArrowLeft, 
  Rocket, 
  Image as ImageIcon,
  Settings,
  Package,
  Users,
  FileText,
  Cpu,
  Zap,
  Terminal,
  Info
} from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

const formSchema = z.object({
  // Basic configuration
  source_path: z.string().min(1, 'Source path is required'),
  dataset_name: z.string().optional(),
  preset: z.string().min(1, 'Preset is required'),
  
  // Training mode
  mode: z.enum(['single', 'batch', 'variations']).default('single'),
  
  // Dataset configuration (removed repeats and class_name as per CLI bridge requirements)
  
  // Training options
  preview_count: z.number().min(0).max(20).default(0),
  generate_configs: z.boolean().default(true),
  auto_clean: z.boolean().default(true),
  
  // Batch mode specific
  batch_strategy: z.enum(['sequential', 'parallel']).default('sequential'),
  batch_datasets: z.array(z.object({
    source_path: z.string(),
    preset: z.string().optional(),
    dataset_name: z.string().optional(),
  })).optional(),
  
  // Variations mode specific
  base_preset: z.string().optional(),
  variations: z.record(z.array(z.any())).optional(),
})

type FormData = z.infer<typeof formSchema>

// Default presets list (hardcoded since API may not provide them)
const DEFAULT_PRESETS = [
  { name: 'FluxLORA', description: 'Flux LoRA training preset' },
  { name: 'FluxCheckpoint', description: 'Flux Checkpoint training preset' },
  { name: 'SDXLCheckpoint', description: 'SDXL Checkpoint training preset' },
  { name: 'FL1', description: 'Custom Flux preset 1' },
  { name: 'FL2', description: 'Custom Flux preset 2' },
  { name: 'SX1', description: 'Custom SDXL preset 1' },
]

export default function NewJobPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const api = getApiClient()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [cliCommand, setCliCommand] = useState<string>('')
  
  // Get preset from URL params if provided
  const preselectedPreset = searchParams.get('preset')

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      source_path: '',
      dataset_name: '',
      preset: preselectedPreset || 'FluxLORA',
      mode: 'single',
      preview_count: 0,
      generate_configs: true,
      auto_clean: true,
      batch_strategy: 'sequential',
    },
  })

  const createJobMutation = useMutation({
    mutationFn: async (data: FormData) => {
      // Handle different training modes
      switch (data.mode) {
        case 'single':
          return api.training.single({
            source_path: data.source_path,
            preset: data.preset,
            dataset_name: data.dataset_name,
            preview_count: data.preview_count,
            generate_configs: data.generate_configs,
            auto_clean: data.auto_clean,
          })
        
        case 'batch':
          if (!data.batch_datasets || data.batch_datasets.length === 0) {
            throw new Error('At least one dataset is required for batch mode')
          }
          return api.training.batch({
            datasets: data.batch_datasets,
            strategy: data.batch_strategy,
            auto_clean: data.auto_clean,
          })
        
        case 'variations':
          if (!data.dataset_name) {
            throw new Error('Dataset name is required for variations mode')
          }
          if (!data.variations || Object.keys(data.variations).length === 0) {
            throw new Error('At least one parameter variation is required')
          }
          return api.training.variations({
            dataset_name: data.dataset_name,
            base_preset: data.base_preset || data.preset,
            variations: data.variations,
            auto_clean: data.auto_clean,
          })
        
        default:
          throw new Error('Invalid training mode')
      }
    },
    onSuccess: (response) => {
      // Show CLI command that was executed
      setCliCommand(response.command)
      
      if (response.success) {
        toast.success('Job submitted successfully!')
        
        // Always redirect to jobs list immediately
        router.push('/dashboard/jobs')
      } else {
        toast.error('Training command failed')
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.message || 'Failed to execute training command')
    }
  })

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true)
    try {
      await createJobMutation.mutateAsync(data)
    } catch (error) {
      // Error is handled by onError
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="container max-w-4xl py-6">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/jobs">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold">New Training Job</h1>
          <p className="text-muted-foreground">
            Configure and execute a training command via CLI
          </p>
        </div>
      </div>

      {/* CLI Bridge Mode Notice */}
      <Alert className="mb-6">
        <Info className="h-4 w-4" />
        <AlertTitle>CLI Bridge Mode</AlertTitle>
        <AlertDescription>
          This interface translates your configuration into CLI commands. 
          The actual training is executed through the AutoTrainX CLI, ensuring consistency with command-line usage.
        </AlertDescription>
      </Alert>

      {/* Show CLI Command Result */}
      {cliCommand && (
        <Alert className="mb-6">
          <Terminal className="h-4 w-4" />
          <AlertTitle>Executed Command</AlertTitle>
          <AlertDescription className="font-mono text-sm mt-2">
            {cliCommand}
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Training Configuration</CardTitle>
          <CardDescription>
            Configure your training parameters. These will be converted to CLI arguments.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <Tabs defaultValue="basic" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="basic">
                  <Package className="mr-2 h-4 w-4" />
                  Basic
                </TabsTrigger>
                <TabsTrigger value="dataset">
                  <FileText className="mr-2 h-4 w-4" />
                  Dataset
                </TabsTrigger>
                <TabsTrigger value="advanced">
                  <Settings className="mr-2 h-4 w-4" />
                  Advanced
                </TabsTrigger>
              </TabsList>

              <TabsContent value="basic" className="mt-6 space-y-6">
                {/* Training Mode */}
                <div className="space-y-3">
                  <Label>Training Mode</Label>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { value: 'single', label: 'Single', icon: Package, description: 'Train a single dataset' },
                      { value: 'batch', label: 'Batch', icon: Users, description: 'Train multiple datasets', disabled: true },
                      { value: 'variations', label: 'Variations', icon: Zap, description: 'Parameter variations', disabled: true }
                    ].map((mode) => (
                      <div
                        key={mode.value}
                        className={`relative rounded-lg border p-4 ${
                          mode.disabled 
                            ? 'opacity-50 cursor-not-allowed' 
                            : 'cursor-pointer hover:border-primary transition-colors'
                        } ${
                          form.watch('mode') === mode.value ? 'border-primary bg-primary/5' : ''
                        }`}
                        onClick={() => !mode.disabled && form.setValue('mode', mode.value as any)}
                      >
                        <div className="flex flex-col items-center text-center space-y-2">
                          <mode.icon className="h-8 w-8 text-muted-foreground" />
                          <h4 className="font-medium">{mode.label}</h4>
                          <p className="text-xs text-muted-foreground">{mode.description}</p>
                          {mode.disabled && (
                            <p className="text-xs text-red-500">Coming soon</p>
                          )}
                        </div>
                        {form.watch('mode') === mode.value && (
                          <Badge className="absolute top-2 right-2" variant="default">
                            Selected
                          </Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Source Path */}
                <div className="space-y-2">
                  <Label htmlFor="source_path">Dataset Path</Label>
                  <Input
                    id="source_path"
                    placeholder="/path/to/dataset"
                    {...form.register('source_path')}
                  />
                  <p className="text-sm text-muted-foreground">
                    Absolute path to your dataset directory
                  </p>
                  {form.formState.errors.source_path && (
                    <p className="text-sm text-red-500">{form.formState.errors.source_path.message}</p>
                  )}
                </div>

                {/* Preset Selection */}
                <div className="space-y-2">
                  <Label htmlFor="preset">Training Preset</Label>
                  <Select
                    value={form.watch('preset')}
                    onValueChange={(value) => form.setValue('preset', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a preset" />
                    </SelectTrigger>
                    <SelectContent>
                      {DEFAULT_PRESETS.map((preset) => (
                        <SelectItem key={preset.name} value={preset.name}>
                          <div>
                            <div className="font-medium">{preset.name}</div>
                            <div className="text-sm text-muted-foreground">{preset.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                      <SelectItem value="all">
                        <div>
                          <div className="font-medium">All Presets</div>
                          <div className="text-sm text-muted-foreground">Generate configs for all available presets</div>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </TabsContent>

              <TabsContent value="dataset" className="mt-6 space-y-6">
                {/* Dataset Name */}
                <div className="space-y-2">
                  <Label htmlFor="dataset_name">Dataset Name (Optional)</Label>
                  <Input
                    id="dataset_name"
                    placeholder="Auto-detected from path if not specified"
                    {...form.register('dataset_name')}
                  />
                  <p className="text-sm text-muted-foreground">
                    Custom name for the dataset. If not specified, it will be extracted from the source path.
                  </p>
                </div>

                {/* Note: Repeats and class_name are configured in the dataset itself, not via CLI parameters */}
              </TabsContent>

              <TabsContent value="advanced" className="mt-6 space-y-6">
                {/* Preview Count */}
                <div className="space-y-2">
                  <Label htmlFor="preview_count">Preview Images</Label>
                  <div className="flex items-center space-x-4">
                    <Slider
                      id="preview_count"
                      min={0}
                      max={20}
                      step={1}
                      value={[form.watch('preview_count')]}
                      onValueChange={(value) => form.setValue('preview_count', value[0])}
                      className="flex-1"
                    />
                    <span className="w-12 text-right font-mono">{form.watch('preview_count')}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Number of preview images to generate after training (0 to disable)
                  </p>
                </div>

                {/* Generate Configs */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="generate_configs">Generate Configurations</Label>
                    <p className="text-sm text-muted-foreground">
                      Generate training configuration files
                    </p>
                  </div>
                  <Switch
                    id="generate_configs"
                    checked={form.watch('generate_configs')}
                    onCheckedChange={(checked) => form.setValue('generate_configs', checked)}
                  />
                </div>

                {/* Auto Clean */}
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="auto_clean">Auto Clean</Label>
                    <p className="text-sm text-muted-foreground">
                      Automatically clean existing datasets before training
                    </p>
                  </div>
                  <Switch
                    id="auto_clean"
                    checked={form.watch('auto_clean')}
                    onCheckedChange={(checked) => form.setValue('auto_clean', checked)}
                  />
                </div>
              </TabsContent>
            </Tabs>

            <div className="flex justify-end space-x-4">
              <Button type="button" variant="outline" asChild>
                <Link href="/dashboard/jobs">Cancel</Link>
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Cpu className="mr-2 h-4 w-4 animate-spin" />
                    Executing...
                  </>
                ) : (
                  <>
                    <Rocket className="mr-2 h-4 w-4" />
                    Start Training
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}