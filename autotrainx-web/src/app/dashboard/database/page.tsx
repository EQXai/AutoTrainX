'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Database, RefreshCw, Table as TableIcon, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TableInfo {
  name: string
  row_count: number
  columns: Array<{
    name: string
    type: string
    nullable: boolean
    primary_key: boolean
  }>
}

interface TableData {
  columns: string[]
  rows: any[][]
  total_count: number
}

export default function DatabasePage() {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [tableData, setTableData] = useState<TableData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingData, setLoadingData] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTables()
  }, [])

  const fetchTables = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/backend/database/tables')
      if (!response.ok) {
        throw new Error('Failed to fetch tables')
      }
      const data = await response.json()
      setTables(data.tables)
      if (data.tables.length > 0 && !selectedTable) {
        setSelectedTable(data.tables[0].name)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const fetchTableData = async (tableName: string) => {
    try {
      setLoadingData(true)
      const response = await fetch(`/api/backend/database/tables/${tableName}/data?limit=100`)
      if (!response.ok) {
        throw new Error('Failed to fetch table data')
      }
      const data = await response.json()
      setTableData(data)
    } catch (err) {
      console.error('Error fetching table data:', err)
    } finally {
      setLoadingData(false)
    }
  }

  useEffect(() => {
    if (selectedTable) {
      fetchTableData(selectedTable)
    }
  }, [selectedTable])

  if (loading) {
    return (
      <div className="container py-6">
        <div className="mb-6">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-96 mt-2" />
        </div>
        <div className="grid gap-4">
          <Skeleton className="h-[400px]" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container py-6">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Error Loading Database
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error}</p>
            <Button onClick={fetchTables} className="mt-4">
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const selectedTableInfo = tables.find(t => t.name === selectedTable)

  return (
    <div className="container py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Database className="h-8 w-8" />
            Database Explorer
          </h1>
          <p className="text-muted-foreground">
            Browse and inspect database tables
          </p>
        </div>
        <Button onClick={fetchTables} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Tables List */}
      <div className="grid gap-6 md:grid-cols-4">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Tables</CardTitle>
            <CardDescription>
              {tables.length} tables found
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px]">
              <div className="space-y-2">
                {tables.map((table) => (
                  <Button
                    key={table.name}
                    variant={selectedTable === table.name ? "default" : "ghost"}
                    className={cn(
                      "w-full justify-start",
                      selectedTable === table.name && "bg-primary text-primary-foreground"
                    )}
                    onClick={() => setSelectedTable(table.name)}
                  >
                    <TableIcon className="mr-2 h-4 w-4" />
                    <span className="truncate">{table.name}</span>
                    <Badge variant="secondary" className="ml-auto">
                      {table.row_count}
                    </Badge>
                  </Button>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Table Details */}
        <div className="md:col-span-3 space-y-6">
          {selectedTableInfo && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>{selectedTableInfo.name}</CardTitle>
                  <CardDescription>
                    {selectedTableInfo.row_count} rows • {selectedTableInfo.columns.length} columns
                  </CardDescription>
                </CardHeader>
              </Card>

              <Tabs defaultValue="data" className="w-full">
                <TabsList>
                  <TabsTrigger value="data">Data</TabsTrigger>
                  <TabsTrigger value="structure">Structure</TabsTrigger>
                </TabsList>

                <TabsContent value="data" className="mt-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Table Data</CardTitle>
                      <CardDescription>
                        Showing first 100 rows of {tableData?.total_count || 0} total
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {loadingData ? (
                        <div className="space-y-2">
                          {[...Array(5)].map((_, i) => (
                            <Skeleton key={i} className="h-12 w-full" />
                          ))}
                        </div>
                      ) : tableData ? (
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                {tableData.columns.map((column) => (
                                  <TableHead key={column}>{column}</TableHead>
                                ))}
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {tableData.rows.map((row, idx) => (
                                <TableRow key={idx}>
                                  {row.map((cell, cellIdx) => (
                                    <TableCell key={cellIdx}>
                                      {cell === null ? (
                                        <span className="text-muted-foreground italic">NULL</span>
                                      ) : typeof cell === 'object' ? (
                                        <code className="text-xs">{JSON.stringify(cell)}</code>
                                      ) : (
                                        String(cell)
                                      )}
                                    </TableCell>
                                  ))}
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      ) : (
                        <p className="text-muted-foreground">No data available</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="structure" className="mt-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Table Structure</CardTitle>
                      <CardDescription>
                        Column definitions and constraints
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Column Name</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Nullable</TableHead>
                            <TableHead>Key</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedTableInfo.columns.map((column) => (
                            <TableRow key={column.name}>
                              <TableCell className="font-mono">{column.name}</TableCell>
                              <TableCell>
                                <Badge variant="outline">{column.type}</Badge>
                              </TableCell>
                              <TableCell>
                                {column.nullable ? (
                                  <Badge variant="secondary">YES</Badge>
                                ) : (
                                  <Badge variant="destructive">NO</Badge>
                                )}
                              </TableCell>
                              <TableCell>
                                {column.primary_key && (
                                  <Badge variant="default">PRIMARY</Badge>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </>
          )}
        </div>
      </div>
    </div>
  )
}