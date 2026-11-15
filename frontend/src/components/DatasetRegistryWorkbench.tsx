import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Database, FileSpreadsheet, Loader2, RefreshCw, Trash2 } from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'

type DatasetRecord = {
  id: string
  filename: string
  file_type: string
  file_size_bytes: number
  row_count: number
  column_count: number
  columns: string[]
  data_types: Record<string, string>
  missing_values: Record<string, number>
  total_missing_values: number
  duplicate_rows: number
  created_at: string
}

export default function DatasetRegistryWorkbench({ onBack }: { onBack: () => void }) {
  const [items, setItems] = useState<DatasetRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<DatasetRecord | null>(null)

  const loadRegistry = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_URL}/api/v1/datasets/registry?limit=50&offset=0`)
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Unable to load dataset registry.')
      setItems(payload.items || [])
      setTotal(Number(payload.total) || 0)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load dataset registry.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadRegistry() }, [loadRegistry])

  const deleteRecord = async (id: string) => {
    if (!window.confirm('Delete this dataset metadata record? The original file is not stored here and will not be affected.')) return
    try {
      const response = await fetch(`${API_URL}/api/v1/datasets/registry/${id}`, { method: 'DELETE' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Unable to delete registry record.')
      if (selected?.id === id) setSelected(null)
      await loadRegistry()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete registry record.')
    }
  }

  return <main className="min-h-screen bg-[#09090f] px-4 py-8 text-zinc-100 sm:px-8">
    <div className="mx-auto max-w-7xl">
      <button onClick={onBack} className="mb-6 inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white"><ArrowLeft size={16}/>Back to overview</button>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><div className="flex items-center gap-2 text-violet-300"><Database size={18}/><span className="text-xs font-semibold tracking-[2px]">PERSISTENT WORKSPACE</span></div><h1 className="mt-2 text-3xl font-bold">Dataset registry.</h1><p className="mt-2 text-sm text-zinc-500">Browse datasets inspected and registered in your local database.</p></div>
        <button onClick={() => void loadRegistry()} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm text-zinc-300 hover:bg-white/5 disabled:opacity-50"><RefreshCw size={15} className={loading ? 'animate-spin' : ''}/>Refresh</button>
      </div>
      <div className="mt-7 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-[#11111b] p-5"><p className="text-xs text-zinc-500">Registered datasets</p><p className="mt-2 text-3xl font-bold">{total}</p></div>
        <div className="rounded-xl border border-white/10 bg-[#11111b] p-5"><p className="text-xs text-zinc-500">Records loaded</p><p className="mt-2 text-3xl font-bold">{items.length}</p></div>
        <div className="rounded-xl border border-emerald-500/15 bg-emerald-500/[0.04] p-5"><p className="text-xs text-emerald-300">Storage policy</p><p className="mt-2 text-lg font-semibold">Metadata only</p><p className="mt-1 text-xs text-zinc-500">No source files or raw rows stored</p></div>
      </div>
      {error && <div role="alert" className="mt-5 rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300">{error}</div>}
      <section className="mt-7 overflow-hidden rounded-2xl border border-white/[0.07] bg-[#11111b]">
        <div className="border-b border-white/5 p-5"><h2 className="font-semibold">Registered datasets</h2><p className="mt-1 text-xs text-zinc-500">Newest uploads appear first. Select a row to inspect its schema metadata.</p></div>
        {loading ? <div className="flex items-center justify-center gap-2 p-12 text-sm text-zinc-500"><Loader2 size={17} className="animate-spin"/>Loading registry...</div> : items.length === 0 ? <div className="p-12 text-center"><FileSpreadsheet size={28} className="mx-auto mb-3 text-zinc-600"/><p className="text-sm text-zinc-300">No registered datasets yet</p><p className="mt-1 text-xs text-zinc-500">Upload a dataset from Overview to register its metadata.</p></div> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-white/[0.025] text-xs text-zinc-500"><tr><th className="px-5 py-3 font-medium">Dataset</th><th className="px-5 py-3 font-medium">Rows × columns</th><th className="px-5 py-3 font-medium">Missing</th><th className="px-5 py-3 font-medium">Duplicates</th><th className="px-5 py-3 font-medium">File size</th><th className="px-5 py-3 font-medium">Registered</th><th className="px-5 py-3"/></tr></thead><tbody>{items.map(item => <tr key={item.id} className="border-t border-white/5 text-zinc-300 hover:bg-white/[0.02]"><td className="px-5 py-4"><button onClick={() => setSelected(item)} className="max-w-[280px] truncate text-left font-medium text-violet-300 hover:text-violet-200">{item.filename}</button><p className="mt-1 text-[10px] text-zinc-600">{item.file_type} · {item.id.slice(0, 8)}</p></td><td className="px-5 py-4 tabular-nums">{item.row_count.toLocaleString()} × {item.column_count}</td><td className="px-5 py-4 tabular-nums">{item.total_missing_values.toLocaleString()}</td><td className="px-5 py-4 tabular-nums">{item.duplicate_rows.toLocaleString()}</td><td className="px-5 py-4 tabular-nums">{(item.file_size_bytes / 1024).toFixed(1)} KB</td><td className="px-5 py-4 text-xs text-zinc-500">{new Date(item.created_at).toLocaleString()}</td><td className="px-5 py-4"><button title="Delete metadata record" onClick={() => void deleteRecord(item.id)} className="rounded-lg p-2 text-zinc-500 hover:bg-red-500/10 hover:text-red-300"><Trash2 size={15}/></button></td></tr>)}</tbody></table></div>}
      </section>
      {selected && <section className="mt-6 rounded-2xl border border-violet-400/20 bg-[#11111b] p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold tracking-wider text-violet-300">DATASET SCHEMA</p><h2 className="mt-1 break-all text-lg font-semibold">{selected.filename}</h2><p className="mt-1 text-xs text-zinc-500">{selected.row_count.toLocaleString()} rows · {selected.column_count} columns</p></div><button onClick={() => setSelected(null)} className="text-xs text-zinc-500 hover:text-white">Close</button></div><div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{selected.columns.map(column => <div key={column} className="rounded-lg border border-white/5 bg-white/[0.02] p-3"><p className="truncate text-sm text-zinc-200">{column}</p><p className="mt-1 text-xs text-zinc-500">{selected.data_types[column] || 'Unknown type'} · {selected.missing_values[column] || 0} missing</p></div>)}</div></section>}
      <p className="mt-6 text-xs text-zinc-600">InsightFlow AI · Dataset registry · Persistent metadata only</p>
    </div>
  </main>
}
