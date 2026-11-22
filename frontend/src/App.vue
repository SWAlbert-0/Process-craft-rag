<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import SettingsView from './SettingsView.vue'
import {
  askQuestion,
  createConversation,
  deleteFailedDocument,
  health,
  listDocuments,
  retryDocument,
  uploadDocument,
} from './api'
import type {
  Citation,
  CraftInstruction,
  DocumentItem,
  MessageResponse,
} from './types'

type Mode = 'qa' | 'craft_instruction'
type ContentPart = { kind: 'text' | 'citation'; value: string; label?: number }

const documents = ref<DocumentItem[]>([])
const view = ref<'workbench' | 'settings'>('workbench')
const documentBusy = ref<string[]>([])
const selectedDocuments = ref<string[]>([])
const question = ref('')
const askedQuestion = ref('')
const mode = ref<Mode>('qa')
const result = ref<MessageResponse | null>(null)
const activeCitation = ref<number | null>(null)
const conversationId = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const asking = ref(false)
const loadingDocuments = ref(true)
const serviceReady = ref(false)
const errorMessage = ref('')
let pollTimer: number | undefined
let pollDelay = 1200

const readyDocuments = computed(() => documents.value.filter((item) => item.status === 'ready'))
const processing = computed(() =>
  documents.value.some((item) => ['pending', 'parsing', 'indexing'].includes(item.status)),
)
const canAsk = computed(
  () => question.value.trim().length > 0 && readyDocuments.value.length > 0 && !asking.value,
)
const craft = computed<CraftInstruction | null>(() => result.value?.structured_content || null)
const diagnostics = computed(() => result.value?.retrieval_diagnostics || null)
const processStages = computed(() => [
  {
    name: '双路召回',
    detail: diagnostics.value
      ? `稠密 ${diagnostics.value.dense.length} · BM25 ${diagnostics.value.sparse.length}`
      : '语义与关键词',
  },
  {
    name: 'RRF 融合',
    detail: diagnostics.value ? `${diagnostics.value.fusion.length} 个候选` : '按名次合并',
  },
  {
    name: '相关重排',
    detail: diagnostics.value ? `${diagnostics.value.rerank.length} 个候选` : '重估相关性',
  },
  {
    name: '引用核查',
    detail: result.value ? `${result.value.citations.length} 条原文快照` : '白名单约束',
  },
])

const examples = [
  'What is on-machine measurement?',
  'Which activities occur before, during, and after machining?',
  '请说明机床测量如何支持零件质量控制。',
]

function statusLabel(status: DocumentItem['status']): string {
  const labels: Record<DocumentItem['status'], string> = {
    pending: '等待处理',
    parsing: '解析分块',
    indexing: '构建双路索引',
    ready: '可检索',
    failed: '处理失败',
    deleting: '正在删除',
  }
  return labels[status]
}

function formatBytes(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`
}

function pageRange(citation: Citation): string {
  return citation.page_start === citation.page_end
    ? `PDF 第 ${citation.page_start} 页`
    : `PDF 第 ${citation.page_start}–${citation.page_end} 页`
}

function contentParts(text: string): ContentPart[] {
  const parts: ContentPart[] = []
  const pattern = /\[(\d+)\]/g
  let cursor = 0
  for (const match of text.matchAll(pattern)) {
    const index = match.index || 0
    if (index > cursor) parts.push({ kind: 'text', value: text.slice(cursor, index) })
    parts.push({ kind: 'citation', value: match[0], label: Number(match[1]) })
    cursor = index + match[0].length
  }
  if (cursor < text.length) parts.push({ kind: 'text', value: text.slice(cursor) })
  return parts
}

function selectCitation(label: number) {
  activeCitation.value = label
  document.getElementById(`citation-${label}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

async function refreshDocuments() {
  try {
    documents.value = await listDocuments()
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '无法读取文档列表'
  } finally {
    loadingDocuments.value = false
  }
}

function schedulePoll() {
  window.clearTimeout(pollTimer)
  if (!processing.value || document.hidden) return
  pollTimer = window.setTimeout(async () => {
    await refreshDocuments()
    pollDelay = processing.value ? Math.min(pollDelay * 1.5, 10000) : 1200
    schedulePoll()
  }, pollDelay)
}

async function handleFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  errorMessage.value = ''
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    errorMessage.value = '请选择 PDF 文件。'
    input.value = ''
    return
  }
  if (file.size > 50 * 1024 * 1024) {
    errorMessage.value = '文件超过 50 MB 上限。'
    input.value = ''
    return
  }
  uploading.value = true
  try {
    await uploadDocument(file)
    ElMessage.success('文件已接收，后台开始解析和索引')
    pollDelay = 1200
    await refreshDocuments()
    schedulePoll()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '上传失败，请重试'
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function retryFailedDocument(item: DocumentItem) {
  if (documentBusy.value.includes(item.id)) return
  documentBusy.value.push(item.id)
  errorMessage.value = ''
  try {
    await retryDocument(item.id)
    ElMessage.success('已重新加入处理队列')
    pollDelay = 1200
    await refreshDocuments()
    schedulePoll()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '重试失败'
  } finally {
    documentBusy.value = documentBusy.value.filter((id) => id !== item.id)
  }
}

async function removeFailedDocument(item: DocumentItem) {
  if (!window.confirm(`删除“${item.name}”的失败记录及暂存数据？此操作不会影响已发布快照。`)) return
  documentBusy.value.push(item.id)
  errorMessage.value = ''
  try {
    await deleteFailedDocument(item.id)
    selectedDocuments.value = selectedDocuments.value.filter((id) => id !== item.id)
    ElMessage.success('失败记录已删除')
    await refreshDocuments()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '删除失败'
  } finally {
    documentBusy.value = documentBusy.value.filter((id) => id !== item.id)
  }
}

async function submitQuestion() {
  if (!canAsk.value) return
  asking.value = true
  errorMessage.value = ''
  activeCitation.value = null
  result.value = null
  askedQuestion.value = question.value.trim()
  try {
    if (!conversationId.value) conversationId.value = await createConversation(mode.value)
    result.value = await askQuestion(
      conversationId.value,
      askedQuestion.value,
      mode.value,
      selectedDocuments.value,
    )
    question.value = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '生成失败，请稍后重试'
  } finally {
    asking.value = false
  }
}

function handleEnter(event: KeyboardEvent) {
  if (event.shiftKey) return
  event.preventDefault()
  void submitQuestion()
}

function useExample(example: string) {
  question.value = example
  mode.value = 'qa'
}

function handleVisibility() {
  if (document.hidden) window.clearTimeout(pollTimer)
  else {
    pollDelay = 1200
    void refreshDocuments().then(schedulePoll)
  }
}

onMounted(async () => {
  const [, healthy] = await Promise.all([refreshDocuments(), health()])
  serviceReady.value = healthy
  schedulePoll()
  document.addEventListener('visibilitychange', handleVisibility)
})

onUnmounted(() => {
  window.clearTimeout(pollTimer)
  document.removeEventListener('visibilitychange', handleVisibility)
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Process Craft 首页">
        <span class="brand-symbol">P<span>/</span>C</span>
        <span><strong>PROCESS CRAFT</strong><small>工艺证据工作台</small></span>
      </a>
      <nav class="main-nav" aria-label="主导航">
        <button :class="{ active: view === 'workbench' }" @click="view = 'workbench'">工作台</button>
        <button :class="{ active: view === 'settings' }" @click="view = 'settings'">设置</button>
      </nav>
      <div class="topbar-meta">
        <span class="iteration-badge">I1 · 核心链路</span>
        <span class="service-state" :class="{ online: serviceReady }">
          <i />{{ serviceReady ? '服务已连接' : '等待服务' }}
        </span>
      </div>
    </header>

    <main v-if="view === 'workbench'" class="workspace">
      <aside class="intake-panel">
        <div class="panel-heading">
          <p class="eyebrow">KNOWLEDGE SOURCE</p>
          <h2>工艺资料</h2>
          <p>导入文本型 PDF。只有完成双路索引的文档才参与回答。</p>
        </div>

        <input
          ref="fileInput"
          class="visually-hidden"
          type="file"
          accept="application/pdf,.pdf"
          @change="handleFile"
        />
        <button class="upload-target" :disabled="uploading" @click="fileInput?.click()">
          <span class="upload-plus">+</span>
          <span><strong>{{ uploading ? '正在接收文件' : '导入 PDF' }}</strong><small>单文件不超过 50 MB</small></span>
        </button>

        <div class="document-summary">
          <span>{{ readyDocuments.length }} 份可检索</span>
          <span>{{ documents.length }} 份资料</span>
        </div>

        <div v-if="loadingDocuments" class="document-empty">正在读取资料状态…</div>
        <div v-else-if="documents.length === 0" class="document-empty">
          <span class="empty-file">PDF</span>
          <p>知识库还是空的。</p>
          <small>建议先导入 I1 样例 NIST AMS 400-1。</small>
        </div>
        <div v-else class="document-list">
          <article
            v-for="item in documents"
            :key="item.id"
            class="document-card"
            :class="`is-${item.status}`"
          >
            <div class="document-status-line">
              <span class="status-dot" />
              {{ statusLabel(item.status) }}
              <span v-if="item.status === 'ready'" class="document-check">已核查</span>
            </div>
            <h3 :title="item.name">{{ item.name }}</h3>
            <p v-if="item.status === 'ready'">{{ item.page_count }} 页 · {{ item.chunk_count }} 个分块</p>
            <p v-else-if="item.status === 'failed'" class="failure-copy">{{ item.failure_message }}</p>
            <p v-else>后台处理中，请稍候</p>
            <label v-if="item.status === 'ready'" class="document-scope">
              <input v-model="selectedDocuments" type="checkbox" :value="item.id" />
              限定在本次检索范围
            </label>
            <div v-else-if="item.status === 'failed'" class="document-actions">
              <button :disabled="documentBusy.includes(item.id)" @click="retryFailedDocument(item)">重试解析</button>
              <button class="danger-action" :disabled="documentBusy.includes(item.id)" @click="removeFailedDocument(item)">删除记录</button>
            </div>
          </article>
        </div>

        <div class="scope-note">
          <strong>检索范围</strong>
          <span>{{ selectedDocuments.length ? `已限定 ${selectedDocuments.length} 份` : '全部就绪文档' }}</span>
          <button v-if="selectedDocuments.length" @click="selectedDocuments = []">恢复全部</button>
        </div>
      </aside>

      <section class="workbench">
        <div class="workbench-heading">
          <div>
            <p class="eyebrow">EVIDENCE BEFORE ANSWER</p>
            <h1>RAG生成</h1>
            <p>围绕已入库资料提问，逐条核对文档名、物理页码与检索原文。</p>
          </div>
          <span class="snapshot-label">版本化索引 · 引用可溯源</span>
        </div>

        <div class="question-console">
          <div class="mode-switch" aria-label="回答模式">
            <button :class="{ active: mode === 'qa' }" @click="mode = 'qa'">
              <span>知识问答</span><small>回答资料中的事实与流程</small>
            </button>
            <button :class="{ active: mode === 'craft_instruction' }" @click="mode = 'craft_instruction'">
              <span>加工指令草案</span><small>缺参待确认，保留人工审核</small>
            </button>
          </div>
          <label class="question-label" for="question-input">
            {{ mode === 'qa' ? '你的问题' : '零件与加工需求' }}
          </label>
          <textarea
            id="question-input"
            v-model="question"
            :disabled="asking"
            :placeholder="mode === 'qa' ? '输入一个可以由工艺 PDF 回答的问题…' : '说明零件、材料、图号与设备条件；未知信息可留待确认…'"
            rows="4"
            maxlength="4000"
            @keydown.enter="handleEnter"
          />
          <div class="console-footer">
            <span>Enter 发送 · Shift + Enter 换行</span>
            <el-button
              type="primary"
              size="large"
              :loading="asking"
              :disabled="!canAsk"
              @click="submitQuestion"
            >
              {{ asking ? '正在检索与生成' : mode === 'qa' ? '检索并回答' : '生成指令草案' }}
            </el-button>
          </div>
          <p v-if="readyDocuments.length === 0 && !loadingDocuments" class="console-hint">
            请先等待至少一份文档进入“可检索”状态。
          </p>
        </div>

        <el-alert
          v-if="errorMessage"
          :title="errorMessage"
          type="error"
          :closable="true"
          @close="errorMessage = ''"
        />

        <div class="process-rail" :class="{ active: asking || result }" aria-label="本次检索处理链路">
          <template v-for="(stage, index) in processStages" :key="stage.name">
            <div class="process-stage">
              <span class="stage-index">0{{ index + 1 }}</span>
              <div><strong>{{ stage.name }}</strong><small>{{ stage.detail }}</small></div>
            </div>
            <span v-if="index < processStages.length - 1" class="stage-connector" />
          </template>
        </div>

        <div v-if="asking" class="waiting-state" aria-live="polite">
          <span class="waiting-line" />
          <p>正在执行真实双路检索、重排序和模型生成。</p>
          <small>不会跳过重排，也不会用无关引用填充答案。</small>
        </div>

        <div v-else-if="result" class="answer-layout">
          <article class="answer-panel">
            <div class="answer-heading">
              <div>
                <p class="eyebrow">{{ mode === 'qa' ? 'GROUNDED ANSWER' : 'PROCESS DRAFT' }}</p>
                <h2>{{ mode === 'qa' ? '回答' : craft?.title }}</h2>
              </div>
              <span v-if="result.insufficient_evidence" class="insufficient-badge">证据不足</span>
            </div>
            <p class="asked-question">{{ askedQuestion }}</p>

            <div v-if="mode === 'qa'" class="answer-copy">
              <template v-for="(part, index) in contentParts(result.content)" :key="index">
                <button
                  v-if="part.kind === 'citation'"
                  class="inline-citation"
                  @click="selectCitation(part.label!)"
                >{{ part.value }}</button>
                <span v-else>{{ part.value }}</span>
              </template>
            </div>

            <div v-else-if="craft" class="craft-result">
              <dl class="workpiece-info">
                <div><dt>零件与已知条件</dt><dd>{{ craft.workpiece }}</dd></div>
                <div v-if="craft.assumptions.length"><dt>明确前提</dt><dd>{{ craft.assumptions.join('；') }}</dd></div>
              </dl>
              <section v-if="craft.missing_information.length" class="missing-section">
                <h3>生成前仍需确认</h3>
                <ul><li v-for="item in craft.missing_information" :key="item">{{ item }}</li></ul>
              </section>
              <section v-if="craft.preparation.length">
                <h3>准备事项</h3>
                <ul><li v-for="item in craft.preparation" :key="item">{{ item }}</li></ul>
              </section>
              <section v-if="craft.steps.length">
                <h3>工序与工步</h3>
                <div class="step-list">
                  <div v-for="step in craft.steps" :key="step.order" class="craft-step">
                    <span class="step-order">{{ String(step.order).padStart(2, '0') }}</span>
                    <div>
                      <h4>{{ step.operation }}</h4>
                      <dl>
                        <div><dt>设备刀具</dt><dd>{{ step.equipment_tools }}</dd></div>
                        <div><dt>参数</dt><dd>{{ step.parameters }}</dd></div>
                        <div><dt>质量要求</dt><dd>{{ step.quality_requirements }}</dd></div>
                      </dl>
                      <button
                        v-for="label in step.citations"
                        :key="label"
                        class="inline-citation"
                        @click="selectCitation(label)"
                      >[{{ label }}]</button>
                    </div>
                  </div>
                </div>
              </section>
              <section v-if="craft.quality_checks.length">
                <h3>质量检查</h3>
                <div v-for="item in craft.quality_checks" :key="item.text" class="evidence-row">
                  {{ item.text }}
                  <button v-for="label in item.citations" :key="label" class="inline-citation" @click="selectCitation(label)">[{{ label }}]</button>
                </div>
              </section>
              <section v-if="craft.safety_notes.length">
                <h3>安全注意事项</h3>
                <div v-for="item in craft.safety_notes" :key="item.text" class="evidence-row">
                  {{ item.text }}
                  <button v-for="label in item.citations" :key="label" class="inline-citation" @click="selectCitation(label)">[{{ label }}]</button>
                </div>
              </section>
            </div>

            <div v-if="diagnostics" class="timing-note">
              检索 {{ diagnostics.retrieval_ms }} ms · 生成 {{ diagnostics.generation_ms }} ms
              <span>快照 {{ diagnostics.index_version_id.slice(0, 8) }}</span>
            </div>
            <div class="review-notice">
              <strong>人工审核边界</strong>
              <p>{{ craft?.disclaimer || 'AI 辅助生成的工艺建议，必须由工艺人员审核，不可直接用于生产控制。' }}</p>
            </div>
          </article>

          <aside class="citation-panel" aria-label="回答引用">
            <div class="citation-heading">
              <div><p class="eyebrow">SOURCE EXCERPTS</p><h2>原文依据</h2></div>
              <span>{{ result.citations.length }}</span>
            </div>
            <div v-if="result.citations.length === 0" class="no-citations">
              本次没有可支持答案的原文。系统不会创建引用。
            </div>
            <article
              v-for="citation in result.citations"
              :id="`citation-${citation.label}`"
              :key="citation.label"
              class="citation-card"
              :class="{ selected: activeCitation === citation.label }"
            >
              <button class="citation-number" @click="activeCitation = citation.label">[{{ citation.label }}]</button>
              <div class="citation-body">
                <h3>{{ citation.document_name }}</h3>
                <p class="page-label">{{ pageRange(citation) }}</p>
                <blockquote>{{ citation.excerpt }}</blockquote>
                <a
                  :href="`/api/v1/documents/${citation.document_id}/content#page=${citation.page_start}`"
                  target="_blank"
                  rel="noopener"
                >打开原始 PDF 对应页 <span>↗</span></a>
              </div>
            </article>
          </aside>
        </div>

        <div v-else class="empty-answer">
          <div class="empty-answer-mark" aria-hidden="true"><span>问</span><i /><span>据</span></div>
          <div>
            <h2>让每一次回答都能回到原文。</h2>
            <p>可以从以下 A4 样例问题开始，或输入自己的问题。</p>
            <div class="example-list">
              <button v-for="example in examples" :key="example" @click="useExample(example)">
                {{ example }}<span>→</span>
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
    <SettingsView v-else />

    <footer class="app-footer">
      <span>PROCESS CRAFT RAG · I1</span>
      <p>输出仅供工艺人员审核，不直接下发机床或替代正式工艺规程。</p>
    </footer>
  </div>
</template>
