import { useEffect, useMemo, useState } from 'react'
import {
  getEventById,
  getEvents,
  getHealth,
  getMetrics,
  getSources,
  ingestLog,
  uploadLogFile,
  type LogEvent,
  type LogSource,
  type HealthResponse,
} from './api'

type Page = 'Overview' | 'Logs Explorer' | 'Sources' | 'Ingestion'

const navItems: Page[] = [
  'Overview',
  'Logs Explorer',
  'Sources',
  'Ingestion',
]

function severityClass(severity: string) {
  switch (severity.toUpperCase()) {
    case 'ERROR':
    case 'CRITICAL':
    case 'FATAL':
      return 'border-red-500/30 bg-red-500/10 text-red-300'
    case 'WARNING':
    case 'WARN':
      return 'border-amber-500/30 bg-amber-500/10 text-amber-300'
    case 'DEBUG':
      return 'border-slate-500/30 bg-slate-500/10 text-slate-300'
    default:
      return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
  }
}

function formatDate(value?: string) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatTime(value?: string) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleTimeString()
}

function StatCard({
  label,
  value,
  detail,
  accent,
}: {
  label: string
  value: string | number
  detail: string
  accent: string
}) {
  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#111827] p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-white">
        {value}
      </p>
      <p className={`mt-2 text-xs ${accent}`}>{detail}</p>
    </div>
  )
}

function App() {
  const [page, setPage] = useState<Page>('Overview')
  const [events, setEvents] = useState<LogEvent[]>([])
  const [selectedEvent, setSelectedEvent] = useState<LogEvent | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [totalEvents, setTotalEvents] = useState(0)
  const [sources, setSources] = useState<LogSource[]>([])
  const [totalSources, setTotalSources] = useState(0)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [sourceFilter, setSourceFilter] = useState('ALL')
  const [sourceSearch, setSourceSearch] = useState('')
  const [ingestSource, setIngestSource] = useState('')
  const [ingestLevel, setIngestLevel] = useState('INFO')
  const [ingestMessage, setIngestMessage] = useState('')
  const [ingestLoading, setIngestLoading] = useState(false)
  const [ingestResult, setIngestResult] = useState('')
  const [ingestError, setIngestError] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileLoading, setFileLoading] = useState(false)
  const [fileResult, setFileResult] = useState('')
  const [fileError, setFileError] = useState('')


  async function loadData(isRefresh = false) {
    if (isRefresh) setRefreshing(true)
    else setLoading(true)

    setError('')

    const [eventsResult, sourcesResult, healthResult, metricsResult] =
      await Promise.allSettled([
        getEvents(50, 0),
        getSources(),
        getHealth(),
        getMetrics(),
      ])

    const errors: string[] = []

    if (eventsResult.status === 'fulfilled') {
      setEvents(eventsResult.value.events ?? [])
      setTotalEvents(eventsResult.value.total ?? eventsResult.value.count ?? 0)
    } else {
      errors.push('Events could not be loaded.')
    }

    if (sourcesResult.status === 'fulfilled') {
      setSources(sourcesResult.value.sources ?? [])
      setTotalSources(
        sourcesResult.value.count ?? sourcesResult.value.sources?.length ?? 0,
      )
    } else {
      errors.push('Sources could not be loaded.')
    }

    if (healthResult.status === 'fulfilled') {
      setHealth(healthResult.value)
    } else {
      setHealth(null)
      errors.push('Backend health could not be checked.')
    }

    if (metricsResult.status === 'fulfilled') {
      setMetrics(metricsResult.value)
    } else {
      setMetrics(null)
    }

    setError(errors.join(' '))
    setLoading(false)
    setRefreshing(false)
  }

  async function handleOpenEvent(event: LogEvent) {
    if (event.event_id == null) {
      setDetailError('This event does not have an event ID.')
      setSelectedEvent(event)
      return
    }

    setSelectedEvent(event)
    setDetailLoading(true)
    setDetailError('')

    try {
      const details = await getEventById(event.event_id)
      setSelectedEvent(details)
    } catch (error) {
      setDetailError(
        error instanceof Error
          ? error.message
          : 'Could not load event details.',
      )
    } finally {
      setDetailLoading(false)
    }
  }


  
  async function handleIngest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIngestResult('')
    setIngestError('')

    if (!ingestSource.trim() || !ingestMessage.trim()) {
      setIngestError('Source and message are required.')
      return
    }

    setIngestLoading(true)

    try {
      await ingestLog({
        source: ingestSource.trim(),
        level: ingestLevel,
        message: ingestMessage.trim(),
      })

      setIngestResult('Log ingested successfully!')
      setIngestMessage('')
      await loadData(true)
    } catch (error) {
      setIngestError(
        error instanceof Error ? error.message : 'Failed to ingest log.',
      )
    } finally {
      setIngestLoading(false)
    }
  }

  
  async function handleFileUpload(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()
    const form = event.currentTarget

    setFileResult('')
    setFileError('')

    if (!selectedFile) {
      setFileError('Please select a CSV or JSON file.')
      return
    }

    setFileLoading(true)

    try {
      const result = await uploadLogFile(selectedFile)

      setFileResult(
        `Successfully ingested ${result.count} log events from ${selectedFile.name}.`,
      )
      setSelectedFile(null)

      form.reset()

      await loadData(true)
    } catch (error) {
      setFileError(
        error instanceof Error ? error.message : 'File upload failed.',
      )
    } finally {
      setFileLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const [pageOffset, setPageOffset] = useState(0)
  const pageSize = 50

  
  useEffect(() => {
    if (page !== 'Logs Explorer') return

    let cancelled = false

    const timer = window.setTimeout(async () => {
      try {
        setError('')

        const result = await getEvents(pageSize, pageOffset, {
          search,
          source: sourceFilter,
          severity: severityFilter,
        })

        if (cancelled) return

        setEvents(result.events ?? [])
        setTotalEvents(result.total ?? 0)
      } catch (error) {
        if (!cancelled) {
          setError(
            error instanceof Error
              ? error.message
              : 'Failed to search events.',
          )
        }
      }
    }, 300)

    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [page, search, sourceFilter, severityFilter, pageOffset])


  const availableSources = useMemo(
    () =>
      [...new Set(events.map((event) => event.source).filter(
        (source): source is string => Boolean(source),
      ))].sort(),
    [events],
  )

  const filteredEvents = useMemo(() => {
    const query = search.trim().toLowerCase()

    return events.filter((event) => {
      const matchesSearch =
        !query ||
        [event.message, event.source, event.severity, event.event_id]
          .some((value) => String(value ?? '').toLowerCase().includes(query))

      const matchesSeverity =
        severityFilter === 'ALL' ||
        String(event.severity ?? 'INFO').toUpperCase() === severityFilter

      const matchesSource =
        sourceFilter === 'ALL' || event.source === sourceFilter

      return matchesSearch && matchesSeverity && matchesSource
    })
  }, [events, search, severityFilter, sourceFilter])

  const filteredSources = useMemo(() => {
    const query = sourceSearch.trim().toLowerCase()
    return sources.filter((source) =>
      [source.name, source.source_type, source.source_id]
        .some((value) => String(value ?? '').toLowerCase().includes(query)),
    )
  }, [sources, sourceSearch])

  const errorCount = events.filter((event) =>
    ['ERROR', 'CRITICAL', 'FATAL'].includes(
      String(event.severity ?? '').toUpperCase(),
    ),
  ).length

  const warningCount = events.filter((event) =>
    ['WARNING', 'WARN'].includes(
      String(event.severity ?? '').toUpperCase(),
    ),
  ).length

  const databaseConnected =
    String(health?.database ?? '').toLowerCase() === 'connected'

  const backendHealthy =
    String(health?.status ?? '').toLowerCase() === 'ok'

  return (
    <div className="min-h-screen bg-[#080d18] text-slate-200">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 shrink-0 border-r border-white/[0.08] bg-[#0b1120] p-5 md:flex md:flex-col">
          <div className="mb-10 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-400/10 text-xl font-bold text-cyan-300">
              L
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-wide text-white">
                LogForge
              </h1>
              <p className="text-xs text-slate-500">Universal Log Platform</p>
            </div>
          </div>

          <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Workspace
          </p>

          <nav className="space-y-1">
            {navItems.map((item) => (
              <button
                key={item}
                onClick={() => setPage(item)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition ${
                  page === item
                    ? 'border border-cyan-400/20 bg-cyan-400/10 text-cyan-300'
                    : 'text-slate-400 hover:bg-white/[0.04] hover:text-white'
                }`}
              >
                <span className="w-5 text-center">
                  {item === 'Overview'
                    ? '◈'
                    : item === 'Logs Explorer'
                      ? '≡'
                      : item === 'Sources'
                        ? '⌘'
                        : '⇧'}
                </span>
                {item}
              </button>
            ))}
          </nav>

          <div className="mt-auto rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
            <div className="mb-2 flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  backendHealthy && databaseConnected
                    ? 'bg-emerald-400'
                    : 'bg-amber-400'
                }`}
              />
              <span className="text-xs font-medium text-slate-300">
                {backendHealthy && databaseConnected
                  ? 'System connected'
                  : 'Connection status'}
              </span>
            </div>
            <p className="text-xs leading-5 text-slate-500">
              Live status from your LogForge API.
            </p>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] px-5 py-5 sm:px-8">
            <div>
              <p className="text-xs text-slate-500">
                LogForge / {page}
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-white">
                {page}
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                Monitor and explore your normalized log events.
              </p>
            </div>

            <button
              onClick={() => void loadData(true)}
              disabled={refreshing || loading}
              className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {refreshing ? 'Refreshing...' : '↻ Refresh data'}
            </button>
          </header>

          <div className="space-y-6 p-5 sm:p-8">
            {error && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/[0.08] p-4 text-sm text-amber-200">
                {error} Check that the FastAPI backend is running on port 8000.
              </div>
            )}

            {loading ? (
              <div className="rounded-2xl border border-white/[0.08] bg-[#111827] p-10 text-center">
                <p className="text-sm text-slate-400">
                  Connecting to LogForge API and loading data...
                </p>
              </div>
            ) : (
              <>
                {page === 'Overview' && (
                  <>
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                      <StatCard
                        label="Total Events"
                        value={totalEvents.toLocaleString()}
                        detail="Total normalized events in backend"
                        accent="text-cyan-300"
                      />
                      <StatCard
                        label="Registered Sources"
                        value={totalSources.toLocaleString()}
                        detail="Sources returned by the API"
                        accent="text-violet-300"
                      />
                      <StatCard
                        label="Errors in Latest 50"
                        value={errorCount}
                        detail="ERROR, CRITICAL and FATAL"
                        accent="text-red-300"
                      />
                      <StatCard
                        label="Warnings in Latest 50"
                        value={warningCount}
                        detail="WARNING and WARN"
                        accent="text-amber-300"
                      />
                    </div>

                    <section className="rounded-2xl border border-white/[0.08] bg-[#111827] p-5">
                      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <h3 className="font-semibold text-white">
                            System health
                          </h3>
                          <p className="mt-1 text-xs text-slate-500">
                            Status reported by your backend
                          </p>
                        </div>
                        <span
                          className={`rounded-full border px-3 py-1 text-xs ${
                            backendHealthy && databaseConnected
                              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                              : 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                          }`}
                        >
                          {backendHealthy && databaseConnected
                            ? 'Healthy'
                            : 'Check connection'}
                        </span>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-3">
                        <div className="rounded-xl bg-white/[0.03] p-4">
                          <p className="text-xs text-slate-500">API status</p>
                          <p className="mt-2 font-medium text-white">
                            {health?.status ?? 'Unavailable'}
                          </p>
                        </div>
                        <div className="rounded-xl bg-white/[0.03] p-4">
                          <p className="text-xs text-slate-500">Service</p>
                          <p className="mt-2 break-all font-medium text-white">
                            {health?.service ?? 'Unavailable'}
                          </p>
                        </div>
                        <div className="rounded-xl bg-white/[0.03] p-4">
                          <p className="text-xs text-slate-500">Database</p>
                          <p className="mt-2 font-medium text-white">
                            {health?.database ?? 'Unavailable'}
                          </p>
                        </div>
                      </div>
                    </section>

                    {metrics && (
                      <section className="rounded-2xl border border-white/[0.08] bg-[#111827] p-5">
                        <h3 className="font-semibold text-white">
                          Backend metrics response
                        </h3>
                        <p className="mt-1 text-xs text-slate-500">
                          Values returned by the /metrics endpoint.
                        </p>
                        <pre className="mt-4 overflow-x-auto rounded-xl bg-black/20 p-4 text-xs leading-6 text-cyan-200">
                          {JSON.stringify(metrics, null, 2)}
                        </pre>
                      </section>
                    )}

                    <LogTable
                      events={filteredEvents.slice(0, 10)}
                      title="Recent events"
                      subtitle="Latest events returned by the backend"
                      emptyMessage="No events were returned by the API."
                      onEventClick={handleOpenEvent}
                    />

                    <button
                      onClick={() => setPage('Logs Explorer')}
                      className="text-sm text-cyan-300 hover:text-cyan-200"
                    >
                      Explore all loaded events →
                    </button>
                  </>
                )}

                {page === 'Logs Explorer' && (
                  <section className="space-y-4">
                    <div className="grid gap-3 lg:grid-cols-[1fr_190px_220px]">
                      <input
                        value={search}
                        onChange={(event) => {
                          setSearch(event.target.value) 
                          setPageOffset(0)
                        }}
                        placeholder="Search message, source, severity or ID..."
                        className="min-w-0 rounded-xl border border-white/10 bg-[#111827] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-cyan-400/50"
                      />

                      <select
                        value={severityFilter}
                        onChange={(event) => {
                          setSeverityFilter(event.target.value)
                          setPageOffset(0)
                        }}
                        className="rounded-xl border border-white/10 bg-[#111827] px-3 py-3 text-sm text-slate-200 outline-none"
                      >
                        <option value="ALL">All severities</option>
                        <option value="INFO">INFO</option>
                        <option value="DEBUG">DEBUG</option>
                        <option value="WARNING">WARNING</option>
                        <option value="WARN">WARN</option>
                        <option value="ERROR">ERROR</option>
                        <option value="CRITICAL">CRITICAL</option>
                        <option value="FATAL">FATAL</option>
                      </select>

                      <select
                        value={sourceFilter}
                        onChange={(event) =>{
                          setSourceFilter(event.target.value)
                          setPageOffset(0)
                        }}
                        className="rounded-xl border border-white/10 bg-[#111827] px-3 py-3 text-sm text-slate-200 outline-none"
                      >
                        <option value="ALL">All loaded sources</option>
                        {availableSources.map((source) => (
                          <option key={source} value={source}>
                            {source}
                          </option>
                        ))}
                      </select>
                    </div>

                    <p className="text-xs text-slate-500">
                      Showing {events.length} events on this page. Total matching events: {totalEvents.toLocaleString()}.
                    </p>

                    <LogTable
                      events={events}
                      title="Logs Explorer"
                      subtitle="Search and filter the events currently loaded"
                      emptyMessage="No events match your current filters."
                      onEventClick={handleOpenEvent}
                    />
                    
                  <div className="flex items-center justify-between gap-4">
                    <p className="text-xs text-slate-500">
                      {totalEvents === 0
                        ? 'No matching events'
                        : `Showing ${pageOffset + 1}–${Math.min(
                            pageOffset + events.length,
                            totalEvents,
                          )} of ${totalEvents}`}
                    </p>

                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          setPageOffset((offset) => Math.max(0, offset - pageSize))
                        }
                        disabled={pageOffset === 0}
                        className="rounded-lg border border-white/10 px-4 py-2 text-sm disabled:opacity-40"
                      >
                        Previous
                      </button>

                      <button
                        onClick={() => setPageOffset((offset) => offset + pageSize)}
                        disabled={pageOffset + events.length >= totalEvents}
                        className="rounded-lg border border-white/10 px-4 py-2 text-sm disabled:opacity-40"
                      >
                        Next
                      </button>
                    </div>
                  </div>

                  </section>
                )}

                {page === 'Sources' && (
                  <section className="overflow-hidden rounded-2xl border border-white/[0.08] bg-[#111827]">
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] p-5">
                      <div>
                        <h3 className="font-semibold text-white">
                          Registered sources
                        </h3>
                        <p className="mt-1 text-xs text-slate-500">
                          {totalSources.toLocaleString()} sources reported by the API
                        </p>
                      </div>
                      <input
                        value={sourceSearch}
                        onChange={(event) => setSourceSearch(event.target.value)}
                        placeholder="Search sources..."
                        className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-600 focus:border-cyan-400/50 sm:w-64"
                      />
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-white/[0.02] text-xs uppercase tracking-wider text-slate-500">
                          <tr>
                            <th className="px-5 py-4">Source name</th>
                            <th className="px-5 py-4">Type</th>
                            <th className="px-5 py-4">Created</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.06]">
                          {filteredSources.slice(0, 100).map((source, index) => (
                            <tr
                              key={source.source_id ?? `${source.name}-${index}`}
                              className="hover:bg-white/[0.02]"
                            >
                              <td className="max-w-xs break-words px-5 py-4 text-slate-200">
                                {source.name ?? 'Unnamed source'}
                              </td>
                              <td className="px-5 py-4 text-slate-400">
                                {source.source_type ?? '—'}
                              </td>
                              <td className="whitespace-nowrap px-5 py-4 text-slate-400">
                                {formatDate(source.created_at)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {filteredSources.length === 0 && (
                      <p className="p-8 text-center text-sm text-slate-500">
                        No sources match your search.
                      </p>
                    )}

                    {filteredSources.length > 100 && (
                      <p className="border-t border-white/[0.06] p-4 text-xs text-slate-500">
                        Showing the first 100 matching sources. Refine your search to find a source.
                      </p>
                    )}
                  </section>
                )}

                
                
                {page === 'Ingestion' && (
                  <div className="mx-auto max-w-3xl space-y-6">
                    <section className="rounded-2xl border border-white/[0.08] bg-[#111827] p-6 sm:p-8">
                      <h3 className="text-xl font-semibold text-white">Ingest a log</h3>
                      <p className="mt-2 text-sm text-slate-400">
                        Submit a single log event directly to LogForge.
                      </p>

                      <form onSubmit={handleIngest} className="mt-6 space-y-5">
                        <div>
                          <label className="mb-2 block text-sm text-slate-300">
                            Registered source
                          </label>
                          <select
                            value={ingestSource}
                            onChange={(event) => setIngestSource(event.target.value)}
                            required
                            className="w-full rounded-xl border border-white/10 bg-[#111827] px-4 py-3 text-sm text-white outline-none focus:border-cyan-400/50"
                          >
                            <option value="">Select a source</option>
                            {sources.map((source, index) => (
                              <option
                                key={source.source_id ?? `${source.name}-${index}`}
                                value={source.name ?? ''}
                                disabled={!source.name}
                              >
                                {source.name ?? 'Unnamed source'}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="mb-2 block text-sm text-slate-300">
                            Severity
                          </label>
                          <select
                            value={ingestLevel}
                            onChange={(event) => setIngestLevel(event.target.value)}
                            className="w-full rounded-xl border border-white/10 bg-[#111827] px-4 py-3 text-sm text-white outline-none"
                          >
                            {['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map((level) => (
                              <option key={level} value={level}>{level}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="mb-2 block text-sm text-slate-300">
                            Log message
                          </label>
                          <textarea
                            value={ingestMessage}
                            onChange={(event) => setIngestMessage(event.target.value)}
                            placeholder="Describe the log event..."
                            required
                            rows={4}
                            className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400/50"
                          />
                        </div>

                        {ingestResult && (
                          <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
                            {ingestResult}
                          </p>
                        )}
                        {ingestError && (
                          <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
                            {ingestError}
                          </p>
                        )}

                        <button
                          type="submit"
                          disabled={ingestLoading}
                          className="w-full rounded-xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
                        >
                          {ingestLoading ? 'Submitting...' : 'Submit log'}
                        </button>
                      </form>
                    </section>

                    <section className="rounded-2xl border border-white/[0.08] bg-[#111827] p-6 sm:p-8">
                      <div className="flex items-center gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-400/10 text-cyan-300">
                          <span className="text-xl">↑</span>
                        </div>
                        <div>
                          <h3 className="text-xl font-semibold text-white">
                            Bulk log upload
                          </h3>
                          <p className="mt-1 text-sm text-slate-400">
                            Upload CSV or JSON containing up to 100 events.
                          </p>
                        </div>
                      </div>

                      <div className="mt-5 rounded-xl border border-white/[0.08] bg-black/20 p-4 text-sm text-slate-400">
                        <p>CSV columns: <code>source,level,message</code></p>
                        <p className="mt-2">JSON must be a list of event objects, each containing <code>source</code>, <code>level</code> and <code>message</code>.</p>
                        <p className="mt-2">Every source must already be registered.</p>
                      </div>

                      <form
                        className="mt-5 space-y-4"
                        onSubmit={handleFileUpload}
                      >
                        <label className="flex cursor-pointer flex-col items-center rounded-xl border border-dashed border-white/20 bg-black/10 px-5 py-8 text-center transition hover:border-cyan-400/50">
                          <span className="text-2xl">⇧</span>
                          <span className="mt-3 text-sm font-medium text-white">
                            {selectedFile ? selectedFile.name : 'Choose a CSV or JSON file'}
                          </span>
                          <span className="mt-1 text-xs text-slate-500">
                            .csv or .json
                          </span>
                          <input
                            type="file"
                            accept=".csv,.json,application/json,text/csv"
                            className="mt-4 block max-w-full text-sm text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-cyan-400/10 file:px-3 file:py-2 file:text-cyan-300"
                            onChange={(event) => {
                              setSelectedFile(event.target.files?.[0] ?? null)
                              setFileResult('')
                              setFileError('')
                            }}
                          />
                        </label>

                        {fileResult && (
                          <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
                            {fileResult}
                          </p>
                        )}
                        {fileError && (
                          <p className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
                            {fileError}
                          </p>
                        )}

                        <button
                          type="submit"
                          disabled={!selectedFile || fileLoading}
                          className="w-full rounded-xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {fileLoading ? 'Uploading and ingesting...' : 'Upload and ingest logs'}
                        </button>
                      </form>
                    </section>
                  </div>
                )}


                      
              </>
            )}
          </div>
          
          {selectedEvent && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
              onClick={() => {
                setSelectedEvent(null)
                setDetailError('')
              }}
            >
              <section
                role="dialog"
                aria-modal="true"
                aria-labelledby="event-details-title"
                className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-white/10 bg-[#111827] p-6 shadow-2xl"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2
                      id="event-details-title"
                      className="text-xl font-semibold text-white"
                    >
                      Log Details
                    </h2>
                    <p className="mt-1 break-all text-xs text-slate-400">
                      Event ID: {selectedEvent.event_id ?? '—'}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      setSelectedEvent(null)
                      setDetailError('')
                    }}
                    className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300 hover:bg-white/10"
                  >
                    Close ✕
                  </button>
                </div>

                {detailLoading && (
                  <p className="mt-5 text-sm text-cyan-300">
                    Loading complete event details...
                  </p>
                )}

                {detailError && (
                  <p className="mt-5 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
                    {detailError}
                  </p>
                )}

                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  {[
                    ['Severity', selectedEvent.severity],
                    ['Source', selectedEvent.source],
                    ['Timestamp', selectedEvent.observed_at],
                    ['Schema Version', selectedEvent.schema_version],
                    ['Raw Event ID', selectedEvent.raw_event_id],
                    ['Message', selectedEvent.message],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      className="min-w-0 rounded-xl border border-white/[0.08] bg-white/[0.03] p-4"
                    >
                      <p className="text-xs text-slate-500">{label}</p>
                      <p className="mt-2 break-words text-sm text-slate-200">
                        {value == null || value === '' ? '—' : String(value)}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="mt-6">
                  <h3 className="mb-3 font-semibold text-white">
                    Complete Event Data (JSON)
                  </h3>
                  <pre className="max-h-80 overflow-auto rounded-xl border border-white/[0.08] bg-black/30 p-4 text-xs leading-6 text-cyan-200">
                    {JSON.stringify(selectedEvent, null, 2)}
                  </pre>
                </div>
              </section>
            </div>
          )}

        </main>
      </div>
    </div>
  )
}


function LogTable({
  events,
  title,
  subtitle,
  emptyMessage,
  onEventClick,
}: {
  events: LogEvent[]
  title: string
  subtitle: string
  emptyMessage: string
  onEventClick: (event: LogEvent) => void
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-white/[0.08] bg-[#111827]">
      <div className="border-b border-white/[0.08] p-5">
        <h3 className="font-semibold text-white">{title}</h3>
        <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-white/[0.02] text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-5 py-4">Severity</th>
              <th className="px-5 py-4">Message</th>
              <th className="px-5 py-4">Source</th>
              <th className="px-5 py-4">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.06]">
            {events.map((event, index) => {
              const severity = String(event.severity ?? 'INFO').toUpperCase()

              return (
                <tr
                  key={event.event_id ?? `${event.observed_at}-${index}`}
                  onClick={() => onEventClick(event)}
                  title="Click to view log details"
                  className="cursor-pointer transition hover:bg-cyan-400/[0.06] focus:outline-none focus:bg-cyan-400/[0.06]"
                >
                  <td className="whitespace-nowrap px-5 py-4">
                    <span
                      className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold tracking-wide ${severityClass(severity)}`}
                    >
                      {severity}
                    </span>
                  </td>
                  <td className="min-w-64 max-w-lg px-5 py-4">
                    <p className="break-words text-slate-200">
                      {event.message ?? 'No message'}
                    </p>
                    <p className="mt-1 text-[10px] text-slate-600">
                      ID: {event.event_id ?? '—'}
                    </p>
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-slate-400">
                    {event.source ?? '—'}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-xs text-slate-500">
                    {formatTime(event.observed_at)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {events.length === 0 && (
        <p className="p-8 text-center text-sm text-slate-500">
          {emptyMessage}
        </p>
      )}
    </section>
  )
}

export default App