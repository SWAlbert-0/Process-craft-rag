import type {
  ApiErrorBody,
  ConnectionTestResult,
  DocumentItem,
  MessageResponse,
  RuntimeSettings,
  SettingsUpdate,
} from './types'

const API_ROOT = '/api/v1'

export class ApiError extends Error {
  code: string

  constructor(message: string, code = 'REQUEST_FAILED') {
    super(message)
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, init)
  if (!response.ok) {
    let body: ApiErrorBody = {}
    try {
      body = await response.json()
    } catch {
      // Keep the response generic when an upstream body is not JSON.
    }
    throw new ApiError(
      body.error?.message || `请求失败（HTTP ${response.status}）`,
      body.error?.code,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const result = await request<{ items: DocumentItem[] }>('/documents?page_size=100')
  return result.items
}

export async function uploadDocument(file: File): Promise<{ document: DocumentItem; task_id: string }> {
  const form = new FormData()
  form.append('file', file)
  return request('/documents', { method: 'POST', body: form })
}

export async function retryDocument(id: string): Promise<void> {
  await request(`/documents/${id}/retry`, { method: 'POST' })
}

export async function deleteFailedDocument(id: string): Promise<void> {
  await request(`/documents/${id}`, { method: 'DELETE' })
}

export async function getSettings(): Promise<RuntimeSettings> {
  return request('/settings')
}

export async function saveSettings(payload: SettingsUpdate): Promise<RuntimeSettings> {
  return request('/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function resetSettings(): Promise<RuntimeSettings> {
  return request('/settings', { method: 'DELETE' })
}

export async function testConnection(
  service: 'llm' | 'embedding' | 'rerank',
): Promise<ConnectionTestResult> {
  return request('/settings/test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service }),
  })
}

export async function createConversation(mode: 'qa' | 'craft_instruction'): Promise<string> {
  const result = await request<{ id: string }>('/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: '新会话', mode, document_ids: [] }),
  })
  return result.id
}

export async function askQuestion(
  conversationId: string,
  content: string,
  mode: 'qa' | 'craft_instruction',
  documentIds: string[],
): Promise<MessageResponse> {
  return request(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content,
      mode,
      document_ids: documentIds.length ? documentIds : undefined,
      client_request_id: crypto.randomUUID(),
    }),
  })
}

export async function health(): Promise<boolean> {
  try {
    const response = await fetch(`${API_ROOT}/health`)
    return response.ok
  } catch {
    return false
  }
}
