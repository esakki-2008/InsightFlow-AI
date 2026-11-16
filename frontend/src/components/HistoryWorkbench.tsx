import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowLeft, AlertCircle, CheckCircle2, ChevronLeft, ChevronRight, Clock3, Database, Eye, FileText, History, Loader2, RefreshCw, Search, Trash2, X } from 'lucide-react'

import { API_URL } from '../config/api'
const PAGE_SIZE = 10

type HistoryItem = {
  id: string
  filename: string
  analysis_type: string
  row_count: number | null
  column_count: number | null
  summary: Record<string, unknown>
  created_at: string
  notes: string | null
}

type HistoryResponse = {
  items: HistoryItem[]
  total: number
  limit: number
  offset: number
}

const labelize = (value: string) => value.replace(/[_-]+/g, ' ').replace(/\b\w/g, char => char.toUpperCase())
export default function HistoryWorkbench({ onBack }: { onBack: () => void }) {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [selected, setSelected] = useState<HistoryItem | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteBusy, setDeleteBusy] = useState(false)

  const loadHistory = useCallback(async (nextOffset: number) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/history?limit=${PAGE_SIZE}&offset=${nextOffset}`)
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Unable to load analysis history.')
      const data = result as HistoryResponse
      setError('')
      setItems(data.items ?? [])
      setTotal(data.total ?? 0)
      setOffset(data.offset ?? nextOffset)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load analysis history.')
    } finally {
      setBusy(false)
    }
  }, [])

  useEffect(() => { void Promise.resolve().then(() => loadHistory(0)) }, [loadHistory])

  const filteredItems = useMemo(() => {
    const term = query.trim().toLowerCase()
    if (!term) return items
    return items.filter(item =>
      item.filename.toLowerCase().includes(term) ||
      item.analysis_type.toLowerCase().includes(term) ||
      item.id.toLowerCase().includes(term) ||
      (item.notes ?? '').toLowerCase().includes(term),
    )
  }, [items, query])

  const page = Math.floor(offset / PAGE_SIZE) + 1
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const confirmDelete = async () => {
    if (!deletingId) return
    setDeleteBusy(true)
    setError('')
    setNotice('')
    try {
      const response = await fetch(`${API_URL}/api/v1/history/${deletingId}`, { method: 'DELETE' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Unable to delete this history record.')
      if (selected?.id === deletingId) setSelected(null)
      setDeletingId(null)
      setNotice('Analysis history record deleted.')
      const nextOffset = items.length === 1 && offset > 0 ? Math.max(0, offset - PAGE_SIZE) : offset
      setBusy(true)
      await loadHistory(nextOffset)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete this history record.')
    } finally {
      setDeleteBusy(false)
    }
  }

  const openDetails = async (item: HistoryItem) => {
    setSelected(item)
    try {
      const response = await fetch(`${API_URL}/api/v1/history/${item.id}`)
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Unable to load record details.')
      if (result.item) setSelected(result.item as HistoryItem)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load record details.')
    }
  }

  return <div className="min-h-screen bg-[#09090f] text-zinc-100">
    <header className="sticky top-0 z-20 border-b border-white/[0.06] bg-[#0d0d16]/95 backdrop-blur">
      <div className="mx-auto flex h-18 max-w-[1500px] items-center gap-3 px-5 sm:px-8">
        <button onClick={onBack} className="rounded-xl border border-white/10 p-2 text-zinc-400 hover:bg-white/5 hover:text-white" aria-label="Back to overview"><ArrowLeft size={18}/></button>
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600"><History size={21}/></div>
        <div><p className="font-semibold">InsightFlow AI</p><p className="text-[10px] tracking-[1.8px] text-zinc-500">ANALYSIS HISTORY</p></div>
      </div>
    </header>

    <main className="mx-auto max-w-[1500px] space-y-7 px-5 py-8 sm:px-8 lg:py-10">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="mb-2 text-xs font-semibold tracking-[2px] text-violet-300">PERSISTENT WORKSPACE</p><h1 className="text-3xl font-bold sm:text-4xl">Analysis history<span className="text-violet-400">.</span></h1><p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-500">Browse saved analysis summaries stored in your local database. Uploaded dataset rows and original files are not stored in this history.</p></div>
        <button onClick={() => { setNotice(''); setError(''); setBusy(true); void loadHistory(offset) }} disabled={busy} className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-zinc-300 hover:bg-white/[0.06] disabled:opacity-50">{busy ? <Loader2 size={16} className="animate-spin"/> : <RefreshCw size={16}/>}Refresh</button>
      </section>

      <section className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><p className="text-xs text-zinc-500">Saved records</p><p className="mt-3 text-3xl font-bold">{total.toLocaleString()}</p><p className="mt-2 text-xs text-zinc-600">All analysis types</p></div>
        <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><p className="text-xs text-zinc-500">Records on this page</p><p className="mt-3 text-3xl font-bold">{items.length}</p><p className="mt-2 text-xs text-zinc-600">Up to {PAGE_SIZE} per page</p></div>
        <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><p className="text-xs text-zinc-500">Storage</p><p className="mt-3 text-lg font-bold text-emerald-300">Metadata only</p><p className="mt-2 text-xs text-zinc-600">No raw dataset rows</p></div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#11111b]">
        <div className="flex flex-col gap-3 border-b border-white/[0.06] p-5 sm:flex-row sm:items-center sm:justify-between">
          <div><h2 className="font-semibold">Saved analyses</h2><p className="mt-1 text-xs text-zinc-500">Newest records appear first.</p></div>
          <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.025] px-3 py-2.5 sm:w-80"><Search size={16} className="shrink-0 text-zinc-500"/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search filename, type or notes…" className="w-full bg-transparent text-sm text-zinc-200 outline-none placeholder:text-zinc-600"/></label>
        </div>

        {error && <div role="alert" className="mx-5 mt-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-300"><AlertCircle size={16}/>{error}</div>}
        {notice && <div className="mx-5 mt-4 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-sm text-emerald-300"><CheckCircle2 size={16}/>{notice}</div>}

        {busy ? <div className="flex items-center justify-center gap-3 px-6 py-16 text-sm text-zinc-500"><Loader2 className="animate-spin" size={19}/>Loading saved analyses…</div>
        : filteredItems.length === 0 ? <div className="px-6 py-16 text-center"><Database className="mx-auto mb-3 text-zinc-600" size={30}/><p className="font-medium text-zinc-300">{query ? 'No matching records' : 'No saved analyses yet'}</p><p className="mt-2 text-sm text-zinc-600">{query ? 'Try another filename or analysis type.' : 'Completed analyses will appear here once history saving is connected.'}</p></div>
        : <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-white/[0.025] text-xs text-zinc-500"><tr>{['Dataset','Analysis type','Rows','Columns','Created','Actions'].map(label => <th key={label} className="px-5 py-4 font-medium">{label}</th>)}</tr></thead><tbody>{filteredItems.map(item => <tr key={item.id} className="border-t border-white/[0.05] hover:bg-white/[0.02]"><td className="max-w-[260px] px-5 py-4"><div className="flex items-center gap-3"><div className="rounded-lg bg-violet-500/10 p-2 text-violet-300"><FileText size={17}/></div><div className="min-w-0"><p className="truncate font-medium text-zinc-200">{item.filename}</p><p className="mt-1 truncate text-[10px] text-zinc-600">{item.id}</p></div></div></td><td className="px-5 py-4"><span className="rounded-lg border border-violet-500/20 bg-violet-500/10 px-2.5 py-1.5 text-xs text-violet-200">{labelize(item.analysis_type)}</span></td><td className="px-5 py-4 tabular-nums text-zinc-300">{item.row_count?.toLocaleString() ?? '—'}</td><td className="px-5 py-4 tabular-nums text-zinc-300">{item.column_count?.toLocaleString() ?? '—'}</td><td className="px-5 py-4 text-xs text-zinc-400"><span className="flex items-center gap-1.5"><Clock3 size={13}/>{new Date(item.created_at).toLocaleString()}</span></td><td className="px-5 py-4"><div className="flex items-center gap-2"><button onClick={() => void openDetails(item)} className="rounded-lg border border-white/10 p-2 text-zinc-400 hover:bg-white/5 hover:text-white" title="View details" aria-label="View details"><Eye size={15}/></button><button onClick={() => setDeletingId(item.id)} className="rounded-lg border border-red-500/20 p-2 text-red-300 hover:bg-red-500/10" title="Delete record" aria-label="Delete record"><Trash2 size={15}/></button></div></td></tr>)}</tbody></table></div>}

        <div className="flex flex-col gap-3 border-t border-white/[0.06] px-5 py-4 sm:flex-row sm:items-center sm:justify-between"><p className="text-xs text-zinc-500">{total === 0 ? '0 records' : `Showing ${offset + 1}–${Math.min(offset + items.length, total)} of ${total}`}</p><div className="flex items-center gap-2"><button onClick={() => { setBusy(true); void loadHistory(Math.max(0, offset - PAGE_SIZE)) }} disabled={busy || offset === 0} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-300 hover:bg-white/5 disabled:opacity-30"><ChevronLeft size={14}/>Previous</button><span className="px-2 text-xs text-zinc-500">Page {page} of {pages}</span><button onClick={() => { setBusy(true); void loadHistory(offset + PAGE_SIZE) }} disabled={busy || offset + PAGE_SIZE >= total} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-300 hover:bg-white/5 disabled:opacity-30">Next<ChevronRight size={14}/></button></div></div>
      </section>
    </main>

    {selected && <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 p-4" onMouseDown={event => { if (event.target === event.currentTarget) setSelected(null) }}><section role="dialog" aria-modal="true" aria-labelledby="history-detail-title" className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-white/10 bg-[#11111b] shadow-2xl"><div className="flex items-center justify-between border-b border-white/[0.06] p-5"><div><p className="text-xs tracking-wider text-violet-300">SAVED RECORD</p><h2 id="history-detail-title" className="mt-1 font-semibold">Analysis details</h2></div><button onClick={() => setSelected(null)} className="rounded-lg p-2 text-zinc-400 hover:bg-white/5" aria-label="Close details"><X size={18}/></button></div><div className="space-y-4 p-5"><div><p className="text-xs text-zinc-500">Dataset</p><p className="mt-1 break-all text-sm text-zinc-200">{selected.filename}</p></div><div className="grid gap-3 sm:grid-cols-2"><div className="rounded-xl bg-white/[0.03] p-3"><p className="text-xs text-zinc-500">Analysis type</p><p className="mt-1 text-sm text-zinc-200">{labelize(selected.analysis_type)}</p></div><div className="rounded-xl bg-white/[0.03] p-3"><p className="text-xs text-zinc-500">Created</p><p className="mt-1 text-sm text-zinc-200">{new Date(selected.created_at).toLocaleString()}</p></div><div className="rounded-xl bg-white/[0.03] p-3"><p className="text-xs text-zinc-500">Rows × columns</p><p className="mt-1 text-sm text-zinc-200">{selected.row_count?.toLocaleString() ?? '—'} × {selected.column_count?.toLocaleString() ?? '—'}</p></div><div className="rounded-xl bg-white/[0.03] p-3"><p className="text-xs text-zinc-500">Record ID</p><p className="mt-1 break-all text-xs text-zinc-300">{selected.id}</p></div></div>{selected.notes && <div><p className="text-xs text-zinc-500">Notes</p><p className="mt-1 text-sm text-zinc-300">{selected.notes}</p></div>}<div><p className="mb-2 text-xs font-semibold tracking-wider text-zinc-400">RESULT SUMMARY</p><pre className="max-h-72 overflow-auto rounded-xl border border-white/[0.06] bg-black/20 p-4 text-xs leading-6 text-emerald-200">{JSON.stringify(selected.summary, null, 2)}</pre></div></div></section></div>}

    {deletingId && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"><section role="alertdialog" aria-modal="true" aria-labelledby="delete-history-title" className="w-full max-w-md rounded-2xl border border-white/10 bg-[#11111b] p-6 shadow-2xl"><div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-red-500/10 text-red-300"><Trash2 size={20}/></div><h2 id="delete-history-title" className="font-semibold">Delete this history record?</h2><p className="mt-2 text-sm leading-6 text-zinc-500">This permanently removes the saved analysis metadata and summary. It does not delete your original dataset file.</p><div className="mt-6 flex justify-end gap-3"><button onClick={() => setDeletingId(null)} disabled={deleteBusy} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-zinc-300 hover:bg-white/5">Cancel</button><button onClick={() => void confirmDelete()} disabled={deleteBusy} className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-50">{deleteBusy && <Loader2 size={15} className="animate-spin"/>}Delete record</button></div></section></div>}
  </div>
}
