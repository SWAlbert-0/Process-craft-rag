<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  getSettings,
  resetSettings as resetSettingsRequest,
  saveSettings,
  testConnection,
} from './api'
import type { RuntimeSettings, SettingsUpdate } from './types'

type ServiceName = 'llm' | 'embedding' | 'rerank'
type TestState = { kind: 'idle' | 'testing' | 'success' | 'error'; text: string }

const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const form = ref({
  llm_provider: 'deepseek',
  llm_base_url: 'https://api.deepseek.com',
  llm_model: 'deepseek-flash',
  llm_timeout_seconds: 90,
  model_max_retries: 2,
  llm_max_output_tokens: 8000,
  embedding_provider: 'dashscope',
  embedding_model: 'text-embedding-v4',
  embedding_dimensions: 1024,
  embedding_batch_size: 10,
  rerank_provider: 'dashscope',
  rerank_model: 'qwen3-rerank',
  dashscope_region: 'cn-beijing',
  chunk_target_chars: 900,
  chunk_overlap_chars: 120,
  chunk_min_chars: 120,
  dense_top_k: 20,
  sparse_top_k: 20,
  rrf_k: 60,
  fusion_top_n: 30,
  rerank_top_n: 8,
  context_token_budget: 5000,
  rerank_min_score: 0,
})
const flags = ref({
  llm_api_key_configured: false,
  dashscope_api_key_configured: false,
  dashscope_workspace_configured: false,
  runtime_override_active: false,
})
const secrets = reactive({
  llm_api_key: '',
  dashscope_api_key: '',
  dashscope_workspace_id: '',
  clear_llm_api_key: false,
  clear_dashscope_api_key: false,
  clear_dashscope_workspace_id: false,
})
const tests = reactive<Record<ServiceName, TestState>>({
  llm: { kind: 'idle', text: '' },
  embedding: { kind: 'idle', text: '' },
  rerank: { kind: 'idle', text: '' },
})

function applySettings(settings: RuntimeSettings) {
  const {
    llm_api_key_configured,
    dashscope_api_key_configured,
    dashscope_workspace_configured,
    runtime_override_active,
    ...values
  } = settings
  form.value = values
  flags.value = {
    llm_api_key_configured,
    dashscope_api_key_configured,
    dashscope_workspace_configured,
    runtime_override_active,
  }
  secrets.llm_api_key = ''
  secrets.dashscope_api_key = ''
  secrets.dashscope_workspace_id = ''
  secrets.clear_llm_api_key = false
  secrets.clear_dashscope_api_key = false
  secrets.clear_dashscope_workspace_id = false
}

function applyProviderPreset() {
  const presets: Record<string, { url: string; model: string }> = {
    deepseek: { url: 'https://api.deepseek.com', model: 'deepseek-flash' },
    kimi: { url: 'https://api.moonshot.cn/v1', model: 'kimi-k3' },
    glm: { url: 'https://api.z.ai/api/paas/v4', model: 'glm-5.3' },
    openai: { url: 'https://api.openai.com/v1', model: 'gpt-4.1-mini' },
  }
  const preset = presets[form.value.llm_provider]
  if (preset) {
    form.value.llm_base_url = preset.url
    form.value.llm_model = preset.model
  }
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    applySettings(await getSettings())
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '无法读取设置'
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const payload: SettingsUpdate = {
      ...form.value,
      clear_llm_api_key: secrets.clear_llm_api_key,
      clear_dashscope_api_key: secrets.clear_dashscope_api_key,
      clear_dashscope_workspace_id: secrets.clear_dashscope_workspace_id,
    }
    if (secrets.llm_api_key.trim()) payload.llm_api_key = secrets.llm_api_key.trim()
    if (secrets.dashscope_api_key.trim()) payload.dashscope_api_key = secrets.dashscope_api_key.trim()
    if (secrets.dashscope_workspace_id.trim()) {
      payload.dashscope_workspace_id = secrets.dashscope_workspace_id.trim()
    }
    applySettings(await saveSettings(payload))
    successMessage.value = '设置已保存。新任务和新提问将使用更新后的配置。'
    for (const service of Object.keys(tests) as ServiceName[]) {
      tests[service] = { kind: 'idle', text: '' }
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '设置保存失败'
  } finally {
    saving.value = false
  }
}

async function restoreDefaults() {
  if (!window.confirm('恢复环境变量中的默认配置？页面保存的运行时覆盖将被移除。')) return
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    applySettings(await resetSettingsRequest())
    successMessage.value = '已恢复环境变量配置。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '恢复默认配置失败'
  } finally {
    saving.value = false
  }
}

async function runTest(service: ServiceName) {
  tests[service] = { kind: 'testing', text: '正在连接' }
  try {
    const result = await testConnection(service)
    tests[service] = { kind: 'success', text: `连接成功 · ${result.latency_ms} ms` }
  } catch (error) {
    tests[service] = {
      kind: 'error',
      text: error instanceof Error ? error.message : '连接失败',
    }
  }
}

onMounted(load)
</script>

<template>
  <main class="settings-page">
    <header class="settings-heading">
      <div>
        <p class="eyebrow">LOCAL PREFERENCES</p>
        <h1>设置</h1>
        <p>配置模型服务与检索参数。页面只保存到本机服务端，不会在浏览器本地存储密钥。</p>
      </div>
      <div class="settings-actions">
        <button class="button-secondary" :disabled="saving" @click="restoreDefaults">恢复环境默认</button>
        <el-button type="primary" size="large" :loading="saving" @click="save">保存更改</el-button>
      </div>
    </header>

    <div v-if="loading" class="settings-loading">正在读取服务端设置…</div>
    <template v-else>
      <div class="configuration-state" :class="{ overridden: flags.runtime_override_active }">
        <span class="configuration-dot" />
        <div>
          <strong>{{ flags.runtime_override_active ? '正在使用页面保存的配置' : '正在使用环境变量配置' }}</strong>
          <p>{{ flags.runtime_override_active ? '运行时配置优先于 .env；恢复环境默认即可移除覆盖。' : '首次保存会创建服务端运行时覆盖，不会改写 .env 文件。' }}</p>
        </div>
      </div>

      <el-alert v-if="errorMessage" :title="errorMessage" type="error" @close="errorMessage = ''" />
      <el-alert v-if="successMessage" :title="successMessage" type="success" @close="successMessage = ''" />

      <div class="settings-layout">
        <div class="settings-sections">
          <section class="settings-card">
            <div class="settings-card-heading">
              <div class="settings-icon">AI</div>
              <div><h2>生成模型</h2><p>OpenAI Chat Completions 兼容服务，用于问答与加工草案。</p></div>
              <button class="test-button" :disabled="tests.llm.kind === 'testing'" @click="runTest('llm')">测试生成模型</button>
            </div>
            <p v-if="tests.llm.text" class="test-result" :class="`is-${tests.llm.kind}`">{{ tests.llm.text }}</p>
            <div class="settings-grid two-columns">
              <label class="setting-field">
                <span>服务商预设</span>
                <select v-model="form.llm_provider" class="setting-input" @change="applyProviderPreset">
                  <option value="deepseek">DeepSeek</option>
                  <option value="kimi">Kimi</option>
                  <option value="glm">GLM / Z.AI</option>
                  <option value="openai">OpenAI</option>
                  <option value="compatible">自定义兼容服务</option>
                </select>
              </label>
              <label class="setting-field"><span>模型名称</span><input v-model.trim="form.llm_model" class="setting-input" /></label>
              <label class="setting-field full-width"><span>Base URL</span><input v-model.trim="form.llm_base_url" class="setting-input mono-input" placeholder="https://api.deepseek.com" /></label>
              <label class="setting-field full-width secret-field">
                <span>API Key <em v-if="flags.llm_api_key_configured">已配置</em></span>
                <input v-model="secrets.llm_api_key" type="password" class="setting-input mono-input" autocomplete="off" :placeholder="flags.llm_api_key_configured ? '留空保持现有密钥不变' : '输入服务端 API Key'" />
                <label v-if="flags.llm_api_key_configured" class="clear-secret"><input v-model="secrets.clear_llm_api_key" type="checkbox" />清除已保存密钥</label>
              </label>
              <label class="setting-field"><span>请求超时（秒）</span><input v-model.number="form.llm_timeout_seconds" type="number" min="1" max="300" class="setting-input" /></label>
              <label class="setting-field"><span>失败重试次数</span><input v-model.number="form.model_max_retries" type="number" min="0" max="4" class="setting-input" /></label>
              <label class="setting-field"><span>最大输出 token</span><input v-model.number="form.llm_max_output_tokens" type="number" min="1024" max="32000" step="1024" class="setting-input" /><small>DeepSeek 推理 token 也计入该预算。</small></label>
            </div>
          </section>

          <section class="settings-card">
            <div class="settings-card-heading">
              <div class="settings-icon">R</div>
              <div><h2>嵌入与重排序</h2><p>阿里云百炼模型 API；嵌入与生成服务相互独立。</p></div>
            </div>
            <div class="settings-grid two-columns">
              <label class="setting-field"><span>服务地域</span><select v-model="form.dashscope_region" class="setting-input"><option value="cn-beijing">北京（cn-beijing）</option><option value="international">国际地域</option></select></label>
              <label class="setting-field secret-field">
                <span>Workspace ID <em v-if="flags.dashscope_workspace_configured">已配置</em></span>
                <input v-model="secrets.dashscope_workspace_id" type="password" class="setting-input mono-input" autocomplete="off" :placeholder="flags.dashscope_workspace_configured ? '留空保持不变' : '可选'" />
                <label v-if="flags.dashscope_workspace_configured" class="clear-secret"><input v-model="secrets.clear_dashscope_workspace_id" type="checkbox" />清除 Workspace ID</label>
              </label>
              <label class="setting-field full-width secret-field">
                <span>百炼 API Key <em v-if="flags.dashscope_api_key_configured">已配置</em></span>
                <input v-model="secrets.dashscope_api_key" type="password" class="setting-input mono-input" autocomplete="off" :placeholder="flags.dashscope_api_key_configured ? '留空保持现有密钥不变' : '输入百炼 API Key'" />
                <label v-if="flags.dashscope_api_key_configured" class="clear-secret"><input v-model="secrets.clear_dashscope_api_key" type="checkbox" />清除已保存密钥</label>
              </label>
            </div>
            <div class="model-subsection">
              <div class="model-subsection-heading"><div><h3>文本嵌入</h3><p>模型或维度变化需要重建向量索引。</p></div><button class="test-button" :disabled="tests.embedding.kind === 'testing'" @click="runTest('embedding')">测试嵌入</button></div>
              <p v-if="tests.embedding.text" class="test-result" :class="`is-${tests.embedding.kind}`">{{ tests.embedding.text }}</p>
              <div class="settings-grid three-columns">
                <label class="setting-field"><span>嵌入模型</span><input v-model.trim="form.embedding_model" class="setting-input mono-input" /></label>
                <label class="setting-field"><span>向量维度</span><input v-model.number="form.embedding_dimensions" type="number" min="128" max="4096" class="setting-input" /></label>
                <label class="setting-field"><span>批大小</span><input v-model.number="form.embedding_batch_size" type="number" min="1" max="10" class="setting-input" /></label>
              </div>
            </div>
            <div class="model-subsection">
              <div class="model-subsection-heading"><div><h3>重排序</h3><p>对融合后的候选重新估计相关性。</p></div><button class="test-button" :disabled="tests.rerank.kind === 'testing'" @click="runTest('rerank')">测试重排序</button></div>
              <p v-if="tests.rerank.text" class="test-result" :class="`is-${tests.rerank.kind}`">{{ tests.rerank.text }}</p>
              <label class="setting-field"><span>重排模型</span><input v-model.trim="form.rerank_model" class="setting-input mono-input" /></label>
            </div>
          </section>

          <section class="settings-card">
            <div class="settings-card-heading">
              <div class="settings-icon">K</div>
              <div><h2>检索与分块</h2><p>调整候选规模、融合和上下文预算。修改分块只影响之后创建的快照。</p></div>
            </div>
            <div class="settings-grid three-columns">
              <label class="setting-field"><span>目标分块字符</span><input v-model.number="form.chunk_target_chars" type="number" min="128" max="4000" class="setting-input" /></label>
              <label class="setting-field"><span>重叠字符</span><input v-model.number="form.chunk_overlap_chars" type="number" min="0" max="1000" class="setting-input" /></label>
              <label class="setting-field"><span>最小分块字符</span><input v-model.number="form.chunk_min_chars" type="number" min="16" max="1000" class="setting-input" /></label>
              <label class="setting-field"><span>稠密召回 top-k</span><input v-model.number="form.dense_top_k" type="number" min="1" max="100" class="setting-input" /></label>
              <label class="setting-field"><span>BM25 top-k</span><input v-model.number="form.sparse_top_k" type="number" min="1" max="100" class="setting-input" /></label>
              <label class="setting-field"><span>RRF 常数 k</span><input v-model.number="form.rrf_k" type="number" min="1" max="200" class="setting-input" /></label>
              <label class="setting-field"><span>融合候选数</span><input v-model.number="form.fusion_top_n" type="number" min="1" max="100" class="setting-input" /></label>
              <label class="setting-field"><span>重排候选数</span><input v-model.number="form.rerank_top_n" type="number" min="1" max="30" class="setting-input" /></label>
              <label class="setting-field"><span>上下文 token 预算</span><input v-model.number="form.context_token_budget" type="number" min="500" max="20000" step="100" class="setting-input" /></label>
              <label class="setting-field"><span>重排最低分数</span><input v-model.number="form.rerank_min_score" type="number" min="0" max="1" step="0.05" class="setting-input" /><small>更换模型后需重新校准，不建议直接沿用旧阈值。</small></label>
            </div>
          </section>
        </div>

        <aside class="settings-aside">
          <section>
            <p class="eyebrow">SECURITY</p>
            <h3>密钥如何保存</h3>
            <p>密钥通过 HTTPS/本机接口写入服务端 <code>data/config/runtime-settings.json</code>，不进入浏览器 localStorage、日志或 Git。GET 响应只包含“已配置”状态。本地文件不等同于加密密钥库，公网部署应使用鉴权和专用密钥管理工具。</p>
          </section>
          <section>
            <p class="eyebrow">APPLYING CHANGES</p>
            <h3>变更何时生效</h3>
            <p>模型与检索参数用于新提问和下一次入库。Worker 每次领取任务前重新读取配置；正在执行的任务不会被中途修改。</p>
          </section>
          <section class="settings-warning">
            <h3>索引兼容性</h3>
            <p>嵌入模型、向量维度或分块配置变化后，需要创建新快照。当前版本不会在保存设置时自动重建现有索引。</p>
          </section>
          <p class="settings-footnote">连接测试使用最近一次保存的配置，可能产生少量模型调用费用。</p>
        </aside>
      </div>
    </template>
  </main>
</template>

<style scoped>
.settings-page {
  width: min(1280px, 100%);
  margin: 0 auto;
  padding: 42px 36px 64px;
}

.settings-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 26px;
}

.settings-heading h1 {
  margin: 0;
  font-size: 36px;
  letter-spacing: -0.035em;
}

.settings-heading > div > p:last-child {
  margin: 9px 0 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.7;
}

.settings-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.button-secondary,
.test-button {
  padding: 9px 14px;
  color: var(--ink);
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 9px;
  font-size: 12px;
  cursor: pointer;
  transition: background 150ms ease, border-color 150ms ease;
}

.button-secondary:hover,
.test-button:hover {
  background: var(--surface-hover);
  border-color: var(--line-strong);
}

.button-secondary:disabled,
.test-button:disabled {
  opacity: 0.55;
}

.settings-loading {
  padding: 80px 0;
  color: var(--muted);
  text-align: center;
}

.configuration-state {
  margin-bottom: 18px;
  padding: 15px 18px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.configuration-dot {
  width: 8px;
  height: 8px;
  margin-top: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: #8d918c;
}

.configuration-state.overridden .configuration-dot {
  background: var(--accent);
}

.configuration-state strong {
  font-size: 13px;
}

.configuration-state p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

.settings-page > .el-alert {
  margin-bottom: 14px;
  border-radius: 10px;
}

.settings-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 22px;
  align-items: start;
}

.settings-sections {
  display: grid;
  gap: 18px;
}

.settings-card {
  padding: 25px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow-soft);
}

.settings-card-heading {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  margin-bottom: 23px;
}

.settings-card-heading > div:nth-child(2) {
  flex: 1;
}

.settings-card h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -0.015em;
}

.settings-card-heading p,
.model-subsection-heading p {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

.settings-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: var(--accent);
  background: var(--accent-soft);
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
}

.test-button {
  flex: 0 0 auto;
  color: var(--accent);
}

.test-result {
  margin: -12px 0 18px 49px;
  font-size: 11px;
}

.test-result.is-success {
  color: #32735a;
}

.test-result.is-error {
  color: #a5483d;
}

.test-result.is-testing {
  color: var(--muted);
}

.settings-grid {
  display: grid;
  align-items: start;
  gap: 17px;
}

.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.three-columns {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.setting-field {
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 7px;
  color: var(--ink);
  font-size: 12px;
}

.setting-field > span {
  min-height: 22px;
  display: flex;
  align-items: center;
  font-weight: 550;
}

.setting-field .setting-input {
  height: 41px;
  min-height: 41px;
}

.setting-field em {
  margin-left: 6px;
  padding: 2px 6px;
  color: #32735a;
  background: #eaf4ed;
  border-radius: 5px;
  font-size: 9px;
  font-style: normal;
  font-weight: 500;
}

.setting-field small {
  color: var(--muted);
  font-size: 10px;
  line-height: 1.5;
}

.full-width {
  grid-column: 1 / -1;
}

.secret-field {
  position: relative;
}

.clear-secret {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 10px;
  font-weight: 400;
  cursor: pointer;
}

.clear-secret input {
  accent-color: var(--accent);
}

.model-subsection {
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

.model-subsection-heading {
  margin-bottom: 16px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 15px;
}

.model-subsection h3,
.settings-aside h3 {
  margin: 0;
  font-size: 14px;
}

.settings-aside {
  display: grid;
  gap: 12px;
}

.settings-aside section {
  padding: 19px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 13px;
}

.settings-aside section > p:last-child {
  margin: 9px 0 0;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.8;
}

.settings-aside .settings-warning {
  background: var(--warning-soft);
  border-color: var(--warning-line);
}

.settings-footnote {
  margin: 4px 6px;
  color: var(--muted);
  font-size: 10px;
  line-height: 1.7;
}

.mono-input {
  font-family: var(--mono);
  font-size: 11px;
}

@media (max-width: 1000px) {
  .settings-layout {
    grid-template-columns: 1fr;
  }

  .settings-aside {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .settings-page {
    padding: 28px 16px 45px;
  }

  .settings-heading {
    display: grid;
  }

  .settings-actions {
    justify-content: flex-start;
  }

  .settings-card {
    padding: 20px 16px;
  }

  .settings-card-heading {
    flex-wrap: wrap;
  }

  .settings-card-heading .test-button {
    margin-left: 49px;
  }

  .two-columns,
  .three-columns,
  .settings-aside {
    grid-template-columns: 1fr;
  }

  .test-result {
    margin-left: 0;
  }
}
</style>
