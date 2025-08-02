'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  ArrowLeft,
  Book,
  Code,
  Cpu,
  Database,
  FileText,
  FolderOpen,
  GitBranch,
  PlayCircle,
  Rocket,
  Settings,
  Terminal,
  Zap,
  ChevronRight,
  Info,
  AlertCircle
} from 'lucide-react'
import { motion } from 'framer-motion'

export default function DocsPage() {
  const sections = [
    {
      title: 'Getting Started',
      icon: Rocket,
      description: 'Learn the basics of AutoTrainX and start training your first model',
      items: [
        { title: 'Installation', href: '#installation' },
        { title: 'Quick Start Guide', href: '#quick-start' },
        { title: 'System Requirements', href: '#requirements' },
        { title: 'Configuration', href: '#configuration' }
      ]
    },
    {
      title: 'Training Pipeline',
      icon: Cpu,
      description: 'Understand how the training pipeline works',
      items: [
        { title: 'Training Presets', href: '#presets' },
        { title: 'Dataset Preparation', href: '#datasets' },
        { title: 'Job Management', href: '#jobs' },
        { title: 'Model Output', href: '#output' }
      ]
    },
    {
      title: 'CLI Commands',
      icon: Terminal,
      description: 'Complete command-line interface reference',
      items: [
        { title: 'Training Commands', href: '#cli-commands' },
        { title: 'Preset Management', href: '#cli-commands' },
        { title: 'Database Commands', href: '#cli-commands' },
        { title: 'System Configuration', href: '#cli-commands' }
      ]
    },
    {
      title: 'API Reference',
      icon: Code,
      description: 'Complete API documentation for developers',
      items: [
        { title: 'REST API', href: '#api' },
        { title: 'WebSocket Events', href: '#websocket' },
        { title: 'Authentication', href: '#auth' },
        { title: 'Error Handling', href: '#errors' }
      ]
    },
    {
      title: 'Advanced Topics',
      icon: Zap,
      description: 'Advanced features and customization options',
      items: [
        { title: 'Custom Training Scripts', href: '#custom-scripts' },
        { title: 'Google Sheets Integration', href: '#sheets' },
        { title: 'Database Schema', href: '#database' },
        { title: 'Performance Tuning', href: '#performance' }
      ]
    }
  ]

  return (
    <div className="container py-8 max-w-7xl">
      {/* Header */}
      <motion.div 
        className="mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Link href="/dashboard">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </Link>
        
        <div className="flex items-center gap-4 mb-4">
          <Book className="h-8 w-8 text-primary" />
          <h1 className="text-4xl font-bold">AutoTrainX Documentation</h1>
        </div>
        
        <p className="text-lg text-muted-foreground">
          Everything you need to know about using AutoTrainX for ML model training
        </p>
      </motion.div>

      {/* Quick Links */}
      <motion.div 
        className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-12"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        {sections.map((section, index) => {
          const Icon = section.icon
          return (
            <motion.div
              key={section.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 + index * 0.1 }}
            >
              <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <Icon className="h-6 w-6 text-primary" />
                    <CardTitle className="text-lg">{section.title}</CardTitle>
                  </div>
                  <CardDescription>{section.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {section.items.map((item) => (
                      <li key={item.title}>
                        <a 
                          href={item.href}
                          className="text-sm text-muted-foreground hover:text-primary transition-colors flex items-center gap-1"
                        >
                          <ChevronRight className="h-3 w-3" />
                          {item.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </motion.div>

      {/* Main Content */}
      <motion.div 
        className="space-y-12"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.6 }}
      >
        {/* Installation Section */}
        <section id="installation">
          <h2 className="text-3xl font-bold mb-4 flex items-center gap-3">
            <Terminal className="h-8 w-8 text-primary" />
            Installation
          </h2>
          <Card>
            <CardContent className="prose prose-neutral dark:prose-invert max-w-none pt-6">
              <h3 className="text-xl font-semibold mb-4">Prerequisites</h3>
              <ul className="space-y-2">
                <li>Python 3.8 or higher</li>
                <li>CUDA-compatible GPU (for GPU acceleration)</li>
                <li>ComfyUI installed and configured</li>
                <li>Node.js 18+ (for web interface)</li>
              </ul>

              <h3 className="text-xl font-semibold mt-6 mb-4">Installation Steps</h3>
              <ol className="space-y-4">
                <li>
                  <p className="font-medium">Clone the repository:</p>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                    <code>git clone https://github.com/yourusername/AutoTrainX.git</code>
                  </pre>
                </li>
                <li>
                  <p className="font-medium">Install Python dependencies:</p>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                    <code>cd AutoTrainX{'\n'}pip install -r requirements.txt</code>
                  </pre>
                </li>
                <li>
                  <p className="font-medium">Install web interface dependencies:</p>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                    <code>cd autotrainx-web{'\n'}npm install</code>
                  </pre>
                </li>
                <li>
                  <p className="font-medium">Configure ComfyUI path in config.json:</p>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                    <code>{`{
  "COMFYPATH": "/path/to/your/ComfyUI"
}`}</code>
                  </pre>
                </li>
              </ol>
            </CardContent>
          </Card>
        </section>

        {/* Quick Start Section */}
        <section id="quick-start">
          <h2 className="text-3xl font-bold mb-4 flex items-center gap-3">
            <PlayCircle className="h-8 w-8 text-primary" />
            Quick Start Guide
          </h2>
          <Card>
            <CardContent className="prose prose-neutral dark:prose-invert max-w-none pt-6">
              <h3 className="text-xl font-semibold mb-4">Starting AutoTrainX</h3>
              <ol className="space-y-4">
                <li>
                  <p className="font-medium">Start the API server:</p>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                    <code>python api_server.py</code>
                  </pre>
                </li>
                <li>
                  <p className="font-medium">Start the web interface:</p>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                    <code>cd autotrainx-web{'\n'}npm run dev</code>
                  </pre>
                </li>
                <li>
                  <p className="font-medium">Open your browser and navigate to:</p>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                    <code>http://localhost:3000</code>
                  </pre>
                </li>
              </ol>

              <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg flex gap-3">
                <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-blue-900 dark:text-blue-100">Pro Tip:</p>
                  <p className="text-blue-800 dark:text-blue-200 text-sm">
                    You can also start the Google Sheets sync daemon for automatic synchronization:
                  </p>
                  <pre className="bg-blue-100 dark:bg-blue-900 p-2 rounded mt-2 text-sm">
                    <code>python sheets_sync_daemon.py --daemon</code>
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Training Presets Section */}
        <section id="presets">
          <h2 className="text-3xl font-bold mb-4 flex items-center gap-3">
            <Settings className="h-8 w-8 text-primary" />
            Training Presets
          </h2>
          <Card>
            <CardContent className="prose prose-neutral dark:prose-invert max-w-none pt-6">
              <p className="text-lg mb-4">
                AutoTrainX includes several pre-configured training presets optimized for different use cases:
              </p>
              
              <div className="grid gap-4 mt-6">
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold">FAST</h4>
                    <Badge>Quick Training</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Optimized for rapid prototyping with 500 steps. Good for testing concepts.
                  </p>
                </div>
                
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold">STANDARD</h4>
                    <Badge>Balanced</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Default preset with 1000 steps. Balances quality and training time.
                  </p>
                </div>
                
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold">HIGH_QUALITY</h4>
                    <Badge variant="secondary">Premium</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Extended training with 2000 steps for maximum quality results.
                  </p>
                </div>
                
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold">CUSTOM</h4>
                    <Badge variant="outline">Flexible</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Create your own presets with custom parameters and workflows.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Dataset Preparation Section */}
        <section id="datasets">
          <h2 className="text-3xl font-bold mb-4 flex items-center gap-3">
            <FolderOpen className="h-8 w-8 text-primary" />
            Dataset Preparation
          </h2>
          <Card>
            <CardContent className="prose prose-neutral dark:prose-invert max-w-none pt-6">
              <h3 className="text-xl font-semibold mb-4">Dataset Structure</h3>
              <p className="mb-4">
                AutoTrainX expects datasets to follow this structure:
              </p>
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                <code>{`dataset_name/
├── images/
│   ├── image1.jpg
│   ├── image2.png
│   └── ...
└── captions/
    ├── image1.txt
    ├── image2.txt
    └── ...`}</code>
              </pre>

              <h3 className="text-xl font-semibold mt-6 mb-4">Caption Files</h3>
              <p className="mb-4">
                Each image should have a corresponding text file with the same name containing the caption.
              </p>

              <div className="mt-6 p-4 bg-amber-50 dark:bg-amber-950 rounded-lg flex gap-3">
                <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-900 dark:text-amber-100">Important:</p>
                  <p className="text-amber-800 dark:text-amber-200 text-sm">
                    Ensure image filenames match their caption filenames exactly (excluding extensions).
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* API Reference Section */}
        <section id="api">
          <h2 className="text-3xl font-bold mb-4 flex items-center gap-3">
            <Code className="h-8 w-8 text-primary" />
            API Reference
          </h2>
          <Card>
            <CardContent className="prose prose-neutral dark:prose-invert max-w-none pt-6">
              <h3 className="text-xl font-semibold mb-4">Base URL</h3>
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                <code>http://localhost:8000/api</code>
              </pre>

              <h3 className="text-xl font-semibold mt-6 mb-4">Key Endpoints</h3>
              <div className="space-y-4">
                <div className="border rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge className="bg-green-100 text-green-800">GET</Badge>
                    <code className="font-mono text-sm">/jobs</code>
                  </div>
                  <p className="text-sm text-muted-foreground">List all training jobs</p>
                </div>

                <div className="border rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge className="bg-blue-100 text-blue-800">POST</Badge>
                    <code className="font-mono text-sm">/jobs</code>
                  </div>
                  <p className="text-sm text-muted-foreground">Create a new training job</p>
                </div>

                <div className="border rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge className="bg-green-100 text-green-800">GET</Badge>
                    <code className="font-mono text-sm">/datasets</code>
                  </div>
                  <p className="text-sm text-muted-foreground">List available datasets</p>
                </div>

                <div className="border rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge className="bg-green-100 text-green-800">GET</Badge>
                    <code className="font-mono text-sm">/presets</code>
                  </div>
                  <p className="text-sm text-muted-foreground">Get available training presets</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* CLI Commands Section */}
        <section id="cli-commands">
          <h2 className="text-3xl font-bold mb-4 flex items-center gap-3">
            <Terminal className="h-8 w-8 text-primary" />
            CLI Commands Reference
          </h2>
          <Card>
            <CardContent className="prose prose-neutral dark:prose-invert max-w-none pt-6">
              <p className="text-lg mb-6">
                AutoTrainX provides a comprehensive command-line interface for all training operations. Below are all available commands organized by category.
              </p>

              {/* Training Commands */}
              <h3 className="text-2xl font-semibold mt-8 mb-4 flex items-center gap-2">
                <PlayCircle className="h-6 w-6 text-primary" />
                Training Commands
              </h3>
              <div className="space-y-4">
                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --train --single --source /path/to/dataset --preset FL1
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Train a model with a single dataset. Replace <code>/path/to/dataset</code> with your dataset directory path.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --train --batch --source /path/to/datasets --preset FL1
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Train multiple datasets in batch mode. The source directory should contain multiple dataset folders.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2 break-all">
                    python main.py --train --mode variations --source dataset --preset FL1 --variations network_dim=32,64,128
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Train with parameter variations for experimentation. This will create multiple training runs with different network dimensions.
                  </p>
                </div>
              </div>

              {/* Preset Management */}
              <h3 className="text-2xl font-semibold mt-8 mb-4 flex items-center gap-2">
                <Settings className="h-6 w-6 text-primary" />
                Preset Management
              </h3>
              <div className="space-y-4">
                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --list-presets
                  </code>
                  <p className="text-sm text-muted-foreground">
                    List all available presets including built-in and custom presets.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --show-preset --name FL2
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Show detailed configuration of a specific preset including all parameters and settings.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2 break-all">
                    python main.py --create-preset --name MyPreset --base FluxLORA --overrides learning_rate=1e-5
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Create a custom preset based on an existing preset with specific parameter overrides.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --delete-preset --name MyPreset
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Delete a custom preset. Built-in presets cannot be deleted.
                  </p>
                </div>
              </div>

              {/* Path Profile Management */}
              <h3 className="text-2xl font-semibold mt-8 mb-4 flex items-center gap-2">
                <FolderOpen className="h-6 w-6 text-primary" />
                Path Profile Management
              </h3>
              <div className="space-y-4">
                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --list-profiles
                  </code>
                  <p className="text-sm text-muted-foreground">
                    List all saved path profiles for different environments.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --save-profile "production" --custom-path /data/models
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Save current path configuration as a named profile for easy switching.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --use-profile "production" --train --source dataset1
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Use a saved profile for training. This loads all path configurations from the profile.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --delete-profile "old_profile"
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Delete a path profile that is no longer needed.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --set-profile "production"
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Set a profile as the default for all future commands.
                  </p>
                </div>
              </div>

              {/* Database Commands */}
              <h3 className="text-2xl font-semibold mt-8 mb-4 flex items-center gap-2">
                <Database className="h-6 w-6 text-primary" />
                Database Commands
              </h3>
              <div className="space-y-4">
                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --job-history --limit 50
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Show recent job execution history with specified limit. Default shows last 20 jobs.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --job-info --job-id JOB123456
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Display detailed information about a specific job including all parameters and results.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --db-stats
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Show database statistics including total jobs, success rate, and storage usage.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --clear-db
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Clear all database records. This action requires confirmation and cannot be undone.
                  </p>
                  <div className="mt-2 p-2 bg-red-50 dark:bg-red-950 rounded flex gap-2">
                    <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 flex-shrink-0" />
                    <span className="text-xs text-red-800 dark:text-red-200">Warning: This will permanently delete all training history!</span>
                  </div>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --cleanup-stale
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Clean up stuck processes and stale job entries from the database.
                  </p>
                </div>
              </div>

              {/* System Configuration */}
              <h3 className="text-2xl font-semibold mt-8 mb-4 flex items-center gap-2">
                <Cpu className="h-6 w-6 text-primary" />
                System Configuration
              </h3>
              <div className="space-y-4">
                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --comfyui-path /path/to/ComfyUI
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Configure the path to your ComfyUI installation for preview generation.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --set-progress-display progress
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Set training display mode. Options: <code>progress</code> (progress bar) or <code>raw</code> (raw output).
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --status
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Show system status including resource usage, active processes, and configuration.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --configure
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Generate configuration files for existing datasets automatically.
                  </p>
                </div>
              </div>

              {/* Information & Diagnostics */}
              <h3 className="text-2xl font-semibold mt-8 mb-4 flex items-center gap-2">
                <Info className="h-6 w-6 text-primary" />
                Information & Diagnostics
              </h3>
              <div className="space-y-4">
                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --dataset-info dataset_name
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Show detailed information about a dataset including image count, captions, and statistics.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --validate-preview
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Validate that the image preview system is working correctly.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python main.py --diagnose-comfyui
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Diagnose ComfyUI installation and check for common issues.
                  </p>
                </div>
              </div>

              {/* Interactive Menu */}
              <h3 className="text-2xl font-semibold mt-8 mb-4 flex items-center gap-2">
                <Zap className="h-6 w-6 text-primary" />
                Interactive Menu
              </h3>
              <div className="space-y-4">
                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    python menu.py
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Launch the interactive configuration menu for a guided experience.
                  </p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/30">
                  <code className="font-mono text-sm block mb-2">
                    ./run_menu.sh
                  </code>
                  <p className="text-sm text-muted-foreground">
                    Launch menu with automatic virtual environment activation (Linux/Mac).
                  </p>
                </div>
              </div>

              <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg flex gap-3">
                <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-blue-900 dark:text-blue-100">Pro Tips:</p>
                  <ul className="text-blue-800 dark:text-blue-200 text-sm space-y-1 mt-2">
                    <li>• Use <code>--help</code> with any command to see all available options</li>
                    <li>• Commands can be combined, e.g., <code>--use-profile prod --train --batch</code></li>
                    <li>• Most commands support verbose output with <code>--verbose</code> flag</li>
                    <li>• Use <code>--dry-run</code> to preview what a command will do without executing</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Google Sheets Integration */}
        <section id="sheets">
          <h2 className="text-3xl font-bold mb-4 flex items-center gap-3">
            <Database className="h-8 w-8 text-primary" />
            Google Sheets Integration
          </h2>
          <Card>
            <CardContent className="prose prose-neutral dark:prose-invert max-w-none pt-6">
              <p className="mb-4">
                AutoTrainX can automatically sync training data to Google Sheets for easy monitoring and analysis.
              </p>

              <h3 className="text-xl font-semibold mb-4">Setup Steps</h3>
              <ol className="space-y-4">
                <li>
                  <p className="font-medium">Create a Google Cloud service account</p>
                </li>
                <li>
                  <p className="font-medium">Download the credentials JSON file</p>
                </li>
                <li>
                  <p className="font-medium">Place it in <code>settings/google_credentials.json</code></p>
                </li>
                <li>
                  <p className="font-medium">Configure the spreadsheet ID in <code>config.json</code>:</p>
                  <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
                    <code>{`"google_sheets_sync": {
  "enabled": true,
  "spreadsheet_id": "YOUR_SPREADSHEET_ID",
  "credentials_path": "settings/google_credentials.json"
}`}</code>
                  </pre>
                </li>
                <li>
                  <p className="font-medium">Share the spreadsheet with your service account email</p>
                </li>
              </ol>
            </CardContent>
          </Card>
        </section>

        {/* Footer */}
        <div className="mt-16 pt-8 border-t text-center text-muted-foreground">
          <p>AutoTrainX Documentation • Version 1.0.0</p>
          <p className="text-sm mt-2">
            Need help? Check out our{' '}
            <a href="https://github.com/yourusername/AutoTrainX" className="text-primary hover:underline">
              GitHub repository
            </a>
          </p>
        </div>
      </motion.div>
    </div>
  )
}