import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { ArrowLeft, Bot, CheckCircle2, CircleAlert, KeyRound, LoaderCircle, Plus, ShieldCheck, Trash2, UserRound, Workflow, X } from 'lucide-react'
import { API_URL, apiFetch, type AuthUser } from '../config/api'

interface SettingsWorkbenchProps {
  user: AuthUser
  onBack: () => void
}

interface Credential {
  id: string
  display_name: string
  provider_name: string
  protocol: 'openai_compatible' | 'native_gemini' | 'native_anthropic'
  base_url: string
  model_id: string
  has_api_key: boolean
  has_custom_headers: boolean
  key_hint: string
  created_at: string
  updated_at: string
}

interface CredentialForm {
  protocol: 'openai_compatible' | 'native_gemini' | 'native_anthropic'
  display_name: string
  provider_name: string
  base_url: string
  model_id: string
  api_key: string
}

const emptyForm: CredentialForm = {
  protocol: 'openai_compatible',
  display_name: '',
  provider_name: '',
  base_url: '',
  model_id: '',
  api_key: '',
}

const inputClass = 'mt-1.5 w-full rounded-xl border border-white/10 bg-[#09090f] px-3.5 py-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-violet-500/60 focus:ring-2 focus:ring-violet-500/10'
const labelClass = 'text-xs font-medium text-zinc-400'

async function readResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof payload.detail === 'string' ? payload.detail : 'The request could not be completed.'
    throw new Error(detail)
  }
  return payload as T
}

export default function SettingsWorkbench({ user, onBack }: SettingsWorkbenchProps) {
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [form, setForm] = useState<CredentialForm>(emptyForm)
  const [customHeadersText, setCustomHeadersText] = useState('')
  const [clearCustomHeaders, setClearCustomHeaders] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [notice, setNotice] = useState<{ kind: 'success' | 'error'; message: string } | null>(null)
  const [testResults, setTestResults] = useState<Record<string, string>>({})

  const loadCredentials = useCallback(async () => {
    setLoading(true)
    try {
      const response = await apiFetch(`${API_URL}/api/v1/ai/credentials`)
      const payload = await readResponse<{ items: Credential[] }>(response)
      setCredentials(payload.items)
    } catch (error) {
      setNotice({ kind: 'error', message: error instanceof Error ? error.message : 'Unable to load provider connections.' })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadCredentials()
  }, [loadCredentials])

  function openNewForm() {
    setEditingId(null)
    setForm(emptyForm)
    setCustomHeadersText('')
    setClearCustomHeaders(false)
    setNotice(null)
    setShowForm(true)
  }

  function openEditForm(credential: Credential) {
    setEditingId(credential.id)
    setForm({
      protocol: credential.protocol,
      display_name: credential.display_name,
      provider_name: credential.provider_name,
      base_url: credential.base_url,
      model_id: credential.model_id,
      api_key: '',
    })
    setCustomHeadersText('')
    setClearCustomHeaders(false)
    setNotice(null)
    setShowForm(true)
  }

  function closeForm() {
    setShowForm(false)
    setEditingId(null)
    setForm(emptyForm)
    setCustomHeadersText('')
    setClearCustomHeaders(false)
  }

  async function saveCredential(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setNotice(null)
    try {
      const payload: Record<string, unknown> = {
        protocol: form.protocol,
        display_name: form.display_name.trim(),
        provider_name: form.provider_name.trim(),
        base_url: form.base_url.trim(),
        model_id: form.model_id.trim(),
      }
      if (form.api_key.trim()) payload.api_key = form.api_key.trim()
      if (customHeadersText.trim()) {
        let parsedHeaders: unknown
        try {
          parsedHeaders = JSON.parse(customHeadersText)
        } catch {
          throw new Error('Custom headers must be valid JSON.')
        }
        if (!parsedHeaders || typeof parsedHeaders !== 'object' || Array.isArray(parsedHeaders)) {
          throw new Error('Custom headers must be a JSON object of header names and string values.')
        }
        if (Object.values(parsedHeaders as Record<string, unknown>).some((value) => typeof value !== 'string')) {
          throw new Error('Every custom header value must be a string.')
        }
        payload.custom_headers = parsedHeaders
      } else if (editingId && clearCustomHeaders) {
        payload.custom_headers = {}
      }
      if (!editingId && !payload.api_key) throw new Error('Enter an API key to add this provider.')
      const response = await apiFetch(
        editingId ? `${API_URL}/api/v1/ai/credentials/${editingId}` : `${API_URL}/api/v1/ai/credentials`,
        {
          method: editingId ? 'PATCH' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      )
      await readResponse(response)
      setForm(emptyForm)
      setCustomHeadersText('')
      setClearCustomHeaders(false)
      setShowForm(false)
      setEditingId(null)
      setNotice({ kind: 'success', message: editingId ? 'Provider settings updated securely.' : 'Provider saved. Your API key is encrypted on the server.' })
      await loadCredentials()
    } catch (error) {
      setNotice({ kind: 'error', message: error instanceof Error ? error.message : 'Unable to save provider.' })
    } finally {
      setSaving(false)
    }
  }

  async function testCredential(credential: Credential) {
    setTestingId(credential.id)
    setNotice(null)
    setTestResults((previous) => ({ ...previous, [credential.id]: '' }))
    try {
      const response = await apiFetch(`${API_URL}/api/v1/ai/credentials/${credential.id}/test`, { method: 'POST' })
      const result = await readResponse<{ connected: boolean; message: string; model: string }>(response)
      setTestResults((previous) => ({ ...previous, [credential.id]: result.message || `Connected to ${result.model}` }))
      setNotice({ kind: 'success', message: `${credential.display_name}: connection successful.` })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Connection test failed.'
      setTestResults((previous) => ({ ...previous, [credential.id]: message }))
      setNotice({ kind: 'error', message: `${credential.display_name}: ${message}` })
    } finally {
      setTestingId(null)
    }
  }

  async function deleteCredential(credential: Credential) {
    if (!window.confirm(`Delete the saved connection "${credential.display_name}"?`)) return
    setDeletingId(credential.id)
    setNotice(null)
    try {
      const response = await apiFetch(`${API_URL}/api/v1/ai/credentials/${credential.id}`, { method: 'DELETE' })
      await readResponse(response)
      setCredentials((previous) => previous.filter((item) => item.id !== credential.id))
      setTestResults((previous) => {
        const next = { ...previous }
        delete next[credential.id]
        return next
      })
      setNotice({ kind: 'success', message: 'Provider connection deleted.' })
    } catch (error) {
      setNotice({ kind: 'error', message: error instanceof Error ? error.message : 'Unable to delete provider.' })
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <main className="min-h-screen bg-[#09090f] px-5 py-8 text-zinc-100 sm:px-8 lg:px-12">
      <div className="mx-auto max-w-5xl">
        <button type="button" onClick={onBack} className="mb-8 inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-400 transition hover:border-violet-500/40 hover:text-white">
          <ArrowLeft size={16} /> Back to dashboard
        </button>

        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-400">Workspace configuration</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Settings</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">Manage your account, AI connections and workspace preferences from one place.</p>
        </div>

        <section className="mb-6 rounded-2xl border border-white/[0.08] bg-[#11111b] p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-violet-500/10 text-violet-300"><UserRound size={22} /></div>
            <div className="min-w-0 flex-1">
              <h2 className="font-semibold text-white">Account</h2>
              <p className="mt-1 text-xs text-zinc-500">Signed in account</p>
              <p className="mt-2 break-all text-sm text-zinc-200">{user.email}</p>
              <p className="mt-2 text-xs text-zinc-600">Your settings and connected providers belong only to this account.</p>
            </div>
            <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-medium text-emerald-300">Authenticated</span>
          </div>
        </section>

        <section className="rounded-2xl border border-white/[0.08] bg-[#11111b] p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10 text-violet-300"><Bot size={20} /></div>
              <div>
                <h2 className="font-semibold text-white">AI provider connections</h2>
                <p className="mt-1 text-xs text-zinc-500">Connect OpenAI-compatible providers, Google Gemini, or Anthropic Claude.</p>
              </div>
            </div>
            <button type="button" onClick={openNewForm} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-500"><Plus size={16} /> Add provider</button>
          </div>

          {notice && (
            <div className={`mt-5 flex items-start gap-2 rounded-xl border p-3 text-sm ${notice.kind === 'success' ? 'border-emerald-500/20 bg-emerald-500/[0.06] text-emerald-300' : 'border-rose-500/20 bg-rose-500/[0.06] text-rose-300'}`}>
              {notice.kind === 'success' ? <CheckCircle2 size={17} className="mt-0.5 shrink-0" /> : <CircleAlert size={17} className="mt-0.5 shrink-0" />}
              <span>{notice.message}</span>
              <button type="button" onClick={() => setNotice(null)} className="ml-auto text-current/70 hover:text-current"><X size={16} /></button>
            </div>
          )}

          {showForm && (
            <form onSubmit={saveCredential} className="mt-6 rounded-xl border border-violet-500/20 bg-[#0d0d16] p-4 sm:p-5">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-semibold text-zinc-100">{editingId ? 'Edit provider connection' : 'Connect a provider'}</h3>
                <button type="button" onClick={closeForm} className="rounded-lg p-1.5 text-zinc-500 hover:bg-white/5 hover:text-white" aria-label="Close form"><X size={17} /></button>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className={labelClass}>API protocol
                  <select className={inputClass} value={form.protocol} onChange={(event) => {
                    const protocol = event.target.value as CredentialForm['protocol']
                    const defaultUrl = protocol === 'native_gemini'
                      ? 'https://generativelanguage.googleapis.com'
                      : protocol === 'native_anthropic'
                        ? 'https://api.anthropic.com'
                        : ''
                    setForm({ ...form, protocol, base_url: defaultUrl })
                  }}>
                    <option value="openai_compatible">OpenAI-compatible API</option>
                    <option value="native_gemini">Google Gemini API (native)</option>
                    <option value="native_anthropic">Anthropic Claude API (native)</option>
                  </select>
                </label>
                <label className={labelClass}>Connection name
                  <input required maxLength={80} className={inputClass} placeholder="My NVIDIA account" value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} />
                </label>
                <label className={labelClass}>Provider name
                  <input required maxLength={80} className={inputClass} placeholder="NVIDIA, OpenRouter, Groq..." value={form.provider_name} onChange={(event) => setForm({ ...form, provider_name: event.target.value })} />
                </label>
                <label className={labelClass + ' sm:col-span-2'}>API base URL
                  <input required type="url" maxLength={500} className={inputClass} placeholder={form.protocol === 'native_gemini' ? 'https://generativelanguage.googleapis.com' : form.protocol === 'native_anthropic' ? 'https://api.anthropic.com' : 'https://integrate.api.nvidia.com/v1'} value={form.base_url} onChange={(event) => setForm({ ...form, base_url: event.target.value })} />
                </label>
                <label className={labelClass}>Model ID
                  <input required maxLength={200} className={inputClass} placeholder="meta/llama-3.1-8b-instruct" value={form.model_id} onChange={(event) => setForm({ ...form, model_id: event.target.value })} />
                </label>
                <label className={labelClass}>API key {editingId && <span className="text-zinc-600">(leave blank to keep current)</span>}
                  <input required={!editingId} type="password" autoComplete="new-password" maxLength={4096} className={inputClass} placeholder={editingId ? 'Enter a new key only to rotate it' : 'Paste your provider API key'} value={form.api_key} onChange={(event) => setForm({ ...form, api_key: event.target.value })} />
                </label>
                <label className={labelClass + ' sm:col-span-2'}>Custom HTTP headers (optional)
                  <textarea rows={4} maxLength={8192} spellCheck={false} className={inputClass + ' font-mono'} placeholder={'{\n  "X-Workspace-ID": "your-workspace",\n  "X-Environment": "production"\n}'} value={customHeadersText} onChange={(event) => setCustomHeadersText(event.target.value)} />
                  <span className="mt-1 block text-[11px] leading-5 text-zinc-600">Enter a JSON object with header names and string values. Values are encrypted on the server and never returned to the browser.</span>
                </label>
                {editingId && credentials.find((item) => item.id === editingId)?.has_custom_headers && (
                  <label className="sm:col-span-2 flex items-center gap-2 text-xs text-zinc-400">
                    <input type="checkbox" checked={clearCustomHeaders} onChange={(event) => setClearCustomHeaders(event.target.checked)} />
                    Remove saved custom headers (leave unchecked to keep them)
                  </label>
                )}
              </div>
              <p className="mt-3 text-xs leading-5 text-zinc-600">Use the provider's HTTPS API base URL. Your key is sent over HTTPS, encrypted at rest, and never shown again. It stays only in this form's memory until you save or close it.</p>
              <div className="mt-5 flex justify-end gap-2">
                <button type="button" onClick={closeForm} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-zinc-400 hover:text-white">Cancel</button>
                <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60">{saving && <LoaderCircle size={15} className="animate-spin" />}{saving ? 'Saving...' : 'Save connection'}</button>
              </div>
            </form>
          )}

          <div className="mt-5 space-y-3">
            {loading ? (
              <div className="flex items-center justify-center gap-2 py-10 text-sm text-zinc-500"><LoaderCircle size={17} className="animate-spin" /> Loading saved connections...</div>
            ) : credentials.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/10 px-4 py-10 text-center">
                <KeyRound size={24} className="mx-auto text-zinc-600" />
                <p className="mt-3 text-sm font-medium text-zinc-300">No AI providers connected</p>
                <p className="mt-1 text-xs text-zinc-600">Add a provider connection to securely store its API key.</p>
              </div>
            ) : credentials.map((credential) => (
              <article key={credential.id} className="rounded-xl border border-white/[0.08] bg-[#0d0d16] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-zinc-100">{credential.display_name}</h3>
                      <span className="rounded-full border border-emerald-500/20 bg-emerald-500/[0.06] px-2 py-0.5 text-[10px] text-emerald-300">Key encrypted</span>{credential.has_custom_headers && <span className="rounded-full border border-violet-500/20 bg-violet-500/[0.06] px-2 py-0.5 text-[10px] text-violet-300">Custom headers encrypted</span>}
                    </div>
                    <p className="mt-1 text-xs text-zinc-500">{credential.provider_name} · {credential.model_id}</p>
                    <p className="mt-1 break-all text-xs text-zinc-600">{credential.base_url}</p>
                    <p className="mt-2 font-mono text-xs text-zinc-500">{credential.key_hint}</p>
                    {testResults[credential.id] && <p className="mt-2 text-xs text-zinc-400">{testResults[credential.id]}</p>}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" disabled={testingId === credential.id} onClick={() => void testCredential(credential)} className="inline-flex items-center gap-1.5 rounded-lg border border-violet-500/25 px-3 py-2 text-xs font-medium text-violet-300 hover:bg-violet-500/10 disabled:opacity-50">{testingId === credential.id ? <LoaderCircle size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} Test</button>
                    <button type="button" onClick={() => openEditForm(credential)} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-400 hover:text-white">Edit</button>
                    <button type="button" disabled={deletingId === credential.id} onClick={() => void deleteCredential(credential)} className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/20 px-3 py-2 text-xs text-rose-300 hover:bg-rose-500/[0.06] disabled:opacity-50">{deletingId === credential.id ? <LoaderCircle size={14} className="animate-spin" /> : <Trash2 size={14} />} Delete</button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <section className="rounded-2xl border border-white/[0.08] bg-[#11111b] p-5">
            <div className="flex items-center gap-3"><ShieldCheck size={19} className="text-emerald-300" /><h3 className="font-semibold text-zinc-100">Privacy & security</h3></div>
            <p className="mt-2 text-sm leading-6 text-zinc-500">Credentials are encrypted on the server and scoped to your authenticated account. The API returns masked key metadata only.</p>
          </section>
          <section className="rounded-2xl border border-white/[0.08] bg-[#11111b] p-5">
            <div className="flex items-center gap-3"><Workflow size={19} className="text-violet-300" /><h3 className="font-semibold text-zinc-100">Provider compatibility</h3></div>
            <p className="mt-2 text-sm leading-6 text-zinc-500">Supports OpenAI-compatible chat completions plus native Google Gemini and Anthropic Claude APIs.</p>
          </section>
        </div>
      </div>
    </main>
  )
}
