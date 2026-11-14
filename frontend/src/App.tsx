
import { useState } from 'react'
import {
  Activity,
  BarChart3,
  BrainCircuit,
  ChevronDown,
  Database,
  FileSpreadsheet,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
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

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [dataset, setDataset] = useState<DatasetInfo | null>(null)

  const navigation = [
    { label: 'Overview', icon: LayoutDashboard, active: true },
    { label: 'Data Explorer', icon: Database, active: false },
    { label: 'Analytics', icon: BarChart3, active: false },
    { label: 'Machine Learning', icon: BrainCircuit, active: false },
  ]

  const handleFileChange = (file: File | null) => {
    setSelectedFile(file)
    setUploadError('')
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a dataset first.')
      return
    }

    setIsUploading(true)
    setUploadError('')
    setDataset(null)

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

  const stats = [
    {
      label: 'Datasets Analyzed',
      value: dataset ? '1' : '0',
      change: dataset ? '1 dataset inspected' : 'No datasets yet',
      icon: Database,
    },
    {
      label: 'Analyses Completed',
      value: dataset ? '1' : '0',
      change: dataset ? 'Dataset inspection complete' : 'Ready to get started',
      icon: Activity,
    },
    {
      label: 'ML Models Trained',
      value: '0',
      change: 'Coming soon',
      icon: BrainCircuit,
    },
    {
      label: 'Data Quality',
      value: dataset
        ? `${Math.round(
            (1 -
              dataset.total_missing_values /
                Math.max(dataset.total_rows * dataset.total_columns, 1)) *
              100,
          )}%`
        : '—',
      change: dataset ? 'Based on missing-value count' : 'Awaiting dataset',
      icon: ShieldCheck,
    },
  ]

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

        <div className="px-4 py-7">
          <p className="mb-4 px-3 text-[10px] font-semibold tracking-[2px] text-zinc-600">
            WORKSPACE
          </p>
          <nav className="space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon
              return (
                <div
                  key={item.label}
                  className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm ${
                    item.active
                      ? 'border border-violet-500/20 bg-violet-600/15 font-medium text-violet-300'
                      : 'text-zinc-500'
                  }`}
                >
                  <Icon size={18} />
                  {item.label}
                </div>
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
                  disabled={isUploading}
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
                    disabled={isUploading}
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
                disabled={!selectedFile || isUploading}
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

              <div className="mt-8 flex min-h-44 flex-col items-center justify-center rounded-xl border border-white/5 bg-white/[0.015] text-center">
                <div className="mb-3 rounded-full bg-zinc-800/70 p-4 text-zinc-500">
                  <BarChart3 size={27} />
                </div>
                <p className="text-sm font-medium text-zinc-400">
                  {dataset ? 'Inspection complete' : 'No analysis yet'}
                </p>
                <p className="mt-2 max-w-52 text-xs leading-relaxed text-zinc-600">
                  {dataset
                    ? `${dataset.total_rows.toLocaleString()} rows and ${dataset.total_columns} columns inspected.`
                    : 'Upload a dataset to begin exploring your data.'}
                </p>
              </div>
            </div>
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

            {dataset ? (
              <div className="mt-5 flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-4">
                <FileSpreadsheet className="shrink-0 text-violet-400" size={24} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-200">
                    {dataset.filename}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {dataset.total_rows.toLocaleString()} rows · {dataset.total_columns} columns · {dataset.file_type}
                  </p>
                </div>
                <CheckCircle2 className="shrink-0 text-emerald-400" size={19} />
              </div>
            ) : (
              <div className="flex min-h-32 flex-col items-center justify-center text-center">
                <FileSpreadsheet className="mb-3 text-zinc-600" size={26} />
                <p className="text-sm text-zinc-400">No datasets available</p>
                <p className="mt-1 text-xs text-zinc-600">
                  Your inspected dataset will appear here.
                </p>
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
