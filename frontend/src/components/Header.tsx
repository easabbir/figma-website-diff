import { Layers } from 'lucide-react'

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Layers className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Figma ↔ Website UI Comparison
            </h1>
            <p className="text-sm text-gray-600">
              Detect visual inconsistencies between design and implementation
            </p>
          </div>
        </div>
      </div>
    </header>
  )
}
