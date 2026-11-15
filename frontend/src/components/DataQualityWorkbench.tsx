import { useMemo, useState } from 'react'
import { ArrowLeft, AlertCircle, CheckCircle2, FileSpreadsheet, Loader2, ShieldCheck, UploadCloud, AlertTriangle, Info } from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'

type ColumnProfile = {
  name: string
  data_type: string
  total_values: number
  missing_values: number
  missing_percentage: number
  unique_values: number
  unique_percentage: number
  is_constant: boolean
  is_identifier_like: boolean
}
type Finding = { severity: 'critical' | 'warning' | 'info' | 'success'; title: string; detail: string; recommendation: string }
type QualityReport = {
  summary: {
    quality_score: number; quality_grade: string; total_rows: number; total_columns: number; total_cells: number
    missing_cells: number; completeness_percentage: number; duplicate_rows: number; duplicate_percentage: number
    constant_columns: number; high_missing_columns: number; high_cardinality_columns: number
  }
  scoring_method: { description: string; note: string }
  columns: ColumnProfile[]
  findings: Finding[]
}

const number = (value: number) => value.toLocaleString()
const percent = (value: number) => `${value.toFixed(2)}%`

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><p className="text-xs text-zinc-500">{label}</p><p className="mt-3 text-2xl font-bold text-white">{value}</p><p className="mt-2 text-xs text-zinc-600">{note}</p></div>
}

export default function DataQualityWorkbench({ onBack }: { onBack: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [report, setReport] = useState<QualityReport | null>(null)
  const [filename, setFilename] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const runReport = async () => {
    if (!file) { setError('Choose a CSV or Excel dataset first.'); return }
    setBusy(true); setError(''); setReport(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const response = await fetch(`${API_URL}/api/v1/datasets/quality`, { method: 'POST', body: form })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Unable to generate the report.')
      setReport(result.report as QualityReport)
      setFilename(result.filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to generate the data quality report.')
    } finally { setBusy(false) }
  }

  const sortedColumns = useMemo(() => [...(report?.columns ?? [])].sort((a, b) => b.missing_percentage - a.missing_percentage), [report])
  const gradeColor = report && report.summary.quality_score >= 75 ? 'text-emerald-300' : report && report.summary.quality_score >= 60 ? 'text-amber-300' : 'text-red-300'

  return <div className="min-h-screen bg-[#09090f] text-zinc-100">
    <header className="sticky top-0 z-20 border-b border-white/[0.06] bg-[#0d0d16]/95 backdrop-blur">
      <div className="mx-auto flex h-18 max-w-[1500px] items-center gap-3 px-5 sm:px-8">
        <button onClick={onBack} className="rounded-xl border border-white/10 p-2 text-zinc-400 hover:bg-white/5 hover:text-white" aria-label="Back to overview"><ArrowLeft size={18}/></button>
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600"><ShieldCheck size={21}/></div>
        <div><p className="font-semibold">InsightFlow AI</p><p className="text-[10px] tracking-[1.8px] text-zinc-500">DATA QUALITY CENTER</p></div>
      </div>
    </header>
    <main className="mx-auto max-w-[1500px] space-y-7 px-5 py-8 sm:px-8 lg:py-10">
      <section><p className="mb-2 text-xs font-semibold tracking-[2px] text-violet-300">DATA TRUST & VALIDATION</p><h1 className="text-3xl font-bold sm:text-4xl">Data quality report<span className="text-violet-400">.</span></h1><p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-500">Assess completeness, duplicates, constant fields, unique values, and column-level quality risks before analysis or model training.</p></section>
      <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3"><div className="rounded-xl bg-violet-500/10 p-3 text-violet-300"><UploadCloud size={21}/></div><div><h2 className="font-semibold">Profile a dataset</h2><p className="mt-1 text-xs text-zinc-500">CSV, XLSX or XLS · maximum 10 MB</p></div></div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="flex min-w-0 cursor-pointer items-center gap-3 rounded-xl border border-dashed border-white/15 bg-white/[0.02] px-4 py-3 hover:border-violet-400/50 sm:min-w-[330px]"><FileSpreadsheet className="shrink-0 text-violet-300" size={19}/><span className="min-w-0 flex-1 truncate text-sm text-zinc-300">{file ? file.name : 'Choose a dataset file'}</span><input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={event => { setFile(event.target.files?.[0] ?? null); setReport(null); setError('') }}/></label>
            <button onClick={runReport} disabled={!file || busy} className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40">{busy ? <><Loader2 size={17} className="animate-spin"/>Generating…</> : <><ShieldCheck size={17}/>Generate report</>}</button>
          </div>
        </div>
        {file && <p className="mt-3 text-xs text-zinc-500">{(file.size / 1024).toFixed(1)} KB selected · Original file remains unchanged.</p>}
        {error && <p role="alert" className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-300"><AlertCircle size={16}/>{error}</p>}
      </section>
      {report && <>
        <section className="rounded-2xl border border-violet-500/20 bg-[#11111b] p-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div><p className="text-xs tracking-wider text-zinc-500">OVERALL DATA QUALITY SCORE</p><div className="mt-2 flex items-baseline gap-3"><span className={`text-5xl font-bold ${gradeColor}`}>{report.summary.quality_score}</span><span className="text-sm text-zinc-500">/ 100</span></div><p className={`mt-2 text-sm font-semibold ${gradeColor}`}>{report.summary.quality_grade}</p></div>
            <div className="min-w-[220px] flex-1 sm:max-w-sm"><div className="mb-2 flex justify-between text-xs text-zinc-500"><span>Quality index</span><span>{report.summary.quality_score}%</span></div><div className="h-3 overflow-hidden rounded-full bg-white/[0.07]"><div className="h-full rounded-full bg-violet-500" style={{ width: `${report.summary.quality_score}%` }}/></div><p className="mt-3 text-xs leading-5 text-zinc-500">Heuristic screening score. Review the findings and scoring method before making data decisions.</p></div>
          </div>
          <p className="mt-4 border-t border-white/[0.06] pt-4 text-xs text-zinc-500">{filename}</p>
        </section>
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Completeness" value={percent(report.summary.completeness_percentage)} note={`${number(report.summary.missing_cells)} missing cells`}/>
          <Metric label="Duplicate rows" value={number(report.summary.duplicate_rows)} note={percent(report.summary.duplicate_percentage) + ' of records'}/>
          <Metric label="Constant columns" value={number(report.summary.constant_columns)} note="One or fewer distinct values"/>
          <Metric label="High-missing columns" value={number(report.summary.high_missing_columns)} note="At least 30% missing values"/>
        </section>
        <section className="grid gap-3 sm:grid-cols-3"><Metric label="Rows" value={number(report.summary.total_rows)} note="Records profiled"/><Metric label="Columns" value={number(report.summary.total_columns)} note="Fields profiled"/><Metric label="High-cardinality fields" value={number(report.summary.high_cardinality_columns)} note="At least 95% unique values"/></section>
        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5">
          <h2 className="font-semibold">Quality findings & recommendations</h2><p className="mt-1 text-xs text-zinc-500">Review each issue before cleaning or model training.</p>
          <div className="mt-4 space-y-3">{report.findings.map((finding, index) => { const Icon = finding.severity === 'critical' || finding.severity === 'warning' ? AlertTriangle : finding.severity === 'success' ? CheckCircle2 : Info; const tone = finding.severity === 'critical' ? 'text-red-300 bg-red-500/10 border-red-500/20' : finding.severity === 'warning' ? 'text-amber-300 bg-amber-500/10 border-amber-500/20' : finding.severity === 'success' ? 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20' : 'text-sky-300 bg-sky-500/10 border-sky-500/20'; return <div key={finding.title + index} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4"><div className="flex items-center gap-2"><Icon size={16} className={tone.split(' ')[0]}/><h3 className="text-sm font-semibold text-zinc-200">{finding.title}</h3></div><p className="mt-2 text-sm text-zinc-400">{finding.detail}</p><p className="mt-2 text-xs leading-5 text-zinc-500">Recommendation: {finding.recommendation}</p></div> })}</div>
        </section>
        <section className="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#11111b]">
          <div className="border-b border-white/[0.06] p-5"><h2 className="font-semibold">Column-level quality profile</h2><p className="mt-1 text-xs text-zinc-500">Sorted by missing percentage, highest first.</p></div>
          <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-xs"><thead className="bg-white/[0.025] text-zinc-500"><tr>{['Column','Data type','Missing','Missing %','Unique values','Unique %','Flags'].map(item => <th key={item} className="px-4 py-3 font-medium">{item}</th>)}</tr></thead><tbody>{sortedColumns.map(column => <tr key={column.name} className="border-t border-white/[0.05]"><td className="px-4 py-3 font-medium text-zinc-200">{column.name}</td><td className="px-4 py-3 text-zinc-400">{column.data_type}</td><td className="px-4 py-3 text-zinc-300">{number(column.missing_values)}</td><td className={`px-4 py-3 ${column.missing_percentage >= 30 ? 'text-red-300' : column.missing_percentage > 0 ? 'text-amber-300' : 'text-emerald-300'}`}>{percent(column.missing_percentage)}</td><td className="px-4 py-3 text-zinc-300">{number(column.unique_values)}</td><td className="px-4 py-3 text-zinc-400">{percent(column.unique_percentage)}</td><td className="px-4 py-3 text-zinc-500">{[column.is_constant && 'Constant', column.is_identifier_like && 'Identifier-like', column.missing_percentage >= 30 && 'High missingness'].filter(Boolean).join(' · ') || '—'}</td></tr>)}</tbody></table></div>
        </section>
        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><h2 className="font-semibold">How the score is calculated</h2><p className="mt-2 text-sm leading-6 text-zinc-400">{report.scoring_method.description}</p><p className="mt-2 text-xs leading-5 text-zinc-600">{report.scoring_method.note}</p></section>
      </>}
    </main>
  </div>
}
