import { useState, useEffect } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts'
import './App.css'

function App() {
  const [metadata, setMetadata] = useState([])
  const [selectedApp, setSelectedApp] = useState('')
  const [selectedEnv, setSelectedEnv] = useState('')
  const [availableEnvs, setAvailableEnvs] = useState([])
  
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  // Fetch metadata on mount
  useEffect(() => {
    fetch('/api/metadata')
      .then(res => res.json())
      .then(data => {
        setMetadata(data)
        if (data.length > 0) {
          // Default to first app/env
          const firstApp = data[0]
          setSelectedApp(firstApp.application)
          setAvailableEnvs(firstApp.environments)
          if (firstApp.environments.length > 0) {
            setSelectedEnv(firstApp.environments[0])
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
        // Reset selected env to first one if current not available
        if (!appData.environments.includes(selectedEnv)) {
          setSelectedEnv(appData.environments[0] || '')
        }
      }
    }
  }, [selectedApp, metadata])

  // Fetch list of tables when app/env changes
  useEffect(() => {
    if (selectedApp && selectedEnv) {
      setLoading(true)
      fetch(`/api/tables?app=${selectedApp}&env=${selectedEnv}`)
        .then(res => res.json())
        .then(data => {
          setTables(data)
          setLoading(false)
          if (data.length > 0) {
            setSelectedTable(data[0].table_name)
          } else {
            setSelectedTable(null)
            setProfile(null)
          }
        })
        .catch(err => {
          console.error('Failed to load tables:', err)
          setLoading(false)
        })
    }
  }, [selectedApp, selectedEnv])

  // Fetch profile when table is selected
  useEffect(() => {
    if (selectedTable && selectedApp && selectedEnv) {
      fetch(`/api/profiles/${selectedTable}?app=${selectedApp}&env=${selectedEnv}`)
        .then(res => res.json())
        .then(data => setProfile(data))
        .catch(err => console.error('Failed to load profile:', err))
    }
  }, [selectedTable, selectedApp, selectedEnv])

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-'
    if (typeof num === 'number') {
      return num.toLocaleString(undefined, { maximumFractionDigits: 4 })
    }
    return num
  }

  const getBarColor = (value) => {
    if (value >= 0.9) return '#22c55e' // green
    if (value >= 0.7) return '#eab308' // yellow
    return '#ef4444' // red
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
            <label className="text-xs text-gray-400 mb-1 uppercase font-bold tracking-wider">Environment</label>
            <select 
              value={selectedEnv}
              onChange={(e) => setSelectedEnv(e.target.value)}
              className="bg-gray-700 text-white border border-gray-600 rounded px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-green-500 w-48 text-sm"
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
                  <div className="font-medium truncate">{table.table_name}</div>
                  <div className="text-xs opacity-75 mt-1 flex justify-between">
                    <span>{table.row_count?.toLocaleString()} rows</span>
                    <span>{table.column_count} cols</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 overflow-y-auto bg-gray-900">
          {profile ? (
            <>
              {/* Table Header */}
              <div className="mb-6 bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-3xl font-bold text-white tracking-tight">{profile.table_name}</h2>
                      <span className="px-2 py-0.5 rounded text-xs font-mono bg-gray-700 text-gray-300 border border-gray-600">
                        {selectedApp} / {selectedEnv}
                      </span>
                    </div>
                    <p className="text-gray-400 mt-2 flex items-center gap-4 text-sm">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                        {profile.row_count?.toLocaleString()} rows
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                        {profile.columns?.length} columns
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        Profiled: {new Date(profile.columns[0]?.scan_time).toLocaleString()}
                      </span>
                    </p>
                  </div>
                </div>
              </div>

              {/* Charts Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Not Null Proportion Chart */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4 text-gray-200 flex items-center gap-2">
                    <span className="w-1 h-5 bg-green-500 rounded-full"></span>
                    Not Null Proportion
                  </h3>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={profile.columns} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
                      <XAxis type="number" domain={[0, 1]} stroke="#9ca3af" fontSize={12} tickFormatter={(val) => `${val * 100}%`} />
                      <YAxis dataKey="column_name" type="category" width={130} stroke="#9ca3af" tick={{ fontSize: 12, fill: '#D1D5DB' }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.5rem', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                        formatter={(value) => [`${(value * 100).toFixed(1)}%`, 'Present']}
                        labelStyle={{ color: '#E5E7EB', marginBottom: '0.25rem' }}
                        cursor={{ fill: 'rgba(55, 65, 81, 0.5)' }}
                      />
                      <Bar dataKey="not_null_proportion" radius={[0, 4, 4, 0]} barSize={20}>
                        {profile.columns?.map((entry, index) => (
                          <Cell key={index} fill={getBarColor(entry.not_null_proportion)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Distinct Proportion Chart */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-sm">
                  <h3 className="text-lg font-semibold mb-4 text-gray-200 flex items-center gap-2">
                    <span className="w-1 h-5 bg-purple-500 rounded-full"></span>
                    Distinct Proportion
                  </h3>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={profile.columns} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
                      <XAxis type="number" domain={[0, 1]} stroke="#9ca3af" fontSize={12} tickFormatter={(val) => `${val * 100}%`} />
                      <YAxis dataKey="column_name" type="category" width={130} stroke="#9ca3af" tick={{ fontSize: 12, fill: '#D1D5DB' }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '0.5rem', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                        formatter={(value) => [`${(value * 100).toFixed(1)}%`, 'Unique']}
                        labelStyle={{ color: '#E5E7EB', marginBottom: '0.25rem' }}
                        cursor={{ fill: 'rgba(55, 65, 81, 0.5)' }}
                      />
                      <Bar dataKey="distinct_proportion" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={20} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Column Details Table */}
              <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-sm">
                <h3 className="text-lg font-semibold p-4 border-b border-gray-700 text-gray-200 bg-gray-800/50">
                  Column Details
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-750 text-gray-400 uppercase text-xs font-semibold tracking-wider">
                      <tr>
                        <th className="px-6 py-3 text-left">Column</th>
                        <th className="px-4 py-3 text-left">Type</th>
                        <th className="px-4 py-3 text-right">Not Null</th>
                        <th className="px-4 py-3 text-right">Distinct</th>
                        <th className="px-4 py-3 text-center">Unique</th>
                        <th className="px-4 py-3 text-left">Min</th>
                        <th className="px-4 py-3 text-left">Max</th>
                        <th className="px-4 py-3 text-right">Avg</th>
                        <th className="px-4 py-3 text-right">Median</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {profile.columns?.map((col, idx) => (
                        <tr key={col.column_name} className={`hover:bg-gray-750 transition-colors ${idx % 2 === 0 ? 'bg-gray-800' : 'bg-gray-800/50'}`}>
                          <td className="px-6 py-3 font-medium text-blue-400">{col.column_name}</td>
                          <td className="px-4 py-3 text-gray-400 font-mono text-xs">{col.data_type}</td>
                          <td className="px-4 py-3 text-right">
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                              col.not_null_proportion >= 0.9 ? 'bg-green-900/30 text-green-400 border border-green-900' :
                              col.not_null_proportion >= 0.7 ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-900' :
                              'bg-red-900/30 text-red-400 border border-red-900'
                            }`}>
                              {formatNumber(col.not_null_proportion)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right text-gray-300">{formatNumber(col.distinct_proportion)}</td>
                          <td className="px-4 py-3 text-center">
                            {col.is_unique ? 
                              <span className="text-green-400 bg-green-900/30 p-1 rounded-full">✓</span> : 
                              <span className="text-gray-600">-</span>
                            }
                          </td>
                          <td className="px-4 py-3 text-gray-300 max-w-[120px] truncate font-mono text-xs" title={col.min}>{col.min || '-'}</td>
                          <td className="px-4 py-3 text-gray-300 max-w-[120px] truncate font-mono text-xs" title={col.max}>{col.max || '-'}</td>
                          <td className="px-4 py-3 text-right text-gray-300 font-mono">{formatNumber(col.avg)}</td>
                          <td className="px-4 py-3 text-right text-gray-300 font-mono">{formatNumber(col.median)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="text-6xl mb-4">📊</div>
              <p className="text-xl font-medium">Select a table to view profile</p>
              <p className="text-sm mt-2 opacity-75">Choose from the sidebar</p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
