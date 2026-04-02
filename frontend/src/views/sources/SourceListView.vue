<template>
  <div>
    <PageHeader title="多任务管理" description="管理多个同步任务的目录映射、定时规则与最近执行状态。">
      <el-button type="primary" @click="router.push('/sources/new')">新增任务</el-button>
    </PageHeader>

    <el-card>
      <div v-if="isMobile" v-loading="loading" class="mobile-card-list">
        <el-empty v-if="!sources.length" description="暂无同步任务" />
        <el-card v-for="item in sources" :key="item.id" shadow="hover" class="mobile-data-card">
          <div class="mobile-data-card__header">
            <div class="mobile-data-card__title">{{ item.name }}</div>
            <el-tag :type="tagType(item.schedule_state?.last_run_status)">
              {{ getStatusText(item.schedule_state?.last_run_status) }}
            </el-tag>
          </div>
          <div class="mobile-data-card__meta">
            <div><span class="label">源目录：</span>{{ item.local_path }}</div>
            <div><span class="label">目标目录：</span>{{ item.remote_path }}</div>
            <div><span class="label">定时规则：</span>{{ item.cron_expr || '仅手动执行' }}</div>
            <div><span class="label">最近执行：</span>{{ item.schedule_state?.last_run_at || '暂无' }}</div>
            <div><span class="label">下次执行：</span>{{ item.schedule_state?.next_run_time || '未调度' }}</div>
          </div>
          <div class="mobile-data-card__footer">
            <div class="mobile-switch-row">
              <span>启用任务</span>
              <el-switch :model-value="item.enabled" @change="(value: string | number | boolean) => handleToggle(item.id, value)" />
            </div>
            <div class="mobile-action-grid">
              <el-button type="primary" plain @click="router.push(`/sources/${item.id}/edit`)">编辑</el-button>
              <el-button type="success" plain @click="handleRun(item.id)">立即执行</el-button>
              <el-button plain @click="router.push('/runs')">运行记录</el-button>
            </div>
          </div>
        </el-card>
      </div>

      <el-table v-else :data="sources" v-loading="loading">
        <el-table-column prop="name" label="任务名称" min-width="160" />
        <el-table-column prop="local_path" label="源目录" min-width="220" />
        <el-table-column prop="remote_path" label="目标 115 目录" min-width="200" />
        <el-table-column prop="cron_expr" label="定时规则" min-width="140">
          <template #default="scope">
            {{ scope.row.cron_expr || '仅手动执行' }}
          </template>
        </el-table-column>
        <el-table-column label="启用状态" width="110">
          <template #default="scope">
            <el-switch :model-value="scope.row.enabled" @change="(value: string | number | boolean) => handleToggle(scope.row.id, value)" />
          </template>
        </el-table-column>
        <el-table-column label="最近执行时间" min-width="170">
          <template #default="scope">
            {{ scope.row.schedule_state?.last_run_at || '暂无' }}
          </template>
        </el-table-column>
        <el-table-column label="下次执行时间" min-width="170">
          <template #default="scope">
            {{ scope.row.schedule_state?.next_run_time || '未调度' }}
          </template>
        </el-table-column>
        <el-table-column label="最近执行状态" width="130">
          <template #default="scope">
            <el-tag :type="tagType(scope.row.schedule_state?.last_run_status)">
              {{ getStatusText(scope.row.schedule_state?.last_run_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="scope">
            <el-space>
              <el-button link type="primary" @click="router.push(`/sources/${scope.row.id}/edit`)">编辑</el-button>
              <el-button link type="success" @click="handleRun(scope.row.id)">立即执行</el-button>
              <el-button link @click="router.push('/runs')">运行记录</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import { listSources, triggerSourceRun, toggleTaskEnabled } from '@/api/sources'
import { useResponsive } from '@/composables/useResponsive'
import type { RunStatus } from '@/types/run'
import type { SyncSource } from '@/types/source'

const router = useRouter()
const loading = ref(false)
const sources = ref<SyncSource[]>([])
const { isMobile } = useResponsive()

function tagType(status?: RunStatus | null) {
  switch (status) {
    case 'success':
      return 'success'
    case 'partial_failed':
      return 'warning'
    case 'failed':
      return 'danger'
    case 'running':
      return 'primary'
    case 'pending':
      return 'warning'
    default:
      return 'info'
  }
}

function getStatusText(status?: RunStatus | null) {
  return status || '暂无'
}

async function fetchData() {
  loading.value = true
  try {
    sources.value = await listSources()
  } finally {
    loading.value = false
  }
}

async function handleRun(id: number) {
  const run = await triggerSourceRun(id)
  ElMessage.success('任务已进入后台执行')
  router.push(`/runs/${run.id ?? run.run_id}`)
}

async function handleToggle(id: number, enabled: string | number | boolean) {
  await toggleTaskEnabled(id, Boolean(enabled))
  ElMessage.success(Boolean(enabled) ? '任务已启用' : '任务已停用')
  await fetchData()
}

onMounted(fetchData)
</script>
