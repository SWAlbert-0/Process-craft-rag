export interface DocumentItem {
  id: string
  name: string
  content_sha256: string
  size_bytes: number
  page_count: number | null
  chunk_count: number
  status: 'pending' | 'parsing' | 'indexing' | 'ready' | 'failed' | 'deleting'
  failure_stage: string | null
  failure_message: string | null
  index_version_id: string | null
  stage?: string
}

export interface Citation {
  label: number
  chunk_id: string
  document_id: string
  document_name: string
  page_start: number
  page_end: number
  excerpt: string
  rerank_score: number | null
  source_available: boolean
}

export interface RetrievalCandidate {
  chunk_id: string
  document_name: string
  page_start: number
  page_end: number
  dense_rank: number | null
  sparse_rank: number | null
  rrf_score: number
  rerank_score: number | null
}

export interface RetrievalDiagnostics {
  index_version_id: string
  dense: RetrievalCandidate[]
  sparse: RetrievalCandidate[]
  fusion: RetrievalCandidate[]
  rerank: RetrievalCandidate[]
  context_labels: number[]
  retrieval_ms: number
  generation_ms: number
  insufficient_evidence: boolean
}

export interface CraftStep {
  order: number
  operation: string
  equipment_tools: string
  parameters: string
  quality_requirements: string
  citations: number[]
}

export interface EvidenceText {
  text: string
  citations: number[]
}

export interface CraftInstruction {
  title: string
  workpiece: string
  assumptions: string[]
  missing_information: string[]
  preparation: string[]
  steps: CraftStep[]
  quality_checks: EvidenceText[]
  safety_notes: EvidenceText[]
  references: Citation[]
  disclaimer: string
}

export interface MessageResponse {
  id: string
  role: 'user' | 'assistant'
  status: string
  content: string
  structured_content: CraftInstruction | null
  citations: Citation[]
  retrieval_diagnostics: RetrievalDiagnostics | null
  insufficient_evidence?: boolean
  request_id: string
}

export interface ApiErrorBody {
  error?: {
    code: string
    message: string
    details?: { document_id?: string } | null
  }
}

export interface EditableSettings {
  llm_provider: string
  llm_base_url: string
  llm_model: string
  llm_timeout_seconds: number
  model_max_retries: number
  llm_max_output_tokens: number
  embedding_provider: string
  embedding_model: string
  embedding_dimensions: number
  embedding_batch_size: number
  rerank_provider: string
  rerank_model: string
  dashscope_region: string
  chunk_target_chars: number
  chunk_overlap_chars: number
  chunk_min_chars: number
  dense_top_k: number
  sparse_top_k: number
  rrf_k: number
  fusion_top_n: number
  rerank_top_n: number
  context_token_budget: number
  rerank_min_score: number
}

export interface RuntimeSettings extends EditableSettings {
  llm_api_key_configured: boolean
  dashscope_api_key_configured: boolean
  dashscope_workspace_configured: boolean
  runtime_override_active: boolean
}

export interface SettingsUpdate extends Partial<EditableSettings> {
  llm_api_key?: string
  dashscope_api_key?: string
  dashscope_workspace_id?: string
  clear_llm_api_key?: boolean
  clear_dashscope_api_key?: boolean
  clear_dashscope_workspace_id?: boolean
}

export interface ConnectionTestResult {
  service: 'llm' | 'embedding' | 'rerank'
  status: 'connected'
  latency_ms: number
  usage: Record<string, number>
}
