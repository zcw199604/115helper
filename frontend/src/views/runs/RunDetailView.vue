<template>
  <div>
    <PageHeader title="运行详情" description="查看文件级结果、任务级日志与失败原因。">
      <el-button @click="router.push('/runs')">返回列表</el-button>
    </PageHeader>

    <el-row :gutter="16" v-if="detail">
      <el-col :span="6">
        <el-card shadow="hover"><div class="stat-title">总文件数</div><div class="stat-value">{{ detail.summary.total_files }}</div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div class="stat-title">秒传成功</div><div class="stat-value">{{ detail.summary.fast_uploaded }}</div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div class="stat-title">分片成功</div><div class="stat-value">{{ detail.summary.multipart_uploaded }}</div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div class="stat-title">失败数</div><div class="stat-value danger">{{ detail.summary.failed }}</div></el-card>
      </el-col>
    </el-row>

    <el-card class="detail-card" v-loading="loading">
      <template #header>
        <div class="detail-header">
          <span>文件明细</span>
          <el-select v-model="actionFilter" placeholder="筛选结果类型" style="width: 220px">
            <el-option label="全部" value="all" />
            <el-option label="秒传成功" value="fast_uploaded" />
            <el-option label="分片成功" value="multipart_uploaded" />
            <el-option label="跳过" value="skipped" />
            <el-option label="失败" value="failed" />
          </el-select>
        </div>
      </template>

      <el-empty v-if="!detail" description="未找到对应运行记录" />
      <el-table v-else :data="filteredRecords">
        <el-table-column prop="relative_path" label="相对路径" min-width="240" />
        <el-table-column prop="suffix" label="后缀" width="110" />
        <el-table-column prop="action" label="结果类型" width="160" />
        <el-table-column prop="message" label="说明" min-width="220" />
        <el-table-column prop="synced_at" label="处理时间" min-width="170" />
      </el-table>
    </el-card>

    <el-card class="detail-card" v-loading="loading">
      <template #header>
        <div class="detail-header detail-header-stack">
          <div>
            <span>任务级日志</span>
            <el-tag size="small" :type="connectionTagType" class="status-tag">{{ connectionText }}</el-tag>
          </div>
          <el-select v-model="logLevelFilter" placeholder="筛选日志级别" style="width: 220px">
            <el-option label="全部" value="all" />
            <el-option label="信息" value="info" />
            <el-option label="警告" value="warning" />
            <el-option label="错误" value="error" />
            <el-option label="调试" value="debug" />
          </el-select>
        </div>
      </template>

      <el-empty v-if="!detail" description="暂无日志" />
      <div v-else ref="logContainerRef" class="log-timeline">
        <el-timeline>
          <el-timeline-item
            v-for="item in filteredLogs"
            :key="item.id"
            :timestamp="item.created_at"
            :type="timelineType(item.level)"
          >
            <div class="log-line">
              <div class="log-line-header">
                <el-tag size="small" :type="tagByLevel(item.level)">{{ item.level }}</el-tag>
                <span class="log-stage">{{ item.stage }}</span>
              </div>
              <div class="log-message">{{ item.message }}</div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import { getRunDetail } from '@/api/runs'
import { subscribeRunLogStream, type LogStreamClient } from '@/api/logStream'
import type { LogLevel, RunDetail, RunStatus, TaskLogRecord } from '@/types/run'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const detail = ref<RunDetail>()
const actionFilter = ref<'all' | 'fast_uploaded' | 'multipart_uploaded' | 'skipped' | 'failed'>('all')
const logLevelFilter = ref<'all' | LogLevel>('all')
const connectionState = ref<'idle' | 'connecting' | 'live' | 'closed' | 'error'>('idle')
const logContainerRef = ref<HTMLElement>()
let streamClient: LogStreamClient | null = null

const filteredRecords = computed(() => {
  if (!detail.value) {
    return []
  }
  if (actionFilter.value === 'all') {
    return detail.value.records
  }
  return detail.value.records.filter((item) => item.action === actionFilter.value)
})

const filteredLogs = computed(() => {
  if (!detail.value) {
    return []
  }
  const logs = detail.value.logs ?? []
  if (logLevelFilter.value === 'all') {
    return logs
  }
  return logs.filter((item) => item.level === logLevelFilter.value)
})

const connectionText = computed(() => {
  switch (connectionState.value) {
    case 'connecting':
      return '连接中'
    case 'live':
      return '实时推送中'
    case 'closed':
      return '已结束'
    case 'error':
      return '连接异常'
    default:
      return '未连接'
  }
})

const connectionTagType = computed(() => {
  switch (connectionState.value) {
    case 'live':
      return 'success'
    case 'connecting':
      return 'warning'
    case 'error':
      return 'danger'
    default:
      return 'info'
  }
})

function tagByLevel(level: LogLevel) {
  switch (level) {
    case 'error':
      return 'danger'
    case 'warning':
      return 'warning'
    case 'info':
      return 'success'
    default:
      return 'info'
  }
}

function timelineType(level: LogLevel) {
  switch (level) {
    case 'error':
      return 'danger'
    case 'warning':
      return 'warning'
    case 'info':
      return 'primary'
    default:
      return 'info'
  }
}

function isTerminalStatus(status?: RunStatus) {
  return status === 'success' || status === 'failed' || status === 'partial_failed' || status === 'cancelled'
}

function scrollLogsToBottom() {
  nextTick(() => {
    const el = logContainerRef.value
    if (!el) {
      return
    }
    el.scrollTop = el.scrollHeight
  })
}

function mergeLog(log: TaskLogRecord) {
  if (!detail.value) {
    return
  }
  const exists = detail.value.logs.some((item) => item.id === log.id)
  if (!exists) {
    detail.value.logs.push(log)
    scrollLogsToBottom()
  }
}

function closeStream() {
  if (streamClient) {
    streamClient.close()
    streamClient = null
  }
}

function startStream(runId: number) {
  closeStream()
  connectionState.value = 'connecting'
  streamClient = subscribeRunLogStream(runId, {
    onOpen: () => {
      connectionState.value = 'live'
    },
    onLog: (log) => {
      mergeLog(log)
    },
    onStatus: (status) => {
      if (status === 'heartbeat') {
        if (connectionState.value !== 'live') {
          connectionState.value = 'live'
        }
        return
      }
      if (detail.value) {
        detail.value.status = status as RunStatus
      }
      if (isTerminalStatus(status as RunStatus)) {
        connectionState.value = 'closed'
        closeStream()
      }
    },
    onError: () => {
      connectionState.value = 'error'
    },
  })
}

async function fetchDetail() {
  loading.value = true
  try {
    detail.value = await getRunDetail(Number(route.params.id))
    if (detail.value) {
      scrollLogsToBottom()
      if (!isTerminalStatus(detail.value.status)) {
        startStream(detail.value.id)
      } else {
        connectionState.value = 'closed'
      }
    }
  } finally {
    loading.value = false
  }
}

onMounted(fetchDetail)
onBeforeUnmount(() => {
  closeStream()
})
</script>

<style scoped>
.detail-card {
  margin-top: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.detail-header-stack {
  gap: 12px;
}

.status-tag {
  margin-left: 8px;
}

.stat-title {
  color: #6b7280;
  font-size: 13px;
}

.stat-value {
  margin-top: 8px;
  font-size: 30px;
  font-weight: 700;
}

.danger {
  color: #dc2626;
}

.log-timeline {
  max-height: 420px;
  overflow-y: auto;
  padding-top: 8px;
}

.log-line-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.log-stage {
  font-weight: 600;
  text-transform: capitalize;
}

.log-message {
  color: #374151;
  line-height: 1.6;
}
</style>
