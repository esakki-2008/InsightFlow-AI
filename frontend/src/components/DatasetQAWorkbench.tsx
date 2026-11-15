import { useEffect, useState } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Database,
  Loader2,
  MessageSquareText,
  Sparkles,
} from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'

type QAResult = {
  question: string
  answer: string
  query_type: string
  result: Record<string, unknown>
  rows_analyzed: number
  provider?: string
  model?: string
  privacy_note?: string
}

type QAResponse = {
  message: string
  filename: string
  qa: QAResult
}

type Props = { onBack: () => void }

const examples = [
  'How many rows are in the dataset?',
  'How many DDoS records are present?',
  'What is the average Flow Duration?',
  'What is the correlation between Flow Bytes/s and Flow Packets/s?',
  'How many missing values are there?',
]

export default function DatasetQAWorkbench({ onBack }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<QAResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<'standard' | 'advanced'>('standard')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('nvidia/nemotron-3.5-lightning-30b-a3b')

  useEffect(() => () => setApiKey(''), [])

  const askQuestion = async (nextQuestion?: string) => {
    const prompt = (nextQuestion ?? question).trim()
    if (!file) {
      setError('Select a CSV or Excel dataset first.')
      return
    }
    if (!prompt) {
      setError('Enter a question about your dataset.')
      return
    }
    if (mode === 'advanced' && !apiKey.trim()) {
      setError('Enter your NVIDIA API key to use Advanced AI mode.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const body = new FormData()
      body.append('file', file)
      body.append('question', prompt)
      const endpoint = mode === 'advanced' ? '/api/v1/datasets/ask/advanced' : '/api/v1/datasets/ask'
      if (mode === 'advanced') {
        body.append('api_key', apiKey.trim())
        body.append('model', model)
      }
      const response = await fetch(API_URL + endpoint, { method: 'POST', body })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || 'Unable to answer this question.')
      }
      const data = payload as QAResponse
      setHistory((current) => [data.qa, ...current])
      setQuestion(prompt)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong while asking the question.')
    } finally {
      setLoading(false)
    }
  }

  const formatValue = (value: unknown) => {
    if (value === null || value === undefined) return '—'
    if (typeof value === 'number') return value.toLocaleString()
    if (Array.isArray(value)) return value.length ? value.join(', ') : 'None'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  return (
    <div className="min-h-screen bg-[#09090f] text-zinc-100">
      <header className="flex h-20 items-center justify-between border-b border-white/5 px-6 lg:px-10">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="rounded-xl border border-white/10 p-2 text-zinc-400 transition hover:bg-white/5 hover:text-white" aria-label="Back to overview">
            <ArrowLeft size={18} />
          </button>
          <div>
            <p className="text-xs text-zinc-500">Workspace / AI Data Q&A</p>
            <h1 className="mt-1 text-lg font-semibold">Ask your dataset</h1>
          </div>
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-violet-500/20 bg-violet-500/5 px-3 py-2 text-xs text-violet-300 sm:flex">
          <Sparkles size={14} /> Standard + Advanced AI
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 p-6 lg:p-10">
        <section className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/[0.10] to-[#11111b] p-6 sm:p-8">
          <div className="flex items-start gap-4">
            <div className="rounded-2xl bg-violet-500/15 p-3 text-violet-300"><MessageSquareText size={25} /></div>
            <div>
              <p className="text-xs font-semibold tracking-[2px] text-violet-300">DATASET QUESTION ANSWERING</p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">Talk to your data.</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">Upload a dataset and ask questions in plain English. Standard mode uses deterministic operations; Advanced AI uses NVIDIA to plan and explain validated Pandas analysis.</p>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-6">
          <h3 className="font-semibold">Choose analysis mode</h3>
          <p className="mt-1 text-xs text-zinc-500">Use Standard without a key, or enable Advanced AI with your NVIDIA API key.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <button type="button" disabled={loading} onClick={() => { setMode('standard'); setError('') }} className={mode === 'standard' ? 'rounded-xl border border-violet-500/50 bg-violet-500/10 p-4 text-left' : 'rounded-xl border border-white/10 bg-black/10 p-4 text-left'}>
              <span className="block text-sm font-semibold text-white">Standard Mode</span>
              <span className="mt-1 block text-xs text-zinc-400">Deterministic Pandas analysis · No API key</span>
            </button>
            <button type="button" disabled={loading} onClick={() => { setMode('advanced'); setError('') }} className={mode === 'advanced' ? 'rounded-xl border border-fuchsia-500/50 bg-fuchsia-500/10 p-4 text-left' : 'rounded-xl border border-white/10 bg-black/10 p-4 text-left'}>
              <span className="block text-sm font-semibold text-white">Advanced AI Mode</span>
              <span className="mt-1 block text-xs text-zinc-400">NVIDIA AI query planning and explanations</span>
            </button>
          </div>
          {mode === 'advanced' && (
            <div className="mt-5 space-y-4 rounded-xl border border-fuchsia-500/20 bg-fuchsia-500/[0.04] p-4">
              <div>
                <label htmlFor="nvidia-model" className="mb-2 block text-sm font-medium text-zinc-300">NVIDIA model</label>
                <select id="nvidia-model" value={model} onChange={(event) => setModel(event.target.value)} disabled={loading} className="w-full rounded-xl border border-white/10 bg-[#09090f] px-3 py-3 text-sm text-white outline-none focus:border-fuchsia-500/50">
                  <option value="nvidia/nemotron-3.5-lightning-30b-a3b">Nemotron 3.5 Lightning 30B</option>
                </select>
              </div>
              <div>
                <label htmlFor="nvidia-api-key" className="mb-2 block text-sm font-medium text-zinc-300">NVIDIA API key</label>
                <input id="nvidia-api-key" type="password" autoComplete="off" value={apiKey} onChange={(event) => setApiKey(event.target.value)} disabled={loading} placeholder="Paste your NVIDIA API key" className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none placeholder:text-zinc-600 focus:border-fuchsia-500/50" />
                <p className="mt-2 text-xs leading-5 text-zinc-500">Your key stays temporarily in this page's memory. It is not saved to localStorage, sessionStorage, or the backend database. It is cleared when you leave this workspace or reload the page.</p>
              </div>
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/[0.05] p-3 text-xs leading-5 text-amber-200/80">
                NVIDIA trial requests may be retained by NVIDIA for service improvement and security. The app sends dataset schema for planning and computed results for explanation; raw dataset rows are processed locally and are not sent by this workflow. Avoid sensitive datasets.
              </div>
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-6">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-xl bg-sky-500/10 p-3 text-sky-300"><Database size={20} /></div>
            <div>
              <h3 className="font-semibold">1. Choose your dataset</h3>
              <p className="mt-1 text-xs text-zinc-500">CSV, XLSX or XLS · Maximum 10 MB</p>
            </div>
          </div>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            disabled={loading}
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null)
              setHistory([])
              setError('')
            }}
            className="block w-full cursor-pointer rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-zinc-300 file:mr-4 file:rounded-lg file:border-0 file:bg-violet-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-violet-500"
          />
          {file && <p className="mt-3 text-xs text-violet-300">{file.name} · {(file.size / 1024).toFixed(1)} KB</p>}
        </section>

        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-6">
          <h3 className="font-semibold">2. Ask a question</h3>
          <p className="mt-1 text-xs text-zinc-500">Try a suggested question or write your own.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {examples.map((example) => (
              <button key={example} type="button" disabled={loading || !file} onClick={() => { setQuestion(example); void askQuestion(example) }} className="rounded-full border border-violet-500/20 bg-violet-500/[0.05] px-3 py-2 text-left text-xs text-violet-200 transition hover:bg-violet-500/15 disabled:cursor-not-allowed disabled:opacity-40">
                {example}
              </button>
            ))}
          </div>
          <form className="mt-5" onSubmit={(event) => { event.preventDefault(); void askQuestion() }}>
            <label htmlFor="dataset-question" className="mb-2 block text-sm font-medium text-zinc-300">Your question</label>
            <textarea
              id="dataset-question"
              rows={3}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="e.g. What is the average Flow Duration?"
              disabled={loading}
              className="w-full resize-y rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/10 disabled:opacity-50"
            />
            <button type="submit" disabled={loading || !file || !question.trim()} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto">
              {loading ? <><Loader2 size={17} className="animate-spin" /> Analyzing question...</> : <><MessageSquareText size={17} /> {mode === 'advanced' ? 'Ask Advanced AI' : 'Ask InsightFlow'}</>}
            </button>
          </form>
          {error && <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300"><AlertCircle size={17} className="mt-0.5 shrink-0" />{error}</div>}
        </section>

        {history.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">Answers</h3>
              <span className="text-xs text-zinc-500">{history.length} question{history.length === 1 ? '' : 's'} this session</span>
            </div>
            {history.map((item, index) => (
              <article key={`${item.question}-${index}`} className="rounded-2xl border border-emerald-500/15 bg-[#11111b] p-5 sm:p-6">
                <div className="flex items-start gap-3">
                  <div className="rounded-xl bg-emerald-500/10 p-2.5 text-emerald-300"><CheckCircle2 size={19} /></div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-zinc-500">QUESTION</p>
                    <h4 className="mt-1 font-medium text-zinc-100">{item.question}</h4>
                    <p className="mt-4 text-xs font-medium text-emerald-300">INSIGHTFLOW ANSWER</p>
                    <p className="mt-2 text-base leading-7 text-zinc-100">{item.answer}</p>
                    <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-zinc-500">
                      <span className="rounded-full border border-white/10 px-2.5 py-1">Type: {item.query_type.replaceAll('_', ' ')}</span>
                      <span className="rounded-full border border-white/10 px-2.5 py-1">Rows analyzed: {item.rows_analyzed.toLocaleString()}</span>
                      {item.provider && <span className="rounded-full border border-fuchsia-500/20 px-2.5 py-1 text-fuchsia-300">{item.provider} · {item.model}</span>}
                    </div>
                    <details className="mt-4 rounded-xl border border-white/5 bg-black/20 p-3">
                      <summary className="cursor-pointer text-xs font-medium text-zinc-400">View structured result</summary>
                      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                        {Object.entries(item.result).map(([key, value]) => (
                          <div key={key} className="rounded-lg bg-white/[0.03] p-3">
                            <dt className="text-[11px] capitalize text-zinc-500">{key.replaceAll('_', ' ')}</dt>
                            <dd className="mt-1 break-words text-sm text-zinc-200">{formatValue(value)}</dd>
                          </div>
                        ))}
                      </dl>
                    </details>
                  </div>
                </div>
              </article>
            ))}
          </section>
        )}
        <p className="text-xs leading-5 text-zinc-600">Standard mode supports predefined analytical operations. Advanced AI can interpret broader questions, but every operation is validated and executed locally with Pandas. Results are descriptive, not causal.</p>
      </main>
    </div>
  )
}
