import { useMemo, useState } from 'react'
import { ArrowLeft, BarChart3, Database, FileSpreadsheet, Loader2, Sparkles, UploadCloud, ShieldCheck, AlertCircle } from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'
type NumericStat = { count: number; mean: number | null; median: number | null; std: number | null; min: number | null; max: number | null }
type CategoryItem = { value: string; count: number }
interface Exploration {
  overview: { total_rows: number; total_columns: number; numeric_columns: number; categorical_columns: number; missing_values: number; duplicate_rows: number }
  columns: { name: string; dtype: string; missing: number }[]
  numeric_statistics: Record<string, NumericStat>
  categorical_statistics: Record<string, CategoryItem[]>
  outlier_counts_iqr: Record<string, number>
  correlation: Record<string, Record<string, number | null>>
}
interface ExploreResponse { message: string; filename: string; exploration: Exploration }

const fmt = (value: number | null | undefined) => value === null || value === undefined || !Number.isFinite(value) ? '—' : value.toLocaleString(undefined, { maximumFractionDigits: 2 })

function StatCard({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><p className="text-xs text-zinc-500">{label}</p><p className="mt-3 text-2xl font-bold text-white">{value}</p><p className="mt-2 text-xs text-zinc-600">{note}</p></div>
}

export default function AnalyticsWorkbench({ onBack }: { onBack: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [filename, setFilename] = useState('')
  const [data, setData] = useState<Exploration | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const runAnalytics = async () => {
    if (!file) { setError('Choose a CSV or Excel dataset first.'); return }
    setBusy(true); setError(''); setData(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('page', '1')
      form.append('page_size', '25')
      form.append('search', '')
      const response = await fetch(`${API_URL}/api/v1/datasets/explore`, { method: 'POST', body: form })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Analytics could not be generated.')
      const payload = result as ExploreResponse
      setData(payload.exploration)
      setFilename(payload.filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to analyze this dataset.')
    } finally { setBusy(false) }
  }

  const identifierColumns = useMemo(() => (data?.columns ?? []).filter(column => /(^id$|(^|[_\\s-])id($|[_\\s-])|uuid|guid|identifier|serial|roll[_\\s-]?no|student[_\\s-]?no|customer[_\\s-]?no|account[_\\s-]?no)/i.test(column.name)).map(column => column.name), [data])
  const categories = useMemo(() => Object.entries(data?.categorical_statistics ?? {}).filter(([name]) => !identifierColumns.includes(name)).slice(0, 4), [data, identifierColumns])
  const numeric = useMemo(() => Object.entries(data?.numeric_statistics ?? {}).filter(([, stat]) => stat.mean !== null).sort((a, b) => Math.abs(b[1].mean ?? 0) - Math.abs(a[1].mean ?? 0)).slice(0, 8), [data])
  const outliers = useMemo(() => Object.entries(data?.outlier_counts_iqr ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 8), [data])
  const correlations = useMemo(() => {
    const matrix = data?.correlation ?? {}
    const names = Object.keys(matrix)
    const pairs: { left: string; right: string; value: number }[] = []
    names.forEach((left, i) => names.slice(i + 1).forEach(right => {
      const value = matrix[left]?.[right]
      if (value !== null && value !== undefined && Number.isFinite(value) && Math.abs(value) >= 0.7) pairs.push({ left, right, value })
    }))
    return pairs.sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).slice(0, 8)
  }, [data])

  return <div className="min-h-screen bg-[#09090f] text-zinc-100">
    <header className="sticky top-0 z-20 border-b border-white/[0.06] bg-[#0d0d16]/95 backdrop-blur">
      <div className="mx-auto flex h-18 max-w-[1500px] items-center gap-3 px-5 sm:px-8">
        <button onClick={onBack} className="rounded-xl border border-white/10 p-2 text-zinc-400 hover:bg-white/5 hover:text-white" aria-label="Back to overview"><ArrowLeft size={18}/></button>
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600"><BarChart3 size={21}/></div>
        <div><p className="font-semibold">InsightFlow AI</p><p className="text-[10px] tracking-[1.8px] text-zinc-500">ANALYTICS OVERVIEW</p></div>
      </div>
    </header>
    <main className="mx-auto max-w-[1500px] space-y-7 px-5 py-8 sm:px-8 lg:py-10">
      <section><p className="mb-2 flex items-center gap-2 text-xs font-semibold tracking-[2px] text-violet-300"><Sparkles size={14}/> DATA-DRIVEN ANALYTICS</p><h1 className="text-3xl font-bold sm:text-4xl">Analytics overview<span className="text-violet-400">.</span></h1><p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-500">Generate a statistical overview of your dataset, review data quality, compare distributions, and identify strong numeric relationships.</p></section>
      <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3"><div className="rounded-xl bg-violet-500/10 p-3 text-violet-300"><UploadCloud size={21}/></div><div><h2 className="font-semibold">Analyze a dataset</h2><p className="mt-1 text-xs text-zinc-500">CSV, XLSX or XLS · maximum 10 MB</p></div></div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="flex min-w-0 cursor-pointer items-center gap-3 rounded-xl border border-dashed border-white/15 bg-white/[0.02] px-4 py-3 hover:border-violet-400/50 sm:min-w-[330px]"><FileSpreadsheet className="shrink-0 text-violet-300" size={19}/><span className="min-w-0 flex-1 truncate text-sm text-zinc-300">{file ? file.name : 'Choose a dataset file'}</span><input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={event => { setFile(event.target.files?.[0] ?? null); setData(null); setError('') }}/></label>
            <button onClick={runAnalytics} disabled={!file || busy} className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40">{busy ? <><Loader2 size={17} className="animate-spin"/>Analyzing…</> : <><Sparkles size={17}/>Generate analytics</>}</button>
          </div>
        </div>
        {file && <p className="mt-3 text-xs text-zinc-500">{(file.size / 1024).toFixed(1)} KB selected · Your original file is not modified.</p>}
        {error && <p role="alert" className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-300"><AlertCircle size={16}/>{error}</p>}
      </section>
      {!data && <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.015] px-6 py-16 text-center"><Database className="mx-auto mb-3 text-zinc-600" size={30}/><p className="font-medium text-zinc-300">Your analytics will appear here</p><p className="mt-2 text-sm text-zinc-600">Select a dataset and generate an analysis to see real statistics.</p></div>}
      {data && <>
        <div className="flex items-center gap-2 text-xs text-zinc-500"><ShieldCheck size={15} className="text-emerald-400"/> Analysis generated from the selected file · <span className="text-zinc-300">{filename}</span></div>
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
          <StatCard label="Total rows" value={fmt(data.overview.total_rows)} note="Dataset records"/><StatCard label="Total columns" value={fmt(data.overview.total_columns)} note="Features"/><StatCard label="Numeric columns" value={fmt(data.overview.numeric_columns)} note="Quantitative"/><StatCard label="Categorical columns" value={fmt(Math.max(0, data.overview.categorical_columns - Object.keys(data.categorical_statistics ?? {}).filter(name => identifierColumns.includes(name)).length))} note="Excludes identifiers"/><StatCard label="Identifier columns" value={fmt(identifierColumns.length)} note="Not charted as categories"/><StatCard label="Missing values" value={fmt(data.overview.missing_values)} note="Null cells"/><StatCard label="Duplicate rows" value={fmt(data.overview.duplicate_rows)} note="Exact duplicates"/>
        </section>
        {identifierColumns.length > 0 && <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><h3 className="font-semibold">Identifier columns excluded</h3><p className="mt-1 text-xs text-zinc-500">These fields identify records rather than describe meaningful category groups, so they are excluded from categorical distributions.</p><div className="mt-3 flex flex-wrap gap-2">{identifierColumns.map(name => <span key={name} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-zinc-300">{name}</span>)}</div></section>}
        <section className="grid gap-4 xl:grid-cols-2">
          <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><h3 className="font-semibold">Numeric feature summary</h3><p className="mt-1 text-xs text-zinc-500">Mean values for selected numeric columns</p><div className="mt-5 space-y-4">{numeric.map(([name, stat]) => { const max = Math.max(...numeric.map(([, item]) => Math.abs(item.mean ?? 0)), 1); return <div key={name}><div className="mb-1 flex justify-between gap-3 text-xs"><span className="truncate text-zinc-300">{name}</span><span className="text-zinc-400">{fmt(stat.mean)}</span></div><div className="h-2 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-violet-500" style={{ width: `${Math.abs(stat.mean ?? 0) / max * 100}%` }}/></div></div> })}{!numeric.length && <p className="text-sm text-zinc-500">No numeric statistics available.</p>}</div></div>
          <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><h3 className="font-semibold">Potential outliers</h3><p className="mt-1 text-xs text-zinc-500">Features ranked by IQR outlier count</p><div className="mt-5 space-y-4">{outliers.map(([name, count]) => <div key={name}><div className="mb-1 flex justify-between gap-3 text-xs"><span className="truncate text-zinc-300">{name}</span><span className="text-amber-300">{count.toLocaleString()}</span></div><div className="h-2 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-amber-400" style={{ width: `${count / Math.max(outliers[0]?.[1] ?? 1, 1) * 100}%` }}/></div></div>)}{!outliers.length && <p className="text-sm text-zinc-500">No outlier data available.</p>}</div></div>
          <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><h3 className="font-semibold">Categorical distributions</h3><p className="mt-1 text-xs text-zinc-500">Most frequent values per categorical feature</p><div className="mt-5 space-y-5">{categories.map(([column, items]) => { const total = items.reduce((sum, item) => sum + item.count, 0); return <div key={column}><div className="mb-2 text-sm font-medium text-zinc-200">{column}</div><div className="space-y-2">{items.slice(0, 5).map(item => <div key={item.value}><div className="mb-1 flex justify-between gap-3 text-xs"><span className="truncate text-zinc-400">{item.value}</span><span className="text-zinc-500">{item.count.toLocaleString()} · ${(item.count / Math.max(total, 1) * 100).toFixed(1)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-sky-400" style={{ width: `${item.count / Math.max(total, 1) * 100}%` }}/></div></div>)}</div></div> })}{!categories.length && <p className="text-sm text-zinc-500">No categorical distributions available.</p>}</div></div>
          <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><h3 className="font-semibold">Strong correlations</h3><p className="mt-1 text-xs text-zinc-500">Numeric pairs with absolute Pearson correlation ≥ 0.70</p><div className="mt-5 space-y-3">{correlations.map(pair => <div key={pair.left + pair.right} className="flex items-center justify-between gap-4 rounded-xl bg-white/[0.025] p-3"><div className="min-w-0"><p className="truncate text-xs text-zinc-200">{pair.left}</p><p className="mt-1 truncate text-xs text-zinc-500">with {pair.right}</p></div><span className={`shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-semibold ${pair.value >= 0 ? 'bg-violet-500/10 text-violet-300' : 'bg-sky-500/10 text-sky-300'}`}>{pair.value.toFixed(3)}</span></div>)}{!correlations.length && <p className="text-sm text-zinc-500">No strong numeric correlations found.</p>}</div></div>
        </section>
        <p className="text-xs leading-5 text-zinc-600">These are descriptive statistics. Outliers and correlations indicate patterns in the selected data; they do not establish causes. This analysis is generated on demand and is not saved as permanent dataset history.</p>
      </>}
    </main>
  </div>
}
