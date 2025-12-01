import { useState } from 'react'
import { AlertCircle, AlertTriangle, Info, ChevronDown, ChevronUp } from 'lucide-react'

interface Difference {
  id: string
  type: string
  severity: string
  element_selector?: string
  element_name?: string
  figma_value: any
  website_value: any
  delta?: string
  description: string
  screenshot_url?: string
  coordinates?: { x: number; y: number }
}

interface DiffViewerProps {
  differences: Difference[]
}

export default function DiffViewer({ differences }: DiffViewerProps) {
  const [filter, setFilter] = useState<string>('all')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const filteredDiffs = differences.filter((diff) => {
    if (filter === 'all') return true
    return diff.severity === filter || diff.type === filter
  })

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      default:
        return <Info className="w-5 h-5 text-blue-500" />
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-l-red-500 bg-red-50'
      case 'warning':
        return 'border-l-yellow-500 bg-yellow-50'
      default:
        return 'border-l-blue-500 bg-blue-50'
    }
  }

  const getTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      color: 'bg-blue-100 text-blue-800',
      typography: 'bg-pink-100 text-pink-800',
      spacing: 'bg-green-100 text-green-800',
      dimension: 'bg-yellow-100 text-yellow-800',
      layout: 'bg-indigo-100 text-indigo-800',
      visual: 'bg-purple-100 text-purple-800',
    }

    return (
      <span className={`px-2 py-1 rounded text-xs font-semibold uppercase ${colors[type] || 'bg-gray-100 text-gray-800'}`}>
        {type}
      </span>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-gray-900">
          Detected Differences ({filteredDiffs.length})
        </h3>

        {/* Filters */}
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              filter === 'all'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('critical')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              filter === 'critical'
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Critical
          </button>
          <button
            onClick={() => setFilter('warning')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              filter === 'warning'
                ? 'bg-yellow-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Warnings
          </button>
        </div>
      </div>

      {/* Differences List */}
      <div className="space-y-3">
        {filteredDiffs.map((diff) => {
          const isExpanded = expandedIds.has(diff.id)

          return (
            <div
              key={diff.id}
              className={`border-l-4 rounded-lg p-4 transition-all ${getSeverityColor(diff.severity)}`}
            >
              {/* Header */}
              <div
                className="flex items-start justify-between cursor-pointer"
                onClick={() => toggleExpand(diff.id)}
              >
                <div className="flex items-start gap-3 flex-1">
                  {getSeverityIcon(diff.severity)}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      {getTypeBadge(diff.type)}
                      {diff.element_name && (
                        <span className="text-sm font-semibold text-gray-800 bg-white px-2 py-1 rounded border border-gray-200">
                          📍 {diff.element_name}
                        </span>
                      )}
                      {diff.coordinates && (
                        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                          Position: ({diff.coordinates.x}, {diff.coordinates.y})
                        </span>
                      )}
                    </div>
                    <p className="text-gray-900 font-medium">{diff.description}</p>
                    {diff.element_selector && (
                      <code className="text-xs text-gray-600 bg-white px-2 py-1 rounded mt-1 inline-block border border-gray-200">
                        {diff.element_selector}
                      </code>
                    )}
                  </div>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-gray-500" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-500" />
                )}
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="mt-4 pl-8 space-y-3">
                  {/* Element Info */}
                  {(diff.element_name || diff.element_selector) && (
                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                      <p className="text-xs font-semibold text-gray-600 mb-2 uppercase">
                        Element Details
                      </p>
                      {diff.element_name && (
                        <p className="text-sm text-gray-900 mb-1">
                          <span className="font-medium">Name:</span> {diff.element_name}
                        </p>
                      )}
                      {diff.element_selector && (
                        <p className="text-sm text-gray-900 mb-1">
                          <span className="font-medium">Selector:</span>{' '}
                          <code className="bg-gray-100 px-1 rounded">{diff.element_selector}</code>
                        </p>
                      )}
                      {diff.coordinates && (
                        <p className="text-sm text-gray-900">
                          <span className="font-medium">Location:</span> x={diff.coordinates.x}, y={diff.coordinates.y}
                        </p>
                      )}
                    </div>
                  )}

                  {diff.figma_value !== null && diff.website_value !== null && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-white rounded-lg p-3 border border-gray-200">
                        <p className="text-xs font-semibold text-gray-600 mb-1 uppercase">
                          Figma Design
                        </p>
                        <p className="text-sm font-mono text-gray-900">
                          {typeof diff.figma_value === 'object'
                            ? JSON.stringify(diff.figma_value)
                            : diff.figma_value}
                        </p>
                        {diff.type === 'color' && diff.figma_value && (
                          <div 
                            className="w-full h-6 mt-2 rounded border border-gray-300"
                            style={{ backgroundColor: diff.figma_value }}
                          />
                        )}
                      </div>
                      <div className="bg-white rounded-lg p-3 border border-gray-200">
                        <p className="text-xs font-semibold text-gray-600 mb-1 uppercase">
                          Website Implementation
                        </p>
                        <p className="text-sm font-mono text-gray-900">
                          {typeof diff.website_value === 'object'
                            ? JSON.stringify(diff.website_value)
                            : diff.website_value || 'Not found'}
                        </p>
                        {diff.type === 'color' && diff.website_value && (
                          <div 
                            className="w-full h-6 mt-2 rounded border border-gray-300"
                            style={{ backgroundColor: diff.website_value }}
                          />
                        )}
                      </div>
                    </div>
                  )}

                  {diff.delta && (
                    <div className="bg-white rounded-lg p-3 border border-orange-200 bg-orange-50">
                      <p className="text-xs font-semibold text-orange-700 mb-1 uppercase">
                        Difference
                      </p>
                      <p className="text-sm text-orange-900 font-medium">{diff.delta}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {filteredDiffs.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <Info className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No differences found in this category</p>
          </div>
        )}
      </div>
    </div>
  )
}
