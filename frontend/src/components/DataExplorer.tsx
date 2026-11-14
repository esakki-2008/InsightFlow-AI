import { useMemo, useState } from 'react'
import {
  ArrowLeft,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Database,
  FileSpreadsheet,
  Filter,
  Loader2,
  Search,
  Sparkles,
  Table2,
  UploadCloud,
  X,
} from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'
type Row = Record<string, unknown>
type NumericStat = { count: number; mean: number | null; median: number | null; std: number | null; min: number | null; max: number | null }
type CategoryItem = { value: string; count: number }
interface Exploration {
  overview: { total_rows: number; total_columns: number; numeric_columns: number; categorical_columns: number; missing_values: number; duplicate_rows: number }
  columns: { name: string; dtype: string; missing: number }[]
  numeric_statistics: Record<string, NumericStat>
  categorical_statistics: Record<string, CategoryItem[]>
  outlier_counts_iqr: Record<string, number>
  correlation: Record<string, Record<string, number | null>>
  table: { rows: Row[]; page: number; page_size: number; total_rows: number; total_pages: number; search: string }
}
interface ExploreResponse { message: string; filename: string; exploration: Exploration }

const number = (value: number | null | undefined) =>
  value === null || value === undefined || !Number.isFinite(value)
    ? '—'
    : value.toLocaleString(undefined, { maximumFractionDigits: 2 })

function MetricCard({ label, value, note, accent = 'violet' }: { label: string; value: string; note: string; accent?: string }) {
  const tones: Record<string, string> = {
    violet: 'bg-violet-500/10 text-violet-300',
    sky: 'bg-sky-500/10 text-sky-300',
    emerald: 'bg-emerald-500/10 text-emerald-300',
    amber: 'bg-amber-500/10 text-amber-300',
  }
  return <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5">
    <p className="text-xs text-zinc-500">{label}</p>
    <p className="mt-3 text-2xl font-bold tracking-tight text-white">{value}</p>
    <p className={`mt-2 inline-flex rounded-md px-2 py-1 text-[10px] ${tones[accent]}`}>{note}</p>
  </div>
}

export default function DataExplorer({ onBack }: { onBack: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [data, setData] = useState<Exploration | null>(null)
  const [filename, setFilename] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [activeTab, setActiveTab] = useState<'table' | 'statistics' | 'categories' | 'correlation'>('table')

  const runExplore = async (nextPage = 1, nextSearch = search) => {
    if (!file) { setError('Choose a CSV or Excel file to explore.'); return }
    setBusy(true); setError('')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('page', String(nextPage))
      form.append('page_size', '25')
      form.append('search', nextSearch)
      const response = await fetch(`${API_URL}/api/v1/datasets/explore`, { method: 'POST', body: form })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Dataset exploration failed.')
      const payload = result as ExploreResponse
      setData(payload.exploration)
      setFilename(payload.filename)
      setPage(payload.exploration.table.page)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to explore this dataset.')
    } finally { setBusy(false) }
  }

  const columns = data?.table.rows.length ? Object.keys(data.table.rows[0]) : data?.columns.map(c => c.name) ?? []
  const numericEntries = Object.entries(data?.numeric_statistics ?? {})
  const outliers = Object.entries(data?.outlier_counts_iqr ?? {}).sort((a,b) => b[1]-a[1]).slice(0,12)
  const categoryEntries = Object.entries(data?.categorical_statistics ?? {})
  const correlationColumns = useMemo(() => Object.keys(data?.correlation ?? {}).slice(0, 15), [data])
  const correlationColor = (value: number | null) => {
    if (value === null || !Number.isFinite(value)) return 'rgba(148,163,184,.08)'
    const strength = Math.abs(value)
    return value >= 0
      ? `rgba(139,92,246,${0.10 + strength * 0.62})`
      : `rgba(14,165,233,${0.10 + strength * 0.62})`
  }

  const tabs = [
    { id: 'table' as const, label: 'Data table', icon: Table2 },
    { id: 'statistics' as const, label: 'Numeric stats', icon: BarChart3 },
    { id: 'categories' as const, label: 'Categories', icon: Filter },
    { id: 'correlation' as const, label: 'Correlation', icon: Sparkles },
  ]

  return <div className="min-h-screen bg-[#09090f] text-zinc-100">
    <header className="sticky top-0 z-20 border-b border-white/[0.06] bg-[#0d0d16]/95 backdrop-blur">
      <div className="mx-auto flex h-18 max-w-[1500px] items-center justify-between px-5 sm:px-8">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="rounded-xl border border-white/10 p-2 text-zinc-400 transition hover:bg-white/5 hover:text-white" aria-label="Back to overview"><ArrowLeft size={18}/></button>
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600"><Database size={21}/></div>
          <div><p className="font-semibold">InsightFlow AI</p><p className="text-[10px] tracking-[1.8px] text-zinc-500">DATA EXPLORER</p></div>
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-300 sm:flex"><span className="h-2 w-2 rounded-full bg-emerald-400"/>{data ? 'Analysis ready' : 'Explorer ready'}</div>
      </div>
    </header>

    <main className="mx-auto max-w-[1500px] space-y-7 px-5 py-8 sm:px-8 lg:py-10">
      <section className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div><p className="mb-2 flex items-center gap-2 text-xs font-semibold tracking-[2px] text-violet-300"><Sparkles size={14}/> PHASE 03 · EXPLORATORY DATA ANALYSIS</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Explore your data<span className="text-violet-400">.</span></h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-500">Inspect records, understand distributions, identify outliers, and discover relationships between numeric features.</p>
        </div>
        {data && <div className="text-xs text-zinc-500"><span className="text-zinc-300">{filename}</span><br/>Last analysis · {data.overview.total_rows.toLocaleString()} records</div>}
      </section>

      <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3"><div className="rounded-xl bg-violet-500/10 p-3 text-violet-300"><UploadCloud size={21}/></div><div><h2 className="font-semibold">Load a dataset</h2><p className="mt-1 text-xs text-zinc-500">CSV, XLSX or XLS · maximum 10 MB</p></div></div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="flex min-w-0 cursor-pointer items-center gap-3 rounded-xl border border-dashed border-white/15 bg-white/[0.02] px-4 py-3 hover:border-violet-400/50 sm:min-w-[330px]">
              <FileSpreadsheet className="shrink-0 text-violet-300" size={19}/>
              <span className="min-w-0 flex-1 truncate text-sm text-zinc-300">{file ? file.name : 'Choose a dataset file'}</span>
              {file && <button type="button" onClick={(event) => { event.preventDefault(); setFile(null); setData(null); setFilename('') }} className="text-zinc-500 hover:text-white" aria-label="Remove file"><X size={16}/></button>}
              <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={event => { setFile(event.target.files?.[0] ?? null); setData(null); setError(''); setPage(1) }}/>
            </label>
            <button onClick={() => runExplore(1, search)} disabled={!file || busy} className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40">
              {busy ? <><Loader2 size={17} className="animate-spin"/>Analyzing…</> : <><Sparkles size={17}/>Explore dataset</>}
            </button>
          </div>
        </div>
        {file && <p className="mt-3 text-xs text-zinc-500">{(file.size/1024).toFixed(1)} KB selected · Original file is not modified.</p>}
        {error && <p role="alert" className="mt-4 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-300">{error}</p>}
      </section>

      {data ? <>
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          <MetricCard label="Total rows" value={number(data.overview.total_rows)} note="Dataset records" />
          <MetricCard label="Total columns" value={number(data.overview.total_columns)} note="Features" accent="sky"/>
          <MetricCard label="Numeric columns" value={number(data.overview.numeric_columns)} note="Quantitative" accent="emerald"/>
          <MetricCard label="Categorical" value={number(data.overview.categorical_columns)} note="Qualitative" accent="amber"/>
          <MetricCard label="Missing values" value={number(data.overview.missing_values)} note="Null cells" accent="sky"/>
          <MetricCard label="Duplicate rows" value={number(data.overview.duplicate_rows)} note="Exact duplicates" accent="amber"/>
        </section>

        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5 sm:p-6">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
            <div><h2 className="font-semibold">Analysis workspace</h2><p className="mt-1 text-xs text-zinc-500">Switch between the dataset views</p></div>
            <div className="flex flex-wrap gap-2">{tabs.map(tab => { const Icon = tab.icon; return <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition ${activeTab === tab.id ? 'bg-violet-600 text-white' : 'border border-white/10 text-zinc-400 hover:bg-white/5 hover:text-white'}`}><Icon size={14}/>{tab.label}</button> })}</div>
          </div>

          {activeTab === 'table' && <div className="mt-6">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div><h3 className="text-sm font-semibold">Dataset records</h3><p className="mt-1 text-xs text-zinc-500">Showing {data.table.rows.length} of {data.table.total_rows.toLocaleString()} matching records</p></div>
              <form onSubmit={event => { event.preventDefault(); runExplore(1, search) }} className="flex gap-2">
                <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3"><Search size={15} className="text-zinc-500"/><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search all columns…" className="w-44 bg-transparent py-2 text-xs text-white outline-none placeholder:text-zinc-600 sm:w-60"/></div>
                <button disabled={busy} className="rounded-lg bg-white/10 px-4 text-xs text-zinc-200 hover:bg-white/15 disabled:opacity-40">Search</button>
              </form>
            </div>
            <div className="overflow-auto rounded-xl border border-white/[0.06]"><table className="w-full min-w-max text-left text-xs">
              <thead className="sticky top-0 bg-[#1a1a27] text-zinc-400"><tr><th className="px-4 py-3 font-medium">#</th>{columns.map(column => <th key={column} className="max-w-56 px-4 py-3 font-medium">{column}</th>)}</tr></thead>
              <tbody>{data.table.rows.map((row,index) => <tr key={index} className="border-t border-white/[0.05] text-zinc-300 hover:bg-white/[0.025]"><td className="px-4 py-3 text-zinc-600">{(page-1)*data.table.page_size+index+1}</td>{columns.map(column => <td key={column} title={String(row[column] ?? '')} className="max-w-56 truncate px-4 py-3">{row[column] === null || row[column] === undefined ? <span className="text-zinc-600">—</span> : String(row[column])}</td>)}</tr>)}</tbody>
            </table></div>
            <div className="mt-4 flex flex-col justify-between gap-3 text-xs text-zinc-500 sm:flex-row sm:items-center"><span>Page {data.table.page} of {Math.max(data.table.total_pages,1)} · 25 rows per page</span><div className="flex items-center gap-2"><button onClick={() => runExplore(Math.max(1,page-1))} disabled={page <= 1 || busy} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 hover:bg-white/5 disabled:opacity-30"><ChevronLeft size={14}/>Previous</button><button onClick={() => runExplore(Math.min(data.table.total_pages,page+1))} disabled={page >= data.table.total_pages || busy} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 hover:bg-white/5 disabled:opacity-30">Next<ChevronRight size={14}/></button></div></div>
          </div>}

          {activeTab === 'statistics' && <div className="mt-6">
            <div className="mb-4"><h3 className="font-semibold">Numeric feature statistics</h3><p className="mt-1 text-xs text-zinc-500">Count, central tendency, spread, minimum and maximum</p></div>
            <div className="overflow-auto rounded-xl border border-white/[0.06]"><table className="w-full min-w-[760px] text-left text-xs"><thead className="bg-[#1a1a27] text-zinc-400"><tr>{['Feature','Count','Mean','Median','Std. deviation','Minimum','Maximum'].map(h=><th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr></thead><tbody>{numericEntries.map(([name,stat])=><tr key={name} className="border-t border-white/[0.05] text-zinc-300"><td className="px-4 py-3 font-medium text-zinc-100">{name}</td><td className="px-4 py-3">{number(stat.count)}</td><td className="px-4 py-3">{number(stat.mean)}</td><td className="px-4 py-3">{number(stat.median)}</td><td className="px-4 py-3">{number(stat.std)}</td><td className="px-4 py-3">{number(stat.min)}</td><td className="px-4 py-3">{number(stat.max)}</td></tr>)}</tbody></table></div>
          </div>}

          {activeTab === 'categories' && <div className="mt-6 grid gap-5 lg:grid-cols-2">
            {categoryEntries.length ? categoryEntries.map(([column,items]) => { const total = items.reduce((sum,item)=>sum+item.count,0); const max = Math.max(...items.map(item=>item.count),1); return <div key={column} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5"><h3 className="font-semibold">{column}</h3><p className="mt-1 text-xs text-zinc-500">Top values · {total.toLocaleString()} records represented</p><div className="mt-5 space-y-4">{items.map(item=><div key={item.value}><div className="mb-2 flex justify-between gap-3 text-xs"><span className="truncate text-zinc-300">{item.value}</span><span className="shrink-0 text-zinc-500">{item.count.toLocaleString()} · {((item.count/Math.max(total,1))*100).toFixed(1)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-violet-500" style={{width:`${(item.count/max)*100}%`}}/></div></div>)}</div></div> }) : <div className="rounded-xl border border-white/[0.06] p-8 text-center text-sm text-zinc-500 lg:col-span-2">No categorical columns were detected in this dataset.</div>}
          </div>}

          {activeTab === 'correlation' && <div className="mt-6">
            <div className="mb-4"><h3 className="font-semibold">Correlation matrix</h3><p className="mt-1 text-xs text-zinc-500">Pearson correlation for up to 15 numeric features · Purple = positive, blue = negative</p></div>
            {correlationColumns.length ? <div className="overflow-auto rounded-xl border border-white/[0.06]"><table className="text-center text-[10px]"><thead><tr><th className="sticky left-0 bg-[#1a1a27] px-3 py-3 text-left text-zinc-500">Feature</th>{correlationColumns.map(name=><th key={name} className="max-w-24 px-2 py-3 font-medium text-zinc-400"><span className="block w-20 truncate" title={name}>{name}</span></th>)}</tr></thead><tbody>{correlationColumns.map(row=><tr key={row}><th className="sticky left-0 max-w-48 bg-[#1a1a27] px-3 py-2 text-left font-medium text-zinc-300"><span className="block w-40 truncate" title={row}>{row}</span></th>{correlationColumns.map(column=>{const value=data.correlation[row]?.[column] ?? null; return <td key={column} title={`${row} × ${column}: ${value === null ? 'not available' : value.toFixed(3)}`} style={{backgroundColor:correlationColor(value)}} className="min-w-16 border border-[#11111b] px-2 py-3 text-zinc-100">{value === null ? '—' : value.toFixed(2)}</td>})}</tr>)}</tbody></table></div> : <p className="rounded-xl border border-white/[0.06] p-8 text-center text-sm text-zinc-500">Correlation data is not available.</p>}
          </div>}
        </section>

        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5 sm:p-6">
          <div className="mb-5 flex items-center gap-3"><div className="rounded-xl bg-amber-500/10 p-3 text-amber-300"><BarChart3 size={20}/></div><div><h2 className="font-semibold">Potential outliers</h2><p className="mt-1 text-xs text-zinc-500">Top 12 numeric features by IQR outlier count</p></div></div>
          {outliers.length ? <div className="grid gap-3 md:grid-cols-2">{outliers.map(([name,count])=><div key={name} className="rounded-xl border border-white/[0.05] bg-white/[0.02] p-4"><div className="mb-2 flex justify-between gap-3 text-xs"><span className="truncate text-zinc-300">{name}</span><span className="shrink-0 font-semibold text-amber-300">{count.toLocaleString()}</span></div><div className="h-2 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-amber-400" style={{width:`${(count/Math.max(data.overview.total_rows,1))*100}%`}}/></div></div>)}</div> : <p className="text-sm text-zinc-500">No outlier counts available.</p>}
        </section>
      </> : <section className="rounded-2xl border border-dashed border-white/10 bg-[#11111b]/60 px-6 py-16 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-500/10 text-violet-300"><Database size={25}/></div>
        <h2 className="text-lg font-semibold">Your analysis starts here</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-zinc-500">Upload a dataset to see its structure, summary metrics, searchable records, feature statistics, category distributions, correlations, and outlier counts.</p>
        <div className="mt-5 inline-flex items-center gap-2 text-xs text-zinc-600"><CircleHelp size={14}/>Your original dataset remains unchanged</div>
      </section>}
      <footer className="border-t border-white/5 pt-5 text-xs text-zinc-600">InsightFlow AI · Data Explorer · Exploratory analysis only</footer>
    </main>
  </div>
}
