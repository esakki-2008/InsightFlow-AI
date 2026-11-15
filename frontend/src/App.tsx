
import { useEffect, useState } from 'react'
import DataExplorer from './components/DataExplorer'
import AnalyticsWorkbench from './components/AnalyticsWorkbench'
import DataQualityWorkbench from './components/DataQualityWorkbench'
import StatisticalWorkbench from './components/StatisticalWorkbench'
import MLWorkbench from './components/MLWorkbench'
import InsightsWorkbench from './components/InsightsWorkbench'
import ExecutiveReportWorkbench from './components/ExecutiveReportWorkbench'
import DatasetQAWorkbench from './components/DatasetQAWorkbench'
import HistoryWorkbench from './components/HistoryWorkbench'
import DatasetRegistryWorkbench from './components/DatasetRegistryWorkbench'
import ModelRegistryWorkbench from './components/ModelRegistryWorkbench'
import {
  Activity,
  AlertCircle,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  LayoutDashboard,
  MessageSquareText,
  History,
  Loader2,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sparkles,
  Upload,
  WandSparkles,
  X,
} from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'

interface DatasetInfo {
  filename: string
  file_size_kb: number
  file_type: string
  total_rows: number
  total_columns: number
  columns: string[]
  data_types: Record<string, string>
  missing_values: Record<string, number>
  total_missing_values: number
  duplicate_rows: number
}

interface UploadResponse {
  message: string
  dataset: DatasetInfo
}

interface CleaningSummary {
  original_rows: number
  preview_rows: number
  original_columns: number
  cleaned_columns: number
  duplicate_rows_detected: number
  missing_values_before: number
  missing_values_after: number
}

interface RenamedColumn {
  old_name: string
  new_name: string
}

interface FilledColumn {
  column: string
  missing_values_filled: number
  method: string
}

interface UnresolvedColumn {
  column: string
  missing_values: number
  reason: string
}

interface CleaningPreview {
  summary: CleaningSummary
  operations: {
    renamed_columns: RenamedColumn[]
    duplicates_to_remove: number
    filled_columns: FilledColumn[]
    unresolved_columns: UnresolvedColumn[]
  }
  column_types: {
    numeric: string[]
    categorical: string[]
  }
  preview: {
    columns: string[]
    rows: Record<string, unknown>[]
  }
}

interface CleaningPreviewResponse {
  message: string
  filename: string
  cleaning_preview: CleaningPreview
}

function App() {
  const [activePage, setActivePage] = useState('Overview')
  const [savedModelCount, setSavedModelCount] = useState<number | null>(null)
  const [modelsLoadError, setModelsLoadError] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [dataset, setDataset] = useState<DatasetInfo | null>(() => {
    try {
      const saved = localStorage.getItem('insightflow_dashboard_dataset')
      return saved ? (JSON.parse(saved) as DatasetInfo) : null
    } catch {
      return null
    }
  })
  const [analysisCount, setAnalysisCount] = useState(() => {
    try {
      return Number(localStorage.getItem('insightflow_dashboard_analysis_count') || 0)
    } catch {
      return 0
    }
  })

  const [recentDatasets, setRecentDatasets] = useState<DatasetInfo[]>(() => {
    try {
      const saved = localStorage.getItem('insightflow_recent_datasets')
      if (saved) return JSON.parse(saved) as DatasetInfo[]
      const latest = localStorage.getItem('insightflow_dashboard_dataset')
      return latest ? [JSON.parse(latest) as DatasetInfo] : []
    } catch {
      return []
    }
  })

  useEffect(() => {
    let cancelled = false
    const loadSavedModels = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/ml/models`)
        if (!response.ok) throw new Error('Unable to load saved models')
        const result = await response.json()
        if (!cancelled) {
          setSavedModelCount(Number(result.total_models) || 0)
          setModelsLoadError('')
        }
      } catch {
        if (!cancelled) {
          setSavedModelCount(null)
          setModelsLoadError('Backend unavailable')
        }
      }
    }
    loadSavedModels()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    try {
      if (dataset) {
        localStorage.setItem('insightflow_dashboard_dataset', JSON.stringify(dataset))
      } else {
        localStorage.removeItem('insightflow_dashboard_dataset')
      }
    } catch {
      // Dashboard remains usable if browser storage is unavailable.
    }
  }, [dataset])

  useEffect(() => {
    try {
      localStorage.setItem('insightflow_dashboard_analysis_count', String(analysisCount))
    } catch {
      // Dashboard remains usable if browser storage is unavailable.
    }
  }, [analysisCount])

  useEffect(() => {
    try {
      localStorage.setItem('insightflow_recent_datasets', JSON.stringify(recentDatasets))
    } catch {
      // Recent dataset history is optional when browser storage is unavailable.
    }
  }, [recentDatasets])

  const [cleaningPreview, setCleaningPreview] =
    useState<CleaningPreview | null>(null)
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [previewError, setPreviewError] = useState('')

  const [isApplying, setIsApplying] = useState(false)
  const [applyError, setApplyError] = useState('')
  const [cleaningSuccess, setCleaningSuccess] = useState('')

  const navigation = [
    { label: 'Overview', icon: LayoutDashboard },
    { label: 'Data Explorer', icon: Database },
    { label: 'Analytics', icon: BarChart3 },
    { label: 'Data Quality', icon: ShieldCheck },
    { label: 'Statistical Analytics', icon: Activity },
    { label: 'Machine Learning', icon: BrainCircuit },
    { label: 'AI Insights', icon: Sparkles },
    { label: 'Executive Report', icon: FileText },
    { label: 'Dataset Q&A', icon: MessageSquareText },
    { label: 'Analysis History', icon: History },
    { label: 'Dataset Registry', icon: Database },
    { label: 'ML Model Registry', icon: BrainCircuit },
  ]

  const handleFileChange = (file: File | null) => {
    setSelectedFile(file)
    setUploadError('')
    setDataset(null)
    setCleaningPreview(null)
    setPreviewError('')
    setApplyError('')
    setCleaningSuccess('')
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a dataset first.')
      return
    }

    setIsUploading(true)
    setUploadError('')
    setDataset(null)
    setCleaningPreview(null)
    setPreviewError('')
    setApplyError('')
    setCleaningSuccess('')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch(
        `${API_URL}/api/v1/datasets/upload`,
        {
          method: 'POST',
          body: formData,
        },
      )

      const result = await response.json()

      if (!response.ok) {
        throw new Error(
          result.detail || 'Unable to upload the dataset.',
        )
      }

      const uploadResult = result as UploadResponse
      setDataset(uploadResult.dataset)
      setRecentDatasets((items) => [
        uploadResult.dataset,
        ...items.filter((item) => item.filename !== uploadResult.dataset.filename),
      ].slice(0, 10))
      setAnalysisCount((count) => count + 1)
    } catch (error) {
      setUploadError(
        error instanceof Error
          ? error.message
          : 'Something went wrong during upload.',
      )
    } finally {
      setIsUploading(false)
    }
  }

  const handleCleaningPreview = async () => {
    if (!selectedFile) {
      setPreviewError('Please select a dataset first.')
      return
    }

    setIsPreviewing(true)
    setPreviewError('')
    setApplyError('')
    setCleaningSuccess('')
    setCleaningPreview(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch(
        `${API_URL}/api/v1/datasets/clean/preview`,
        {
          method: 'POST',
          body: formData,
        },
      )

      const result = await response.json()

      if (!response.ok) {
        throw new Error(
          result.detail || 'Unable to generate the cleaning preview.',
        )
      }

      const previewResult = result as CleaningPreviewResponse
      setCleaningPreview(previewResult.cleaning_preview)
      setAnalysisCount((count) => count + 1)

      // Save compact cleaning metadata only; never persist uploaded rows.
      try {
        const summary = previewResult.cleaning_preview.summary
        const historyResponse = await fetch(`${API_URL}/api/v1/history`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: previewResult.filename || selectedFile.name,
            analysis_type: 'Data Cleaning',
            row_count: summary.original_rows,
            column_count: summary.original_columns,
            summary: {
              rows_after_cleaning: summary.preview_rows,
              columns_after_cleaning: summary.cleaned_columns,
              duplicate_rows_detected: summary.duplicate_rows_detected,
              missing_values_before: summary.missing_values_before,
              missing_values_after: summary.missing_values_after,
              renamed_columns: previewResult.cleaning_preview.operations.renamed_columns.length,
              duplicate_rows_to_remove: previewResult.cleaning_preview.operations.duplicates_to_remove,
              columns_filled: previewResult.cleaning_preview.operations.filled_columns.length,
              unresolved_columns: previewResult.cleaning_preview.operations.unresolved_columns.length,
            },
            notes: 'Cleaning preview metadata saved automatically. Original dataset rows were not stored.',
          }),
        })
        if (!historyResponse.ok) {
          throw new Error('History save request failed')
        }
        setCleaningSuccess('Cleaning preview generated and saved to Analysis History.')
      } catch {
        setCleaningSuccess('Cleaning preview generated. Analysis History could not be saved; you can still use the preview.')
      }
    } catch (error) {
      setPreviewError(
        error instanceof Error
          ? error.message
          : 'Something went wrong while generating the preview.',
      )
    } finally {
      setIsPreviewing(false)
    }
  }

  const handleApplyCleaning = async () => {
    if (!selectedFile || !cleaningPreview) {
      setApplyError('Generate a cleaning preview before applying cleaning.')
      return
    }

    const approved = window.confirm(
      'Apply the proposed cleaning operations and download a new CSV file? Your original file will not be changed.',
    )

    if (!approved) return

    setIsApplying(true)
    setApplyError('')
    setCleaningSuccess('')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('confirm', 'true')

      const response = await fetch(
        `${API_URL}/api/v1/datasets/clean/apply`,
        {
          method: 'POST',
          body: formData,
        },
      )

      if (!response.ok) {
        let message = 'Unable to apply the cleaning operations.'

        try {
          const result = await response.json()
          message = result.detail || message
        } catch {
          // Keep the default error message if the response is not JSON.
        }

        throw new Error(message)
      }

      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')

      link.href = downloadUrl
      link.download = 'cleaned_dataset.csv'
      document.body.appendChild(link)
      link.click()
      link.remove()

      window.URL.revokeObjectURL(downloadUrl)

      const rowsRemoved =
        response.headers.get('X-Cleaning-Rows-Removed')

      setCleaningSuccess(
        rowsRemoved !== null
          ? `Cleaned CSV downloaded successfully. ${rowsRemoved} duplicate rows removed.`
          : 'Cleaned CSV downloaded successfully.',
      )
    } catch (error) {
      setApplyError(
        error instanceof Error
          ? error.message
          : 'Something went wrong while applying cleaning.',
      )
    } finally {
      setIsApplying(false)
    }
  }

  const formatPreviewValue = (value: unknown): string => {
    if (value === null || value === undefined) return '—'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  const dataCompleteness = dataset
    ? Math.max(
        0,
        Math.round(
          (1 -
            dataset.total_missing_values /
              Math.max(dataset.total_rows * dataset.total_columns, 1)) *
            100,
        ),
      )
    : null

  const stats = [
    {
      label: 'Datasets Analyzed',
      value: String(recentDatasets.length),
      change: recentDatasets.length ? 'Saved in this browser' : 'Upload a dataset to begin',
      icon: Database,
    },
    {
      label: 'Analyses Completed',
      value: String(analysisCount),
      change: analysisCount ? 'Inspections and cleaning previews this session' : 'No analyses in this session yet',
      icon: Activity,
    },
    {
      label: 'ML Models Trained',
      value: savedModelCount === null ? '—' : String(savedModelCount),
      change: modelsLoadError || (savedModelCount === null ? 'Connecting to backend' : 'Saved model bundles on backend'),
      icon: BrainCircuit,
    },
    {
      label: 'Data Completeness',
      value: dataCompleteness === null ? '—' : `${dataCompleteness}%`,
      change: dataset ? 'Based on non-missing cells' : 'Awaiting dataset',
      icon: ShieldCheck,
    },
  ]

  if (activePage === 'Data Explorer') {
    return <DataExplorer onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'Analytics') {
    return <AnalyticsWorkbench onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'Data Quality') {
    return <DataQualityWorkbench onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'Statistical Analytics') {
    return <StatisticalWorkbench onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'Machine Learning') {
    return <MLWorkbench onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'AI Insights') {
    return <InsightsWorkbench onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'Executive Report') {
    return <ExecutiveReportWorkbench onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'Dataset Q&A') {
    return <DatasetQAWorkbench onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'Analysis History') {
    return <HistoryWorkbench onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'Dataset Registry') {
    return <DatasetRegistryWorkbench onBack={() => setActivePage('Overview')} />
  }

  if (activePage === 'ML Model Registry') {
    return <ModelRegistryWorkbench onBack={() => setActivePage('Overview')} />
  }

  return (
    <div className="min-h-screen bg-[#09090f] text-zinc-100">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-white/5 bg-[#0d0d16] lg:flex lg:flex-col">
        <div className="flex h-20 items-center gap-3 border-b border-white/5 px-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 shadow-lg shadow-violet-600/20">
            <BrainCircuit size={23} />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">InsightFlow AI</h1>
            <p className="text-[10px] tracking-[2px] text-zinc-500">
              INTELLIGENT ANALYTICS
            </p>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-7 [scrollbar-width:thin]">
          <p className="mb-4 px-3 text-[10px] font-semibold tracking-[2px] text-zinc-600">
            WORKSPACE
          </p>
          <nav className="space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => {
                    if (item.label === 'Overview' || item.label === 'Data Explorer' || item.label === 'Analytics' || item.label === 'Data Quality' || item.label === 'Statistical Analytics' || item.label === 'Machine Learning' || item.label === 'AI Insights' || item.label === 'Executive Report' || item.label === 'Dataset Q&A' || item.label === 'Analysis History' || item.label === 'Dataset Registry' || item.label === 'ML Model Registry') {
                      setActivePage(item.label)
                    }
                  }}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition ${
                    activePage === item.label
                      ? 'border border-violet-500/20 bg-violet-600/15 font-medium text-violet-300'
                      : 'text-zinc-500 hover:bg-white/[0.03] hover:text-zinc-300'
                  }`}
                >
                  <Icon size={18} />
                  {item.label}
                  {item.label === 'Data Explorer' && (
                    <span className="ml-auto rounded-md bg-violet-500/15 px-2 py-0.5 text-[10px] text-violet-300">NEW</span>
                  )}
                </button>
              )
            })}
          </nav>
        </div>

        <div className="mt-auto border-t border-white/5 p-4">
          <div className="flex items-center gap-3 rounded-xl p-3 text-sm text-zinc-400">
            <Settings size={18} />
            Settings
          </div>
          <div className="mt-3 rounded-xl border border-violet-500/15 bg-violet-500/5 p-4">
            <Sparkles className="mb-2 text-violet-400" size={20} />
            <p className="text-sm font-semibold text-white">
              AI-powered analytics
            </p>
            <p className="mt-1 text-xs leading-relaxed text-zinc-500">
              Your intelligent data workspace is being built.
            </p>
          </div>
        </div>
      </aside>

      <main className="min-h-screen lg:ml-64">
        <header className="flex h-20 items-center justify-between border-b border-white/5 px-6 lg:px-10">
          <div>
            <p className="text-xs text-zinc-500">Workspace / Overview</p>
            <h2 className="mt-1 text-lg font-semibold">Dashboard</h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-xs text-emerald-400 sm:flex">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              Platform initialized
            </div>
            <button className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-600 text-xs font-bold">
                I
              </div>
              <span className="hidden sm:inline">Workspace</span>
              <ChevronDown size={15} className="text-zinc-500" />
            </button>
          </div>
        </header>

        <div className="mx-auto max-w-7xl space-y-8 p-6 lg:p-10">
          <section className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
            <div>
              <p className="mb-2 text-sm font-medium text-violet-400">
                <Sparkles className="mr-2 inline" size={15} />
                INTELLIGENT DATA ANALYST
              </p>
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Welcome to <span className="text-violet-400">InsightFlow.</span>
              </h2>
              <p className="mt-3 max-w-xl text-sm leading-relaxed text-zinc-500">
                Explore your data, discover hidden patterns, and transform
                information into meaningful insights.
              </p>
            </div>
            <div className="text-xs text-zinc-500">
              {dataset
                ? 'Your dataset has been inspected successfully.'
                : 'Your workspace is ready for its first dataset.'}
            </div>
          </section>

          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {stats.map((stat) => {
              const Icon = stat.icon
              return (
                <div
                  key={stat.label}
                  className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-zinc-500">{stat.label}</p>
                    <div className="rounded-xl bg-violet-500/10 p-2.5 text-violet-400">
                      <Icon size={19} />
                    </div>
                  </div>
                  <h3 className="mt-5 text-3xl font-bold">{stat.value}</h3>
                  <p className="mt-2 text-xs text-zinc-600">{stat.change}</p>
                </div>
              )
            })}
          </section>

          <section className="grid gap-6 xl:grid-cols-5">
            <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-6 xl:col-span-3">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">Upload your dataset</h3>
                  <p className="mt-1 text-xs text-zinc-500">
                    Start your first data analysis
                  </p>
                </div>
                <div className="rounded-xl bg-violet-500/10 p-3 text-violet-400">
                  <FileSpreadsheet size={21} />
                </div>
              </div>

              <label className="flex min-h-52 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-violet-500/30 bg-violet-500/[0.03] p-6 text-center transition hover:border-violet-400 hover:bg-violet-500/[0.07]">
                <div className="mb-4 rounded-2xl bg-violet-600/15 p-4 text-violet-400">
                  <Upload size={25} />
                </div>
                <p className="text-sm font-semibold text-zinc-200">
                  Click to select a dataset
                </p>
                <p className="mt-2 text-xs text-zinc-500">
                  Supported formats: CSV, XLSX, XLS · Maximum 10 MB
                </p>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="hidden"
                  disabled={isUploading || isPreviewing || isApplying}
                  onChange={(event) =>
                    handleFileChange(event.target.files?.[0] ?? null)
                  }
                />
              </label>

              {selectedFile && (
                <div className="mt-4 flex items-center justify-between rounded-xl border border-violet-500/20 bg-violet-500/5 p-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <FileSpreadsheet
                      className="shrink-0 text-violet-400"
                      size={19}
                    />
                    <div className="min-w-0">
                      <p className="truncate text-sm text-zinc-200">
                        {selectedFile.name}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {(selectedFile.size / 1024).toFixed(1)} KB · Selected
                      </p>
                    </div>
                  </div>
                  <button
                    disabled={isUploading || isPreviewing || isApplying}
                    onClick={() => handleFileChange(null)}
                    className="rounded-lg p-2 text-zinc-500 hover:bg-white/5 hover:text-white disabled:opacity-40"
                    aria-label="Remove selected file"
                  >
                    <X size={17} />
                  </button>
                </div>
              )}

              <button
                onClick={handleUpload}
                disabled={!selectedFile || isUploading || isPreviewing || isApplying}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {isUploading ? (
                  <>
                    <Loader2 size={17} className="animate-spin" />
                    Inspecting dataset...
                  </>
                ) : (
                  <>
                    <Upload size={17} />
                    Upload and inspect dataset
                  </>
                )}
              </button>

              {uploadError && (
                <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-400">
                  <AlertCircle size={18} className="mt-0.5 shrink-0" />
                  <p>{uploadError}</p>
                </div>
              )}

              {dataset && (
                <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <CheckCircle2 size={19} />
                    <p className="text-sm font-semibold">
                      Dataset inspected successfully
                    </p>
                  </div>
                  <p className="mt-2 break-all text-xs text-zinc-400">
                    {dataset.filename}
                  </p>
                  <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <div>
                      <p className="text-xl font-bold text-white">
                        {dataset.total_rows.toLocaleString()}
                      </p>
                      <p className="text-xs text-zinc-500">Rows</p>
                    </div>
                    <div>
                      <p className="text-xl font-bold text-white">
                        {dataset.total_columns}
                      </p>
                      <p className="text-xs text-zinc-500">Columns</p>
                    </div>
                    <div>
                      <p className="text-xl font-bold text-white">
                        {dataset.total_missing_values}
                      </p>
                      <p className="text-xs text-zinc-500">Missing values</p>
                    </div>
                    <div>
                      <p className="text-xl font-bold text-white">
                        {dataset.duplicate_rows}
                      </p>
                      <p className="text-xs text-zinc-500">Duplicate rows</p>
                    </div>
                  </div>
                </div>
              )}

              <p className="mt-4 text-[11px] leading-relaxed text-zinc-600">
                Your selected file is sent to your local FastAPI backend for
                inspection. Files are not permanently stored yet.
              </p>
            </div>

            <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-6 xl:col-span-2">
              <h3 className="font-semibold">Analysis overview</h3>
              <p className="mt-1 text-xs text-zinc-500">
                Your dataset inspection activity
              </p>

              {dataset ? (
                <div className="mt-6 space-y-4">
                  <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-zinc-200">Latest dataset inspection</p>
                        <p className="mt-1 max-w-xs truncate text-xs text-zinc-500">{dataset.filename}</p>
                      </div>
                      <CheckCircle2 className="shrink-0 text-emerald-400" size={20} />
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-3">
                      <div><p className="text-xl font-bold">{dataset.total_rows.toLocaleString()}</p><p className="text-xs text-zinc-500">Rows</p></div>
                      <div><p className="text-xl font-bold">{dataset.total_columns}</p><p className="text-xs text-zinc-500">Columns</p></div>
                      <div><p className="text-xl font-bold">{dataset.total_missing_values.toLocaleString()}</p><p className="text-xs text-zinc-500">Missing cells</p></div>
                      <div><p className="text-xl font-bold">{dataset.duplicate_rows.toLocaleString()}</p><p className="text-xs text-zinc-500">Duplicate rows</p></div>
                    </div>
                  </div>
                  <div>
                    <div className="mb-2 flex justify-between text-xs"><span className="text-zinc-400">Data completeness</span><span className="font-semibold text-emerald-400">{dataCompleteness}%</span></div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${dataCompleteness}%` }} /></div>
                  </div>
                  <p className="text-[11px] text-zinc-600">Session activity only. Dataset history and ML model totals will be connected after persistent storage is implemented.</p>
                </div>
              ) : (
                <div className="mt-8 flex min-h-44 flex-col items-center justify-center rounded-xl border border-white/5 bg-white/[0.015] text-center">
                  <div className="mb-3 rounded-full bg-zinc-800/70 p-4 text-zinc-500"><BarChart3 size={27} /></div>
                  <p className="text-sm font-medium text-zinc-400">No analysis yet</p>
                  <p className="mt-2 max-w-52 text-xs leading-relaxed text-zinc-600">Upload a dataset to see real inspection statistics and completeness.</p>
                </div>
              )}
            </div>
          </section>

          {/* Data cleaning workflow */}
          <section className="rounded-2xl border border-violet-500/20 bg-[#11111b] p-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <div className="rounded-xl bg-violet-500/10 p-2.5 text-violet-400">
                    <WandSparkles size={21} />
                  </div>
                  <h3 className="text-lg font-semibold">Data Cleaning Studio</h3>
                </div>
                <p className="mt-2 text-sm text-zinc-500">
                  Prepare your dataset before analytics and machine learning.
                </p>
              </div>

              <span className="w-fit rounded-full border border-violet-500/20 bg-violet-500/10 px-3 py-1.5 text-xs text-violet-300">
                Phase 2 · Data preparation
              </span>
            </div>

            {!dataset && (
              <div className="mt-6 rounded-xl border border-white/5 bg-white/[0.02] p-5 text-center">
                <Database className="mx-auto mb-3 text-zinc-600" size={25} />
                <p className="text-sm text-zinc-400">
                  Upload and inspect a dataset to begin cleaning.
                </p>
              </div>
            )}

            {dataset && (
              <>
                <div className="mt-6 rounded-xl border border-white/5 bg-white/[0.02] p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex min-w-0 items-center gap-3">
                      <FileSpreadsheet className="shrink-0 text-violet-400" size={22} />
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-zinc-200">
                          {dataset.filename}
                        </p>
                        <p className="mt-1 text-xs text-zinc-500">
                          Ready for cleaning preview
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={handleCleaningPreview}
                      disabled={!selectedFile || isPreviewing || isApplying}
                      className="flex items-center justify-center gap-2 rounded-xl border border-violet-500/30 bg-violet-500/10 px-4 py-2.5 text-sm font-semibold text-violet-300 transition hover:bg-violet-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {isPreviewing ? (
                        <>
                          <Loader2 size={16} className="animate-spin" />
                          Generating preview...
                        </>
                      ) : (
                        <>
                          <RefreshCw size={16} />
                          Generate cleaning preview
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {previewError && (
                  <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-400">
                    <AlertCircle size={18} className="mt-0.5 shrink-0" />
                    <p>{previewError}</p>
                  </div>
                )}

                {cleaningPreview && (
                  <div className="mt-6 space-y-6">
                    <div className="flex items-center gap-2 text-emerald-400">
                      <CheckCircle2 size={19} />
                      <p className="text-sm font-semibold">
                        Cleaning preview generated successfully
                      </p>
                    </div>

                    {/* Summary cards */}
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      {[
                        {
                          label: 'Original rows',
                          value: cleaningPreview.summary.original_rows,
                        },
                        {
                          label: 'Rows after cleaning',
                          value: cleaningPreview.summary.preview_rows,
                        },
                        {
                          label: 'Duplicate rows',
                          value: cleaningPreview.summary.duplicate_rows_detected,
                        },
                        {
                          label: 'Missing values before',
                          value: cleaningPreview.summary.missing_values_before,
                        },
                        {
                          label: 'Missing values after',
                          value: cleaningPreview.summary.missing_values_after,
                        },
                        {
                          label: 'Original columns',
                          value: cleaningPreview.summary.original_columns,
                        },
                        {
                          label: 'Numeric columns',
                          value: cleaningPreview.column_types.numeric.length,
                        },
                        {
                          label: 'Categorical columns',
                          value: cleaningPreview.column_types.categorical.length,
                        },
                      ].map((item) => (
                        <div
                          key={item.label}
                          className="rounded-xl border border-white/5 bg-white/[0.025] p-4"
                        >
                          <p className="text-xs text-zinc-500">{item.label}</p>
                          <p className="mt-2 text-2xl font-bold text-white">
                            {item.value.toLocaleString()}
                          </p>
                        </div>
                      ))}
                    </div>

                    {/* Operations */}
                    <div className="grid gap-4 lg:grid-cols-2">
                      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-5">
                        <h4 className="font-semibold text-zinc-200">
                          Proposed cleaning operations
                        </h4>
                        <div className="mt-4 space-y-4 text-sm">
                          <div>
                            <p className="text-zinc-400">
                              Duplicate rows to remove
                            </p>
                            <p className="mt-1 font-semibold text-violet-300">
                              {cleaningPreview.operations.duplicates_to_remove}
                            </p>
                          </div>

                          <div>
                            <p className="text-zinc-400">
                              Column names to normalize
                            </p>
                            {cleaningPreview.operations.renamed_columns.some(
                              (item) => item.old_name !== item.new_name,
                            ) ? (
                              <ul className="mt-2 space-y-2">
                                {cleaningPreview.operations.renamed_columns
                                  .filter(
                                    (item) => item.old_name !== item.new_name,
                                  )
                                  .map(
                                  (item, index) => (
                                    <li
                                      key={`${item.old_name}-${index}`}
                                      className="rounded-lg bg-white/[0.03] p-2 text-xs"
                                    >
                                      <code className="whitespace-pre-wrap text-zinc-400">
                                        {JSON.stringify(item.old_name)}
                                      </code>
                                      <span className="mx-2 text-violet-400">→</span>
                                      <code className="whitespace-pre-wrap text-emerald-300">
                                        {JSON.stringify(item.new_name)}
                                      </code>
                                    </li>
                                  ),
                                )}
                              </ul>
                            ) : (
                              <p className="mt-1 text-xs text-zinc-600">
                                No column-name changes needed.
                              </p>
                            )}
                          </div>

                          <div>
                            <p className="text-zinc-400">
                              Missing values to fill
                            </p>
                            {cleaningPreview.operations.filled_columns.length > 0 ? (
                              <ul className="mt-2 space-y-2">
                                {cleaningPreview.operations.filled_columns.map(
                                  (item, index) => (
                                    <li
                                      key={`${item.column}-${index}`}
                                      className="rounded-lg bg-white/[0.03] p-2 text-xs text-zinc-300"
                                    >
                                      <span className="font-medium text-white">
                                        {item.column}
                                      </span>
                                      <span className="text-zinc-500">
                                        {' '}· {item.missing_values_filled} values
                                        {' '}· {item.method}
                                      </span>
                                    </li>
                                  ),
                                )}
                              </ul>
                            ) : (
                              <p className="mt-1 text-xs text-zinc-600">
                                No missing values need filling.
                              </p>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-5">
                        <h4 className="font-semibold text-zinc-200">
                          Column type detection
                        </h4>

                        <div className="mt-4">
                          <p className="text-xs font-medium text-violet-300">
                            Numeric columns ({cleaningPreview.column_types.numeric.length})
                          </p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {cleaningPreview.column_types.numeric.length > 0 ? (
                              cleaningPreview.column_types.numeric.map((column) => (
                                <span
                                  key={column}
                                  className="rounded-lg bg-violet-500/10 px-2.5 py-1.5 text-xs text-violet-300"
                                >
                                  {column}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-zinc-600">None detected</span>
                            )}
                          </div>
                        </div>

                        <div className="mt-5">
                          <p className="text-xs font-medium text-sky-300">
                            Categorical columns ({cleaningPreview.column_types.categorical.length})
                          </p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {cleaningPreview.column_types.categorical.length > 0 ? (
                              cleaningPreview.column_types.categorical.map((column) => (
                                <span
                                  key={column}
                                  className="rounded-lg bg-sky-500/10 px-2.5 py-1.5 text-xs text-sky-300"
                                >
                                  {column}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-zinc-600">None detected</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Unresolved values warning */}
                    {cleaningPreview.operations.unresolved_columns.length > 0 && (
                      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                        <div className="flex items-center gap-2 text-amber-300">
                          <AlertCircle size={18} />
                          <p className="text-sm font-semibold">
                            Some missing values could not be filled
                          </p>
                        </div>
                        <p className="mt-2 text-xs leading-relaxed text-zinc-400">
                          These columns may still contain missing values in the downloaded file.
                        </p>
                        <ul className="mt-3 space-y-2">
                          {cleaningPreview.operations.unresolved_columns.map(
                            (item, index) => (
                              <li
                                key={`${item.column}-${index}`}
                                className="text-xs text-amber-200/80"
                              >
                                <span className="font-semibold">{item.column}</span>
                                {' '}· {item.missing_values} missing values
                                {' '}· {item.reason}
                              </li>
                            ),
                          )}
                        </ul>
                      </div>
                    )}

                    {/* First 10 rows preview */}
                    <div className="overflow-hidden rounded-xl border border-white/5">
                      <div className="flex flex-col justify-between gap-2 border-b border-white/5 bg-white/[0.02] p-4 sm:flex-row sm:items-center">
                        <div>
                          <h4 className="font-semibold text-zinc-200">
                            Cleaned data preview
                          </h4>
                          <p className="mt-1 text-xs text-zinc-500">
                            First {cleaningPreview.preview.rows.length} rows after proposed cleaning
                          </p>
                        </div>
                        <span className="text-xs text-zinc-500">
                          {cleaningPreview.preview.columns.length} columns
                        </span>
                      </div>

                      {cleaningPreview.preview.rows.length > 0 ? (
                        <div className="max-h-[420px] overflow-auto">
                          <table className="w-full min-w-max text-left text-xs">
                            <thead className="sticky top-0 bg-[#1a1a27] text-zinc-400">
                              <tr>
                                <th className="px-4 py-3 font-medium">#</th>
                                {cleaningPreview.preview.columns.map((column) => (
                                  <th
                                    key={column}
                                    className="px-4 py-3 font-medium"
                                  >
                                    {column}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {cleaningPreview.preview.rows.map((row, rowIndex) => (
                                <tr
                                  key={rowIndex}
                                  className="border-t border-white/5 text-zinc-300 hover:bg-white/[0.02]"
                                >
                                  <td className="px-4 py-3 text-zinc-600">
                                    {rowIndex + 1}
                                  </td>
                                  {cleaningPreview.preview.columns.map((column) => (
                                    <td
                                      key={column}
                                      className="max-w-64 truncate px-4 py-3"
                                      title={formatPreviewValue(row[column])}
                                    >
                                      {formatPreviewValue(row[column])}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="p-5 text-sm text-zinc-500">
                          No preview rows were returned.
                        </p>
                      )}
                    </div>

                    {/* Approval and download */}
                    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-5">
                      <div className="flex items-start gap-3">
                        <ShieldCheck className="mt-0.5 shrink-0 text-emerald-400" size={22} />
                        <div>
                          <h4 className="font-semibold text-emerald-300">
                            Review and approve cleaning
                          </h4>
                          <p className="mt-1 text-xs leading-relaxed text-zinc-400">
                            Review the proposed operations and sample rows before approving.
                            Approval applies the backend cleaning rules and downloads a new CSV.
                            Your original file remains unchanged.
                          </p>
                        </div>
                      </div>

                      <button
                        onClick={handleApplyCleaning}
                        disabled={isApplying || isPreviewing}
                        className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
                      >
                        {isApplying ? (
                          <>
                            <Loader2 size={17} className="animate-spin" />
                            Applying cleaning...
                          </>
                        ) : (
                          <>
                            <Download size={17} />
                            Approve & download cleaned CSV
                          </>
                        )}
                      </button>

                      {applyError && (
                        <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-400">
                          <AlertCircle size={18} className="mt-0.5 shrink-0" />
                          <p>{applyError}</p>
                        </div>
                      )}

                      {cleaningSuccess && (
                        <div className="mt-4 flex items-start gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 text-sm text-emerald-300">
                          <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
                          <p>{cleaningSuccess}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </section>

          <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Recent datasets</h3>
                <p className="mt-1 text-xs text-zinc-500">
                  Your recently inspected files
                </p>
              </div>
              <Database className="text-zinc-600" size={20} />
            </div>

            {recentDatasets.length > 0 ? (
              <div className="mt-5 space-y-3">
                {recentDatasets.map((item, index) => (
                  <div key={`${item.filename}-${index}`} className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-4">
                    <FileSpreadsheet className="shrink-0 text-violet-400" size={24} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-zinc-200">{item.filename}</p>
                      <p className="mt-1 text-xs text-zinc-500">
                        {item.total_rows.toLocaleString()} rows · {item.total_columns} columns · {item.file_type}
                      </p>
                    </div>
                    {index === 0 && <span className="rounded-full bg-emerald-500/10 px-2 py-1 text-[10px] text-emerald-400">Latest</span>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex min-h-32 flex-col items-center justify-center text-center">
                <FileSpreadsheet className="mb-3 text-zinc-600" size={26} />
                <p className="text-sm text-zinc-400">No datasets available</p>
                <p className="mt-1 text-xs text-zinc-600">Your inspected datasets will appear here.</p>
              </div>
            )}
          </section>

          <footer className="flex flex-col justify-between gap-2 border-t border-white/5 pt-6 text-xs text-zinc-600 sm:flex-row">
            <p>InsightFlow AI · Intelligent Data Analyst</p>
            <p>Early development · Version 0.1.0</p>
          </footer>
        </div>
      </main>
    </div>
  )
}

export default App
