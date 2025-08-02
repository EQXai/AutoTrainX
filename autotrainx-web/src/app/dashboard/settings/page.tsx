'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getApiClient } from '@/lib/api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
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
  Settings as SettingsIcon,
  FolderOpen,
  Save,
  Trash2,
  CheckCircle,
  AlertCircle,
  Database,
  Key,
  TestTube,
  RefreshCw,
  HardDrive,
  FileText,
  Plus,
  Edit,
  Check,
  X
} from 'lucide-react'
import { toast } from 'sonner'

const api = getApiClient()

export default function SettingsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState<any>(null)
  const [profiles, setProfiles] = useState<Record<string, any>>({})
  const [dbStats, setDbStats] = useState<Record<string, any>>({})
  
  // Form states
  const [customPath, setCustomPath] = useState('')
  const [comfyuiPath, setComfyuiPath] = useState('')
  const [sheetsEnabled, setSheetsEnabled] = useState(false)
  const [spreadsheetId, setSpreadsheetId] = useState('')
  const [syncInterval, setSyncInterval] = useState(300)
  
  // Dialog states
  const [showNewProfile, setShowNewProfile] = useState(false)
  const [newProfileName, setNewProfileName] = useState('')

  useEffect(() => {
    loadSettings()
    loadProfiles()
    loadDatabaseStats()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await api.settings.get()
      setSettings(data)
      setCustomPath(data.custom_output_path || '')
      setComfyuiPath(data.comfyui_path || '')
      setSheetsEnabled(data.google_sheets.enabled)
      setSpreadsheetId(data.google_sheets.spreadsheet_id || '')
      setSyncInterval(data.google_sheets.sync_interval)
    } catch (error: any) {
      toast.error('Failed to load settings')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const loadProfiles = async () => {
    try {
      const data = await api.settings.listProfiles()
      setProfiles(data)
    } catch (error: any) {
      console.error('Failed to load profiles:', error)
    }
  }

  const loadDatabaseStats = async () => {
    try {
      const data = await api.settings.getDatabaseStats()
      setDbStats(data)
    } catch (error: any) {
      console.error('Failed to load database stats:', error)
    }
  }

  const saveSettings = async () => {
    setSaving(true)
    try {
      await api.settings.update({
        custom_output_path: customPath || null,
        active_profile: settings?.active_profile,
        comfyui_path: comfyuiPath || null,
        google_sheets: {
          enabled: sheetsEnabled,
          spreadsheet_id: spreadsheetId || null,
          credentials_path: settings?.google_sheets.credentials_path,
          sync_interval: syncInterval,
          batch_size: settings?.google_sheets.batch_size || 100
        },
        database_paths: settings?.database_paths || []
      })
      toast.success('Settings saved successfully')
      await loadSettings()
    } catch (error: any) {
      toast.error('Failed to save settings')
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  const saveProfile = async () => {
    if (!newProfileName.trim()) {
      toast.error('Profile name is required')
      return
    }

    try {
      await api.settings.saveProfile(newProfileName, customPath || undefined)
      toast.success(`Profile '${newProfileName}' saved`)
      setShowNewProfile(false)
      setNewProfileName('')
      await loadProfiles()
    } catch (error: any) {
      toast.error('Failed to save profile')
      console.error(error)
    }
  }

  const activateProfile = async (name: string) => {
    try {
      await api.settings.activateProfile(name)
      toast.success(`Profile '${name}' activated`)
      await loadSettings()
    } catch (error: any) {
      toast.error('Failed to activate profile')
      console.error(error)
    }
  }

  const deleteProfile = async (name: string) => {
    if (confirm(`Are you sure you want to delete profile '${name}'?`)) {
      try {
        await api.settings.deleteProfile(name)
        toast.success(`Profile '${name}' deleted`)
        await loadProfiles()
        if (settings?.active_profile === name) {
          await loadSettings()
        }
      } catch (error: any) {
        toast.error('Failed to delete profile')
        console.error(error)
      }
    }
  }

  const validateComfyUI = async () => {
    try {
      await api.settings.validateComfyUI()
      toast.success('ComfyUI installation validated successfully')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'ComfyUI validation failed')
    }
  }

  const testSheetsConnection = async () => {
    try {
      await api.settings.testSheetsConnection()
      toast.success('Google Sheets connection successful')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Connection test failed')
    }
  }

  const cleanupDatabase = async () => {
    if (confirm('This will remove old records from the database. Continue?')) {
      try {
        await api.settings.cleanupDatabase(30)
        toast.success('Database cleanup completed')
        await loadDatabaseStats()
      } catch (error: any) {
        toast.error('Database cleanup failed')
        console.error(error)
      }
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  if (loading) {
    return (
      <div className="container py-6">
        <Skeleton className="h-8 w-48 mb-6" />
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    )
  }

  return (
    <div className="container py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <SettingsIcon className="h-8 w-8" />
            Settings
          </h1>
          <p className="text-muted-foreground">
            Configure system paths, integrations, and preferences
          </p>
        </div>
        <Button onClick={saveSettings} disabled={saving}>
          {saving ? (
            <>
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Save Settings
            </>
          )}
        </Button>
      </div>

      <Tabs defaultValue="paths" className="space-y-4">
        <TabsList>
          <TabsTrigger value="paths">
            <FolderOpen className="mr-2 h-4 w-4" />
            Paths & Profiles
          </TabsTrigger>
          <TabsTrigger value="comfyui">
            <SettingsIcon className="mr-2 h-4 w-4" />
            ComfyUI
          </TabsTrigger>
          <TabsTrigger value="sheets">
            <FileText className="mr-2 h-4 w-4" />
            Google Sheets
          </TabsTrigger>
          <TabsTrigger value="database">
            <Database className="mr-2 h-4 w-4" />
            Database
          </TabsTrigger>
        </TabsList>

        {/* Paths & Profiles Tab */}
        <TabsContent value="paths" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Output Path Configuration</CardTitle>
              <CardDescription>
                Configure where models and outputs are saved
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="custom-path">Custom Output Path</Label>
                <div className="flex gap-2">
                  <Input
                    id="custom-path"
                    value={customPath}
                    onChange={(e) => setCustomPath(e.target.value)}
                    placeholder="/path/to/custom/output"
                  />
                  <Button variant="outline" size="icon">
                    <FolderOpen className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                  Leave empty to use default workspace path
                </p>
              </div>

              {settings?.active_profile && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    Active Profile: <strong>{settings.active_profile}</strong>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Path Profiles</CardTitle>
                  <CardDescription>
                    Save and switch between different path configurations
                  </CardDescription>
                </div>
                <Dialog open={showNewProfile} onOpenChange={setShowNewProfile}>
                  <DialogTrigger asChild>
                    <Button size="sm">
                      <Plus className="mr-2 h-4 w-4" />
                      New Profile
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Create New Profile</DialogTitle>
                      <DialogDescription>
                        Save the current path configuration as a profile
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="profile-name">Profile Name</Label>
                        <Input
                          id="profile-name"
                          value={newProfileName}
                          onChange={(e) => setNewProfileName(e.target.value)}
                          placeholder="production, development, etc."
                        />
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Current path: {customPath || 'Default workspace'}
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setShowNewProfile(false)}>
                        Cancel
                      </Button>
                      <Button onClick={saveProfile}>
                        Save Profile
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
            <CardContent>
              {Object.keys(profiles).length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">
                  No profiles saved yet
                </div>
              ) : (
                <div className="space-y-2">
                  {Object.entries(profiles).map(([name, profile]) => (
                    <div key={name} className="flex items-center justify-between p-3 rounded-lg border">
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          {name}
                          {settings?.active_profile === name && (
                            <Badge variant="default" className="text-xs">Active</Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {profile.custom_path || 'Default workspace'}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => activateProfile(name)}
                          disabled={settings?.active_profile === name}
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => deleteProfile(name)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ComfyUI Tab */}
        <TabsContent value="comfyui" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>ComfyUI Configuration</CardTitle>
              <CardDescription>
                Configure ComfyUI installation for preview generation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="comfyui-path">ComfyUI Installation Path</Label>
                <div className="flex gap-2">
                  <Input
                    id="comfyui-path"
                    value={comfyuiPath}
                    onChange={(e) => setComfyuiPath(e.target.value)}
                    placeholder="/path/to/ComfyUI"
                  />
                  <Button variant="outline" size="icon">
                    <FolderOpen className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="flex gap-2">
                <Button variant="outline" onClick={validateComfyUI}>
                  <TestTube className="mr-2 h-4 w-4" />
                  Validate Installation
                </Button>
              </div>

              {comfyuiPath && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Make sure ComfyUI is properly installed at the specified path
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Google Sheets Tab */}
        <TabsContent value="sheets" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Google Sheets Integration</CardTitle>
              <CardDescription>
                Sync training data with Google Sheets
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="sheets-enabled">Enable Google Sheets Sync</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically sync job data to a spreadsheet
                  </p>
                </div>
                <Switch
                  id="sheets-enabled"
                  checked={sheetsEnabled}
                  onCheckedChange={setSheetsEnabled}
                />
              </div>

              {sheetsEnabled && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="spreadsheet-id">Spreadsheet ID</Label>
                    <Input
                      id="spreadsheet-id"
                      value={spreadsheetId}
                      onChange={(e) => setSpreadsheetId(e.target.value)}
                      placeholder="1234567890abcdef..."
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="sync-interval">Sync Interval (seconds)</Label>
                    <Input
                      id="sync-interval"
                      type="number"
                      value={syncInterval}
                      onChange={(e) => setSyncInterval(parseInt(e.target.value) || 300)}
                      min="60"
                      max="3600"
                    />
                  </div>

                  <div className="flex gap-2">
                    <Button variant="outline" onClick={testSheetsConnection}>
                      <TestTube className="mr-2 h-4 w-4" />
                      Test Connection
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Database Tab */}
        <TabsContent value="database" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Database Management</CardTitle>
              <CardDescription>
                View and manage system databases
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.keys(dbStats).length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">
                  No databases found
                </div>
              ) : (
                <div className="space-y-2">
                  {Object.entries(dbStats).map(([name, stats]: [string, any]) => (
                    <div key={name} className="flex items-center justify-between p-3 rounded-lg border">
                      <div className="flex items-center gap-3">
                        <Database className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <div className="font-medium">{name}</div>
                          <div className="text-sm text-muted-foreground">
                            {formatBytes(stats.size)}
                          </div>
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => router.push('/dashboard/database')}
                      >
                        View
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <div className="pt-4 border-t">
                <Button variant="outline" onClick={cleanupDatabase}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Cleanup Old Records
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}