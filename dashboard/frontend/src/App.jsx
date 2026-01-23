import { useState, useEffect } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend
} from 'recharts'
import './App.css'

function App() {
  const [metadata, setMetadata] = useState([])
  const [selectedApp, setSelectedApp] = useState('')
  const [selectedEnv1, setSelectedEnv1] = useState('')
  const [selectedEnv2, setSelectedEnv2] = useState('')
  const [availableEnvs, setAvailableEnvs] = useState([])
  
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [autoIncrement, setAutoIncrement] = useState(null)
  const [loading, setLoading] = useState(true)
  const [backendConfig, setBackendConfig] = useState(null)

  // Colors for environments
  const ENV1_COLOR = '#3b82f6' // blue
  const ENV2_COLOR = '#22c55e' // green

  // Fetch backend config on mount
  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => setBackendConfig(data))
      .catch(err => console.error('Failed to load config:', err))
  }, [])

  // Fetch metadata on mount
  useEffect(() => {
    fetch('/api/metadata')
      .then(res => res.json())
      .then(data => {
        setMetadata(data)
        if (data.length > 0) {
          // Default to first app
          const firstApp = data[0]
          setSelectedApp(firstApp.application)
          setAvailableEnvs(firstApp.environments)
          if (firstApp.environments.length >= 2) {
            setSelectedEnv1(firstApp.environments[0])
            setSelectedEnv2(firstApp.environments[1])
          } else if (firstApp.environments.length === 1) {
            setSelectedEnv1(firstApp.environments[0])
            setSelectedEnv2(firstApp.environments[0])
          }
        } else {
          setLoading(false)
        }
      })
      .catch(err => {
        console.error('Failed to load metadata:', err)
        setLoading(false)
      })
  }, [])

  // Update available envs when app changes
  useEffect(() => {
    if (selectedApp && metadata.length > 0) {
      const appData = metadata.find(m => m.application === selectedApp)
      if (appData) {
        setAvailableEnvs(appData.environments)
        // Reset selected envs if current not available
        if (!appData.environments.includes(selectedEnv1)) {
          setSelectedEnv1(appData.environments[0] || '')
        }
        if (!appData.environments.includes(selectedEnv2)) {
          setSelectedEnv2(appData.environments[1] || appData.environments[0] || '')
        }
      }
    }
  }, [selectedApp, metadata])

  // Fetch list of tables (union from both environments)
  useEffect(() => {
    if (selectedApp && selectedEnv1) {
      setLoading(true)
      // Fetch tables for both environments and merge
      const fetchTables = async () => {
        try {
          const [res1, res2] = await Promise.all([
            fetch(`/api/tables?app=${selectedApp}&env=${selectedEnv1}`),
            selectedEnv2 && selectedEnv2 !== selectedEnv1 
              ? fetch(`/api/tables?app=${selectedApp}&env=${selectedEnv2}`)
              : Promise.resolve({ json: () => [] })
          ])
          
          const tables1 = await res1.json()
          const tables2 = selectedEnv2 ? await res2.json() : []
          
          // Merge tables (unique by table_name)
          const tableMap = new Map()
          tables1.forEach(t => tableMap.set(t.table_name, { ...t, inEnv1: true, inEnv2: false }))
          tables2.forEach(t => {
            if (tableMap.has(t.table_name)) {
              tableMap.get(t.table_name).inEnv2 = true
            } else {
              tableMap.set(t.table_name, { ...t, inEnv1: false, inEnv2: true })
            }
          })
          
          const mergedTables = Array.from(tableMap.values()).sort((a, b) => 
            a.table_name.localeCompare(b.table_name)
          )
          
          setTables(mergedTables)
          setLoading(false)
          if (mergedTables.length > 0) {
            setSelectedTable(mergedTables[0].table_name)
          } else {
            setSelectedTable(null)
            setComparison(null)
          }
        } catch (err) {
          console.error('Failed to load tables:', err)
          setLoading(false)
        }
      }
      fetchTables()
    }
  }, [selectedApp, selectedEnv1, selectedEnv2])

  // Fetch comparison when table is selected
  useEffect(() => {
    if (selectedTable && selectedApp && selectedEnv1 && selectedEnv2) {
      // Fetch profile comparison
      fetch(`/api/profiles/compare/${selectedTable}?app=${selectedApp}&env1=${selectedEnv1}&env2=${selectedEnv2}`)
        .then(res => res.json())
        .then(data => setComparison(data))
        .catch(err => {
          console.error('Failed to load comparison:', err)
          setComparison(null)
        })
      
      // Fetch auto-increment comparison
      fetch(`/api/autoincrement/compare/${selectedTable}?app=${selectedApp}&env1=${selectedEnv1}&env2=${selectedEnv2}`)
        .then(res => res.json())
        .then(data => setAutoIncrement(data))
        .catch(err => {
          console.error('Failed to load auto-increment:', err)
          setAutoIncrement(null)
        })
    }
  }, [selectedTable, selectedApp, selectedEnv1, selectedEnv2])

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-'
    if (typeof num === 'number') {
      return num.toLocaleString(undefined, { maximumFractionDigits: 4 })
    }
    return num
  }

  const formatPercent = (num) => {
    if (num === null || num === undefined) return '-'
    return `${(num * 100).toFixed(1)}%`
  }

  const formatDateTime = (dateStr) => {
    if (!dateStr) return '-'
    try {
      return new Date(dateStr).toLocaleString()
    } catch {
      return dateStr
    }
  }

  const formatDiff = (num) => {
    if (num === null || num === undefined) return '-'
    const percent = (num * 100).toFixed(1)
    if (num > 0) return `+${percent}%`
    if (num < 0) return `${percent}%`
    return '0%'
  }

  const getDiffColor = (diff) => {
    if (diff === null || diff === undefined) return 'text-gray-500'
    if (Math.abs(diff) < 0.01) return 'text-gray-400'
    if (diff > 0) return 'text-green-400'
    return 'text-red-400'
  }

  // Check if data type supports min/max display (numeric and date/time types)
  const isMinMaxSupported = (dataType) => {
    if (!dataType) return false
    const supportedTypes = [
      // Numeric types
      'integer', 'int', 'bigint', 'smallint', 'tinyint', 'decimal', 'numeric', 
      'float', 'real', 'double', 'money', 'serial', 'bigserial',
      'int2', 'int4', 'int8', 'float4', 'float8',
      // Date/Time types
      'date', 'timestamp', 'time', 'interval', 'datetime'
    ]
    const lowerType = dataType.toLowerCase()
    return supportedTypes.some(t => lowerType.includes(t))
  }

  // Prepare chart data for comparison
  const getComparisonChartData = (metric) => {
    if (!comparison || !comparison.columns) return []
    return comparison.columns.map(col => ({
      column_name: col.column_name,
      env1: col.env1?.[metric] || 0,
      env2: col.env2?.[metric] || 0
    }))
  }

  if (loading && tables.length === 0 && !selectedApp) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4 flex justify-between items-center shadow-md z-10">
        <h1 className="text-2xl font-bold text-blue-400 flex items-center gap-2">
          <span>📊</span> Data Profile Dashboard
          <span className="text-sm font-normal text-gray-400 ml-2">Environment Comparison</span>
          {backendConfig && (
            <span className={`text-xs font-normal px-2 py-0.5 rounded-full ml-2 ${
              backendConfig.metrics_backend === 'postgresql' 
                ? 'bg-blue-900/50 text-blue-300 border border-blue-700' 
                : 'bg-orange-900/50 text-orange-300 border border-orange-700'
            }`}>
              📊 {backendConfig.backend_display_name}
            </span>
          )}
        </h1>

        {/* Global Filters */}
        <div className="flex gap-4">
          <div className="flex flex-col">
            <label className="text-xs text-gray-400 mb-1 uppercase font-bold tracking-wider">Application</label>
            <select 
              value={selectedApp}
              onChange={(e) => setSelectedApp(e.target.value)}
              className="bg-gray-700 text-white border border-gray-600 rounded px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 w-48 text-sm"
            >
              <option value="" disabled>Select App</option>
              {metadata.map(m => (
                <option key={m.application} value={m.application}>{m.application}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col">
            <label className="text-xs text-blue-400 mb-1 uppercase font-bold tracking-wider flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
              Environment 1
            </label>
            <select 
              value={selectedEnv1}
              onChange={(e) => setSelectedEnv1(e.target.value)}
              className="bg-gray-700 text-white border border-blue-600 rounded px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 w-40 text-sm"
            >
              <option value="" disabled>Select Env</option>
              {availableEnvs.map(env => (
                <option key={env} value={env}>{env.toUpperCase()}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col">
            <label className="text-xs text-green-400 mb-1 uppercase font-bold tracking-wider flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              Environment 2
            </label>
            <select 
              value={selectedEnv2}
              onChange={(e) => setSelectedEnv2(e.target.value)}
              className="bg-gray-700 text-white border border-green-600 rounded px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-green-500 w-40 text-sm"
            >
              <option value="" disabled>Select Env</option>
              {availableEnvs.map(env => (
                <option key={env} value={env}>{env.toUpperCase()}</option>
              ))}
            </select>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-gray-800 border-r border-gray-700 p-4 overflow-y-auto">
          <h2 className="text-lg font-semibold mb-4 text-gray-300 flex justify-between items-center">
            <span>Tables</span>
            <span className="text-xs bg-gray-700 text-gray-400 px-2 py-0.5 rounded-full">{tables.length}</span>
          </h2>
          
          {tables.length === 0 && !loading && (
            <div className="text-gray-500 text-sm text-center py-4">No tables found</div>
          )}

          <ul className="space-y-2">
            {tables.map(table => (
              <li key={table.table_name}>
                <button
                  onClick={() => setSelectedTable(table.table_name)}
                  className={`w-full text-left px-4 py-3 rounded-lg transition-colors border border-transparent ${
                    selectedTable === table.table_name
                      ? 'bg-blue-600 text-white border-blue-500 shadow-lg'
                      : 'bg-gray-700 hover:bg-gray-650 text-gray-200 hover:border-gray-600'
                  }`}
                >
                  <div className="font-medium truncate flex items-center justify-between">
                    <span>{table.table_name}</span>
                    <div className="flex gap-1">
                      {table.inEnv1 && <span className="w-2 h-2 rounded-full bg-blue-500" title={selectedEnv1}></span>}
                      {table.inEnv2 && <span className="w-2 h-2 rounded-full bg-green-500" title={selectedEnv2}></span>}
                    </div>
                  </div>
                  <div className="text-xs opacity-75 mt-1">
                    {table.row_count?.toLocaleString()} rows
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 overflow-y-auto bg-gray-900">
          {comparison ? (
            <>
              {/* Table Header */}
              <div className="mb-6 bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-3xl font-bold text-white tracking-tight">{comparison.table_name}</h2>
                      <span className="px-2 py-0.5 rounded text-xs font-mono bg-gray-700 text-gray-300 border border-gray-600">
                        {selectedApp}
                      </span>
                    </div>
                    <div className="mt-3 flex gap-6">
                      {/* Env 1 Info */}
                      <div className="flex items-center gap-3 text-sm bg-blue-900/20 px-3 py-2 rounded-lg border border-blue-800">
                        <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                        <span className="text-blue-400 font-semibold">{selectedEnv1.toUpperCase()}</span>
                        {comparison.env1.exists ? (
                          <>
                            <span className="text-gray-400">
                              {comparison.env1.row_count?.toLocaleString()} rows
                            </span>
                            <span className="text-gray-500">|</span>
                            <span className="text-gray-400 text-xs">
                              Profiled: {formatDateTime(comparison.env1.scan_time)}
                            </span>
                            {comparison.env1.database_host && (
                              <>
                                <span className="text-gray-500">|</span>
                                <span className="text-gray-400 text-xs font-mono" title="Database Host">
                                  🖥️ {comparison.env1.database_host}
                                </span>
                              </>
                            )}
                          </>
                        ) : (
                          <span className="text-red-400">(No data)</span>
                        )}
                      </div>
                      {/* Env 2 Info */}
                      <div className="flex items-center gap-3 text-sm bg-green-900/20 px-3 py-2 rounded-lg border border-green-800">
                        <span className="w-3 h-3 rounded-full bg-green-500"></span>
                        <span className="text-green-400 font-semibold">{selectedEnv2.toUpperCase()}</span>
                        {comparison.env2.exists ? (
                          <>
                            <span className="text-gray-400">
                              {comparison.env2.row_count?.toLocaleString()} rows
                            </span>
                            <span className="text-gray-500">|</span>
                            <span className="text-gray-400 text-xs">
                              Profiled: {formatDateTime(comparison.env2.scan_time)}
                            </span>
                            {comparison.env2.database_host && (
                              <>
                                <span className="text-gray-500">|</span>
                                <span className="text-gray-400 text-xs font-mono" title="Database Host">
                                  🖥️ {comparison.env2.database_host}
                                </span>
                              </>
                            )}
                          </>
                        ) : (
                          <span className="text-red-400">(No data)</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Charts Section - Side by Side Comparison */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Not Null Proportion Comparison Chart */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4 text-gray-200 flex items-center gap-2">
                    <span className="w-1 h-5 bg-gradient-to-b from-blue-500 to-green-500 rounded-full"></span>
                    Not Null Proportion Comparison
                  </h3>
                  <ResponsiveContainer width="100%" height={Math.max(250, comparison.columns.length * 30)}>
                    <BarChart data={getComparisonChartData('not_null_proportion')} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
                      <XAxis type="number" domain={[0, 1]} stroke="#9ca3af" fontSize={12} tickFormatter={(val) => `${val * 100}%`} />
                      <YAxis dataKey="column_name" type="category" width={130} stroke="#9ca3af" tick={{ fontSize: 11, fill: '#D1D5DB' }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.5rem' }}
                        formatter={(value, name) => [`${(value * 100).toFixed(1)}%`, name === 'env1' ? selectedEnv1.toUpperCase() : selectedEnv2.toUpperCase()]}
                        labelStyle={{ color: '#E5E7EB' }}
                      />
                      <Legend 
                        formatter={(value) => value === 'env1' ? selectedEnv1.toUpperCase() : selectedEnv2.toUpperCase()}
                      />
                      <Bar dataKey="env1" fill={ENV1_COLOR} radius={[0, 4, 4, 0]} barSize={12} />
                      <Bar dataKey="env2" fill={ENV2_COLOR} radius={[0, 4, 4, 0]} barSize={12} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Distinct Proportion Comparison Chart */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4 text-gray-200 flex items-center gap-2">
                    <span className="w-1 h-5 bg-gradient-to-b from-blue-500 to-green-500 rounded-full"></span>
                    Distinct Proportion Comparison
                  </h3>
                  <ResponsiveContainer width="100%" height={Math.max(250, comparison.columns.length * 30)}>
                    <BarChart data={getComparisonChartData('distinct_proportion')} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
                      <XAxis type="number" domain={[0, 1]} stroke="#9ca3af" fontSize={12} tickFormatter={(val) => `${val * 100}%`} />
                      <YAxis dataKey="column_name" type="category" width={130} stroke="#9ca3af" tick={{ fontSize: 11, fill: '#D1D5DB' }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.5rem' }}
                        formatter={(value, name) => [`${(value * 100).toFixed(1)}%`, name === 'env1' ? selectedEnv1.toUpperCase() : selectedEnv2.toUpperCase()]}
                        labelStyle={{ color: '#E5E7EB' }}
                      />
                      <Legend 
                        formatter={(value) => value === 'env1' ? selectedEnv1.toUpperCase() : selectedEnv2.toUpperCase()}
                      />
                      <Bar dataKey="env1" fill={ENV1_COLOR} radius={[0, 4, 4, 0]} barSize={12} />
                      <Bar dataKey="env2" fill={ENV2_COLOR} radius={[0, 4, 4, 0]} barSize={12} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Column Details Comparison Table */}
              <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-sm">
                <h3 className="text-lg font-semibold p-4 border-b border-gray-700 text-gray-200 bg-gray-800/50">
                  Column Details Comparison
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-750 text-gray-400 uppercase text-xs font-semibold tracking-wider">
                      <tr>
                        <th className="px-4 py-3 text-left" rowSpan={2}>Column</th>
                        <th className="px-4 py-3 text-left" rowSpan={2}>Type</th>
                        <th className="px-4 py-3 text-center border-l border-gray-600 bg-blue-900/20" colSpan={5}>
                          <span className="flex items-center justify-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                            {selectedEnv1.toUpperCase()}
                          </span>
                        </th>
                        <th className="px-4 py-3 text-center border-l border-gray-600 bg-green-900/20" colSpan={5}>
                          <span className="flex items-center justify-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-green-500"></span>
                            {selectedEnv2.toUpperCase()}
                          </span>
                        </th>
                        <th className="px-4 py-3 text-center border-l border-gray-600" colSpan={2}>Diff (Δ)</th>
                      </tr>
                      <tr>
                        <th className="px-3 py-2 text-right border-l border-gray-600 bg-blue-900/10">Not Null</th>
                        <th className="px-3 py-2 text-right bg-blue-900/10">Distinct</th>
                        <th className="px-3 py-2 text-center bg-blue-900/10">Unique</th>
                        <th className="px-3 py-2 text-left bg-blue-900/10">Min</th>
                        <th className="px-3 py-2 text-left bg-blue-900/10">Max</th>
                        <th className="px-3 py-2 text-right border-l border-gray-600 bg-green-900/10">Not Null</th>
                        <th className="px-3 py-2 text-right bg-green-900/10">Distinct</th>
                        <th className="px-3 py-2 text-center bg-green-900/10">Unique</th>
                        <th className="px-3 py-2 text-left bg-green-900/10">Min</th>
                        <th className="px-3 py-2 text-left bg-green-900/10">Max</th>
                        <th className="px-3 py-2 text-right border-l border-gray-600">Not Null</th>
                        <th className="px-3 py-2 text-right">Distinct</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {comparison.columns?.map((col, idx) => (
                        <tr key={col.column_name} className={`hover:bg-gray-750 transition-colors ${
                          !col.in_env1 || !col.in_env2 ? 'bg-yellow-900/10' : idx % 2 === 0 ? 'bg-gray-800' : 'bg-gray-800/50'
                        }`}>
                          <td className="px-4 py-3 font-medium text-blue-400">
                            <div className="flex items-center gap-2">
                              {col.column_name}
                              {(!col.in_env1 || !col.in_env2) && (
                                <span className="text-xs bg-yellow-900/50 text-yellow-400 px-1.5 py-0.5 rounded border border-yellow-700">
                                  {!col.in_env1 ? `Only in ${selectedEnv2}` : `Only in ${selectedEnv1}`}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-gray-400 font-mono text-xs">{col.data_type}</td>
                          
                          {/* Env1 values */}
                          <td className="px-3 py-3 text-right border-l border-gray-700">
                            {col.env1 ? formatPercent(col.env1.not_null_proportion) : '-'}
                          </td>
                          <td className="px-3 py-3 text-right">
                            {col.env1 ? formatPercent(col.env1.distinct_proportion) : '-'}
                          </td>
                          <td className="px-3 py-3 text-center">
                            {col.env1 ? (col.env1.is_unique ? 
                              <span className="text-green-400">✓</span> : 
                              <span className="text-gray-600">-</span>
                            ) : '-'}
                          </td>
                          <td className="px-3 py-3 text-left text-gray-300 font-mono text-xs max-w-[100px] truncate" title={col.env1?.min}>
                            {isMinMaxSupported(col.data_type) ? (col.env1?.min || '-') : '-'}
                          </td>
                          <td className="px-3 py-3 text-left text-gray-300 font-mono text-xs max-w-[100px] truncate" title={col.env1?.max}>
                            {isMinMaxSupported(col.data_type) ? (col.env1?.max || '-') : '-'}
                          </td>
                          
                          {/* Env2 values */}
                          <td className="px-3 py-3 text-right border-l border-gray-700">
                            {col.env2 ? formatPercent(col.env2.not_null_proportion) : '-'}
                          </td>
                          <td className="px-3 py-3 text-right">
                            {col.env2 ? formatPercent(col.env2.distinct_proportion) : '-'}
                          </td>
                          <td className="px-3 py-3 text-center">
                            {col.env2 ? (col.env2.is_unique ? 
                              <span className="text-green-400">✓</span> : 
                              <span className="text-gray-600">-</span>
                            ) : '-'}
                          </td>
                          <td className="px-3 py-3 text-left text-gray-300 font-mono text-xs max-w-[100px] truncate" title={col.env2?.min}>
                            {isMinMaxSupported(col.data_type) ? (col.env2?.min || '-') : '-'}
                          </td>
                          <td className="px-3 py-3 text-left text-gray-300 font-mono text-xs max-w-[100px] truncate" title={col.env2?.max}>
                            {isMinMaxSupported(col.data_type) ? (col.env2?.max || '-') : '-'}
                          </td>
                          
                          {/* Diff values */}
                          <td className={`px-3 py-3 text-right font-mono text-xs border-l border-gray-700 ${getDiffColor(col.not_null_diff)}`}>
                            {formatDiff(col.not_null_diff)}
                          </td>
                          <td className={`px-3 py-3 text-right font-mono text-xs ${getDiffColor(col.distinct_diff)}`}>
                            {formatDiff(col.distinct_diff)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Auto-Increment Overflow Monitoring */}
              {autoIncrement && autoIncrement.columns && autoIncrement.columns.length > 0 && (
                <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <span className="text-2xl">⚠️</span>
                    Auto-Increment Overflow Monitoring
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-700 text-left text-gray-400 text-sm">
                          <th className="px-4 py-3 font-medium">Column</th>
                          <th className="px-4 py-3 font-medium">Type</th>
                          <th className="px-3 py-3 text-center border-l border-gray-700 font-medium" style={{color: ENV1_COLOR}}>{selectedEnv1?.toUpperCase()} Usage</th>
                          <th className="px-3 py-3 text-center font-medium" style={{color: ENV1_COLOR}}>Days Until Full</th>
                          <th className="px-3 py-3 text-center font-medium" style={{color: ENV1_COLOR}}>Status</th>
                          <th className="px-3 py-3 text-center border-l border-gray-700 font-medium" style={{color: ENV2_COLOR}}>{selectedEnv2?.toUpperCase()} Usage</th>
                          <th className="px-3 py-3 text-center font-medium" style={{color: ENV2_COLOR}}>Days Until Full</th>
                          <th className="px-3 py-3 text-center font-medium" style={{color: ENV2_COLOR}}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {autoIncrement.columns.map((col, idx) => (
                          <tr key={idx} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                            <td className="px-4 py-3 font-medium text-white">{col.column_name}</td>
                            <td className="px-4 py-3 text-gray-400 font-mono text-xs">{col.data_type}</td>
                            
                            {/* Env1 values */}
                            <td className="px-3 py-3 text-center border-l border-gray-700">
                              {col.env1 ? (
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  col.env1.usage_percentage >= 90 ? 'bg-red-900/50 text-red-400' :
                                  col.env1.usage_percentage >= 75 ? 'bg-yellow-900/50 text-yellow-400' :
                                  'bg-green-900/50 text-green-400'
                                }`}>
                                  {col.env1.usage_percentage?.toFixed(6)}%
                                </span>
                              ) : '-'}
                            </td>
                            <td className="px-3 py-3 text-center">
                              {col.env1?.days_until_full ? (
                                <span className={`${
                                  col.env1.days_until_full < 30 ? 'text-red-400' :
                                  col.env1.days_until_full < 90 ? 'text-yellow-400' :
                                  'text-green-400'
                                }`}>
                                  {Math.round(col.env1.days_until_full)} days
                                </span>
                              ) : <span className="text-gray-500">N/A</span>}
                            </td>
                            <td className="px-3 py-3 text-center">
                              {col.env1?.alert_status === 'CRITICAL' && <span className="text-red-400">🔴 CRITICAL</span>}
                              {col.env1?.alert_status === 'WARNING' && <span className="text-yellow-400">🟡 WARNING</span>}
                              {col.env1?.alert_status === 'OK' && <span className="text-green-400">🟢 OK</span>}
                              {!col.env1 && '-'}
                            </td>
                            
                            {/* Env2 values */}
                            <td className="px-3 py-3 text-center border-l border-gray-700">
                              {col.env2 ? (
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  col.env2.usage_percentage >= 90 ? 'bg-red-900/50 text-red-400' :
                                  col.env2.usage_percentage >= 75 ? 'bg-yellow-900/50 text-yellow-400' :
                                  'bg-green-900/50 text-green-400'
                                }`}>
                                  {col.env2.usage_percentage?.toFixed(6)}%
                                </span>
                              ) : '-'}
                            </td>
                            <td className="px-3 py-3 text-center">
                              {col.env2?.days_until_full ? (
                                <span className={`${
                                  col.env2.days_until_full < 30 ? 'text-red-400' :
                                  col.env2.days_until_full < 90 ? 'text-yellow-400' :
                                  'text-green-400'
                                }`}>
                                  {Math.round(col.env2.days_until_full)} days
                                </span>
                              ) : <span className="text-gray-500">N/A</span>}
                            </td>
                            <td className="px-3 py-3 text-center">
                              {col.env2?.alert_status === 'CRITICAL' && <span className="text-red-400">🔴 CRITICAL</span>}
                              {col.env2?.alert_status === 'WARNING' && <span className="text-yellow-400">🟡 WARNING</span>}
                              {col.env2?.alert_status === 'OK' && <span className="text-green-400">🟢 OK</span>}
                              {!col.env2 && '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="text-6xl mb-4">📊</div>
              <p className="text-xl font-medium">Select a table to compare profiles</p>
              <p className="text-sm mt-2 opacity-75">Choose from the sidebar</p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
