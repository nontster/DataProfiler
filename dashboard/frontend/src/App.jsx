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
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  // Fetch list of tables on mount
  useEffect(() => {
    fetch('/api/tables')
      .then(res => res.json())
      .then(data => {
        setTables(data)
        setLoading(false)
        if (data.length > 0) {
          setSelectedTable(data[0].table_name)
        }
      })
      .catch(err => {
        console.error('Failed to load tables:', err)
        setLoading(false)
      })
  }, [])

  // Fetch profile when table is selected
  useEffect(() => {
    if (selectedTable) {
      fetch(`/api/profiles/${selectedTable}`)
        .then(res => res.json())
        .then(data => setProfile(data))
        .catch(err => console.error('Failed to load profile:', err))
    }
  }, [selectedTable])

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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <h1 className="text-2xl font-bold text-blue-400">📊 Data Profile Dashboard</h1>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-gray-800 min-h-screen border-r border-gray-700 p-4">
          <h2 className="text-lg font-semibold mb-4 text-gray-300">Tables</h2>
          <ul className="space-y-2">
            {tables.map(table => (
              <li key={table.table_name}>
                <button
                  onClick={() => setSelectedTable(table.table_name)}
                  className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
                    selectedTable === table.table_name
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                  }`}
                >
                  <div className="font-medium">{table.table_name}</div>
                  <div className="text-sm opacity-75">
                    {table.row_count?.toLocaleString()} rows • {table.column_count} cols
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {profile && (
            <>
              {/* Table Header */}
              <div className="mb-6">
                <h2 className="text-3xl font-bold text-white">{profile.table_name}</h2>
                <p className="text-gray-400 mt-1">
                  {profile.row_count?.toLocaleString()} rows • {profile.columns?.length} columns
                </p>
              </div>

              {/* Charts Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Not Null Proportion Chart */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                  <h3 className="text-lg font-semibold mb-4 text-gray-200">Not Null Proportion</h3>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={profile.columns} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis type="number" domain={[0, 1]} stroke="#9ca3af" />
                      <YAxis dataKey="column_name" type="category" width={100} stroke="#9ca3af" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                        formatter={(value) => [value?.toFixed(2), 'Proportion']}
                      />
                      <Bar dataKey="not_null_proportion" radius={[0, 4, 4, 0]}>
                        {profile.columns?.map((entry, index) => (
                          <Cell key={index} fill={getBarColor(entry.not_null_proportion)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Distinct Proportion Chart */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                  <h3 className="text-lg font-semibold mb-4 text-gray-200">Distinct Proportion</h3>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={profile.columns} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis type="number" domain={[0, 1]} stroke="#9ca3af" />
                      <YAxis dataKey="column_name" type="category" width={100} stroke="#9ca3af" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                        formatter={(value) => [value?.toFixed(2), 'Proportion']}
                      />
                      <Bar dataKey="distinct_proportion" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Column Details Table */}
              <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                <h3 className="text-lg font-semibold p-4 border-b border-gray-700 text-gray-200">
                  Column Details
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-700">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Column</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Type</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Not Null</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Distinct</th>
                        <th className="px-4 py-3 text-center text-sm font-medium text-gray-300">Unique</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Min</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Max</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Avg</th>
                        <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Median</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {profile.columns?.map((col, idx) => (
                        <tr key={col.column_name} className={idx % 2 === 0 ? 'bg-gray-800' : 'bg-gray-750'}>
                          <td className="px-4 py-3 font-medium text-blue-400">{col.column_name}</td>
                          <td className="px-4 py-3 text-gray-400 text-sm">{col.data_type}</td>
                          <td className="px-4 py-3 text-right">
                            <span className={`px-2 py-1 rounded text-sm ${
                              col.not_null_proportion >= 0.9 ? 'bg-green-900 text-green-300' :
                              col.not_null_proportion >= 0.7 ? 'bg-yellow-900 text-yellow-300' :
                              'bg-red-900 text-red-300'
                            }`}>
                              {formatNumber(col.not_null_proportion)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right text-gray-300">{formatNumber(col.distinct_proportion)}</td>
                          <td className="px-4 py-3 text-center">
                            {col.is_unique ? 
                              <span className="text-green-400">✓</span> : 
                              <span className="text-gray-500">-</span>
                            }
                          </td>
                          <td className="px-4 py-3 text-gray-300 text-sm max-w-[100px] truncate">{col.min || '-'}</td>
                          <td className="px-4 py-3 text-gray-300 text-sm max-w-[100px] truncate">{col.max || '-'}</td>
                          <td className="px-4 py-3 text-right text-gray-300">{formatNumber(col.avg)}</td>
                          <td className="px-4 py-3 text-right text-gray-300">{formatNumber(col.median)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
