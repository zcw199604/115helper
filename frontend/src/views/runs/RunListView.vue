<template>
  <div>
    <PageHeader title="运行记录" description="查看手动执行与 Cron 任务的运行结果。" />

    <el-card>
      <div v-if="isMobile" v-loading="loading" class="mobile-card-list">
        <el-empty v-if="!runs.length" description="暂无运行记录" />
        <el-card v-for="item in runs" :key="item.id" shadow="hover" class="mobile-data-card">
          <div class="mobile-data-card__header">
            <div class="mobile-data-card__title">运行 #{{ item.id }}</div>
            <el-tag :type="tagType(item.status)">{{ item.status }}</el-tag>
          </div>
          <div class="mobile-data-card__meta">
            <div><span class="label">同步源：</span>{{ item.source_name }}</div>
            <div><span class="label">触发方式：</span>{{ item.trigger_type }}</div>
            <div><span class="label">开始时间：</span>{{ item.started_at }}</div>
            <div><span class="label">结果摘要：</span></div>
            <div class="summary-text">
              总数 {{ item.summary.total_files }} / 秒传 {{ item.summary.fast_uploaded }} /
              分片 {{ item.summary.multipart_uploaded }} / 跳过 {{ item.summary.skipped }} /
              失败 {{ item.summary.failed }}
            </div>
          </div>
          <div class="mobile-action-grid">
            <el-button type="primary" plain @click="router.push(`/runs/${item.id}`)">详情</el-button>
            <el-button type="warning" plain @click="handleRetry(item.id)">重试</el-button>
            <el-button v-if="item.status === 'running' || item.status === 'pending'" type="danger" plain @click="handleCancel(item.id)">取消</el-button>
          </div>
        </el-card>
      </div>

      <el-table v-else :data="runs" v-loading="loading">
        <el-table-column prop="id" label="运行 ID" width="110" />
        <el-table-column prop="source_name" label="同步源" min-width="140" />
        <el-table-column prop="trigger_type" label="触发方式" width="120" />
        <el-table-column label="状态" width="140">
          <template #default="scope">
            <el-tag :type="tagType(scope.row.status)">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果摘要" min-width="260">
          <template #default="scope">
            总数 {{ scope.row.summary.total_files }} / 秒传 {{ scope.row.summary.fast_uploaded }} /
            分片 {{ scope.row.summary.multipart_uploaded }} / 跳过 {{ scope.row.summary.skipped }} /
            失败 {{ scope.row.summary.failed }}
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" min-width="160" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="scope">
            <el-space>
              <el-button link type="primary" @click="router.push(`/runs/${scope.row.id}`)">详情</el-button>
              <el-button link type="warning" @click="handleRetry(scope.row.id)">重试</el-button>
              <el-button
                v-if="scope.row.status === 'running' || scope.row.status === 'pending'"
                link
                type="danger"
                @click="handleCancel(scope.row.id)"
              >
                取消
              </el-button>
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
import { cancelRun, listRuns, retryRun } from '@/api/runs'
import { useResponsive } from '@/composables/useResponsive'
import type { JobRun, RunStatus } from '@/types/run'

const router = useRouter()
const loading = ref(false)
const runs = ref<JobRun[]>([])
const { isMobile } = useResponsive()

function tagType(status: RunStatus) {
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

async function fetchRuns() {
  loading.value = true
  try {
    runs.value = await listRuns()
  } finally {
    loading.value = false
  }
}

async function handleRetry(id: number) {
  const run = await retryRun(id)
  ElMessage.success('已创建后台重试任务')
  router.push(`/runs/${run.id ?? run.run_id}`)
}

async function handleCancel(id: number) {
  await cancelRun(id)
  ElMessage.success('已提交取消请求')
  await fetchRuns()
}

onMounted(fetchRuns)
</script>
