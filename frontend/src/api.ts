const API_BASE_URL = '/api'

export type LogEvent = {
  event_id?: string | number
  raw_event_id?: string
  schema_version?: string
  source?: string
  severity?: string
  message?: string
  observed_at?: string
  [key: string]: unknown
}

export type LogSource = {
  source_id?: string
  name?: string
  source_type?: string
  created_at?: string
  [key: string]: unknown
}

export type EventsResponse = {
  count: number
  total: number
  limit: number
  offset: number
  events: LogEvent[]
}

export type SourcesResponse = {
  count: number
  sources: LogSource[]
}

export type HealthResponse = {
  status?: string
  service?: string
  database?: string
  [key: string]: unknown
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)

  if (!response.ok) {
    throw new Error(
      `API request failed: ${response.status} ${response.statusText}`,
    )
  }

  return response.json() as Promise<T>
}

export function getHealth() {
  return request<HealthResponse>('/health')
}

export function getMetrics() {
  return request<Record<string, unknown>>('/metrics')
}


export type EventFilters = {
  search?: string
  source?: string
  severity?: string
}

export function getEvents(
  limit = 50,
  offset = 0,
  filters: EventFilters = {},
) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })

  if (filters.search?.trim()) {
    params.set('search', filters.search.trim())
  }

  if (filters.source && filters.source !== 'ALL') {
    params.set('source', filters.source)
  }

  if (filters.severity && filters.severity !== 'ALL') {
    params.set('severity', filters.severity)
  }

  return request<EventsResponse>(`/events?${params.toString()}`)
}


export function getEventById(eventId: string | number) {
  return request<LogEvent>(
    `/events/${encodeURIComponent(String(eventId))}`,
  )
}


export function getSources() {
  return request<SourcesResponse>('/sources')
}


export type IngestLogPayload = {
  source: string
  level: string
  message: string
}

export async function ingestLog(payload: IngestLogPayload) {
  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : `Ingestion failed: ${response.status} ${response.statusText}`,
    )
  }

  return data
}


export async function uploadLogFile(file: File) {
  const extension = file.name.split('.').pop()?.toLowerCase()

  let endpoint: string

  if (extension === 'csv') {
    endpoint = '/ingest/csv'
  } else if (extension === 'json') {
    endpoint = '/ingest/file'
  } else {
    throw new Error('Only CSV and JSON files are supported.')
  }

  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    body: formData,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : `Upload failed: ${response.status} ${response.statusText}`,
    )
  }

  return data as {
    accepted: boolean
    count: number
    result: unknown[]
  }
}