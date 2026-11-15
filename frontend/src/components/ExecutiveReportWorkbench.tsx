import { useState } from 'react'
import { ArrowLeft, FileSpreadsheet, FileText, Loader2, AlertCircle, Sparkles, Download, ShieldCheck, Printer } from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'
type Finding = { area: string; priority: string; title: string; detail: string; recommendation: string }
type Report = {
  filename: string
  summary: string
  kpis: Record<string, number>
  findings: Finding[]
  recommendations: string[]
  limitations: string[]
  generation: string
}

export default function ExecutiveReportWorkbench({ onBack }: { onBack: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [historyStatus, setHistoryStatus] = useState('')

  const generate = async () => {
    if (!file) { setError('Choose a CSV or Excel dataset first.'); return }
    setBusy(true); setError(''); setHistoryStatus(''); setReport(null)
    try {
      const body = new FormData(); body.append('file', file)
      const response = await fetch(`${API_URL}/api/v1/datasets/executive-report`, { method: 'POST', body })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Unable to generate the report.')
      const generatedReport = payload.report as Report
      setReport(generatedReport)
      try {
        const historyResponse = await fetch(`${API_URL}/api/v1/history`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: generatedReport.filename || file.name,
            analysis_type: 'executive_report',
            row_count: generatedReport.kpis.rows,
            column_count: generatedReport.kpis.columns,
            summary: {
              quality_score: generatedReport.kpis.quality_score,
              completeness_percentage: generatedReport.kpis.completeness_percentage,
              missing_cells: generatedReport.kpis.missing_cells,
              duplicate_rows: generatedReport.kpis.duplicate_rows,
              insights_count: generatedReport.kpis.insights_count,
              correlation_pairs: generatedReport.kpis.correlation_pairs,
              group_comparisons: generatedReport.kpis.group_comparisons,
              findings_count: generatedReport.findings.length,
              recommendations_count: generatedReport.recommendations.length
            },
            notes: 'Automatically saved after successful executive report generation.'
          })
        })
        if (!historyResponse.ok) throw new Error('History save failed')
        setHistoryStatus('This executive report was automatically saved to Analysis History.')
      } catch {
        setHistoryStatus('Report generated, but it could not be saved to Analysis History. Check that the backend is running, then try again.')
      }
    } catch (e) { setError(e instanceof Error ? e.message : 'Report generation failed.') }
    finally { setBusy(false) }
  }

  const exportPdf = () => window.print()

  const download = () => {
    if (!report) return
    const escapeCsv = (value: unknown) => '"' + String(value ?? '').replaceAll('"', '""') + '"'
    const rows = [
      ['InsightFlow AI - Executive Report'], ['Dataset', report.filename], ['Executive summary', report.summary], [],
      ['KEY METRICS'], ['Metric', 'Value'], ...Object.entries(report.kpis),
      [], ['FINDINGS'], ['Area', 'Priority', 'Finding', 'Evidence', 'Recommendation'],
      ...report.findings.map(x => [x.area, x.priority, x.title, x.detail, x.recommendation]),
      [], ['RECOMMENDATIONS'], ...report.recommendations.map((x, i) => [i + 1, x]),
      [], ['LIMITATIONS'], ...report.limitations.map(x => [x]),
      [], ['Generation method', report.generation],
    ]
    const csv = rows.map(row => row.map(escapeCsv).join(',')).join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a'); link.href = url; link.download = 'insightflow_executive_report.csv'; link.click(); URL.revokeObjectURL(url)
  }

  return <div className="executive-report-print min-h-screen bg-[#09090f] text-zinc-100">
    <style>{`
      @page { size: A4; margin: 15mm; }
      @media print {
        body { background: #fff !important; }
        .no-print { display: none !important; }
        .executive-report-print, .executive-report-print main { min-height: 0 !important; background: #fff !important; color: #111827 !important; }
        .executive-report-print * { color: #111827 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        .executive-report-print section, .executive-report-print article, .executive-report-print [class*="rounded-2xl"], .executive-report-print [class*="rounded-xl"] { background: #fff !important; border-color: #d1d5db !important; box-shadow: none !important; }
        .executive-report-print main { max-width: none !important; padding: 0 !important; gap: 16px !important; }
        .executive-report-print header { display: none !important; }
        .executive-report-print h1 { font-size: 24pt !important; }
        .executive-report-print h2 { break-after: avoid; }
        .executive-report-print article, .executive-report-print section { break-inside: avoid; }
        .executive-report-print p, .executive-report-print li { orphans: 2; widows: 2; }
      }
    `}</style>
    <header className="no-print flex h-20 items-center justify-between border-b border-white/5 px-6 lg:px-10">
      <div><p className="text-xs text-zinc-500">Workspace / Executive Report</p><h1 className="mt-1 text-lg font-semibold">AI Executive Report Generator</h1></div>
      <button onClick={onBack} className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-sm text-zinc-300 hover:bg-white/5"><ArrowLeft size={16}/> Back</button>
    </header>
    <main className="mx-auto max-w-7xl space-y-6 p-6 lg:p-10">
      <section className="no-print rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/[0.10] to-[#11111b] p-6 sm:p-8">
        <div className="flex items-center gap-2 text-sm font-medium tracking-wide text-violet-300"><Sparkles size={17}/> EXECUTIVE INTELLIGENCE</div>
        <h2 className="mt-3 text-3xl font-bold sm:text-4xl">From raw data to clear decisions.</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-400">Generate an executive-ready summary with dataset KPIs, evidence-backed findings, recommended next steps, and analytical limitations. Calculations run locally in the InsightFlow backend.</p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 rounded-xl border border-dashed border-violet-400/30 bg-black/20 px-4 py-3"><FileSpreadsheet size={20} className="shrink-0 text-violet-300"/><span className="truncate text-sm text-zinc-200">{file?.name ?? 'Choose a dataset file'}<span className="mt-1 block text-xs text-zinc-500">CSV, XLSX or XLS · Maximum 10 MB</span></span><input className="sr-only" type="file" accept=".csv,.xlsx,.xls" disabled={busy} onChange={e=>{setFile(e.target.files?.[0]??null);setReport(null);setError('')}}/></label>
          <button onClick={generate} disabled={!file||busy} className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold hover:bg-violet-500 disabled:opacity-40">{busy?<><Loader2 size={17} className="animate-spin"/>Generating…</>:<><FileText size={17}/>Generate report</>}</button>
        </div>
        {historyStatus&&<p role="status" className="no-print mt-4 rounded-xl border border-violet-500/20 bg-violet-500/5 p-3 text-sm text-violet-200">{historyStatus}</p>}
      {error&&<p role="alert" className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300"><AlertCircle size={16}/>{error}</p>}
      </section>
      {!report&&<div className="rounded-2xl border border-dashed border-white/10 px-6 py-16 text-center"><FileText size={30} className="mx-auto mb-3 text-zinc-600"/><p className="font-medium text-zinc-300">Your executive report will appear here</p><p className="mt-2 text-sm text-zinc-600">Upload a dataset and generate a report.</p></div>}
      {report&&<>
        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs uppercase tracking-wider text-violet-300">Executive summary</p><h2 className="mt-2 text-xl font-semibold">{report.filename}</h2></div><div className="no-print flex flex-wrap gap-2"><button onClick={exportPdf} className="inline-flex items-center gap-2 rounded-xl border border-violet-400/30 bg-violet-500/10 px-4 py-2 text-sm font-semibold text-violet-200 hover:bg-violet-500/20"><Printer size={16}/>Export PDF</button><button onClick={download} className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2 text-sm hover:bg-white/5"><Download size={16}/>Export CSV report</button></div></div><p className="mt-4 text-sm leading-7 text-zinc-300">{report.summary}</p></section>
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{Object.entries(report.kpis).map(([key,value])=><div key={key} className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><p className="text-xs capitalize text-zinc-500">{key.replaceAll('_',' ')}</p><p className="mt-3 text-2xl font-bold tabular-nums">{typeof value==='number'?value.toLocaleString():value}</p></div>)}</section>
        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-6"><h2 className="font-semibold">Key findings</h2><p className="mt-1 text-xs text-zinc-500">Observations with supporting evidence</p><div className="mt-4 space-y-3">{report.findings.map((x,i)=><article key={i} className="rounded-xl border border-white/[0.06] p-4"><div className="flex flex-wrap justify-between gap-2"><p className="text-xs text-violet-300">{x.area}</p><span className="text-xs capitalize text-zinc-500">{x.priority}</span></div><h3 className="mt-2 font-semibold">{x.title}</h3><p className="mt-2 text-sm leading-6 text-zinc-400">{x.detail}</p><p className="mt-3 text-sm leading-6 text-zinc-300"><strong>Suggested action:</strong> {x.recommendation}</p></article>)}</div>{report.findings.length===0&&<p className="mt-4 text-sm text-zinc-500">No additional findings were generated.</p>}</section>
        <section className="rounded-2xl border border-emerald-500/15 bg-[#11111b] p-6"><h2 className="font-semibold text-emerald-300">Recommended next steps</h2><ol className="mt-4 list-decimal space-y-3 pl-5 text-sm leading-6 text-zinc-300">{report.recommendations.map((x,i)=><li key={i}>{x}</li>)}</ol></section>
        <section className="rounded-2xl border border-amber-500/15 bg-[#11111b] p-6"><h2 className="font-semibold text-amber-200">Limitations & methodology</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-xs leading-5 text-zinc-400">{report.limitations.map((x,i)=><li key={i}>{x}</li>)}</ul><p className="mt-4 flex items-center gap-2 text-xs text-zinc-500"><ShieldCheck size={15}/>{report.generation}</p></section>
      </>}
    </main>
  </div>
}
