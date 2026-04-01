<template>
  <div>
    <PageHeader title="运行记录" description="查看手动执行与 Cron 任务的运行结果。" />

    <el-card>
      <el-table :data="runs" v-loading="loading">
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
import type { JobRun, RunStatus } from '@/types/run'

const router = useRouter()
const loading = ref(false)
const runs = ref<JobRun[]>([])

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
