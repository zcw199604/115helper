<template>
  <div>
    <PageHeader :title="pageTitle" description="配置同步目录、上传模式、后缀白名单与定时任务。" />

    <el-card>
      <el-form ref="formRef" :model="form" label-width="140px" class="source-form">
        <el-form-item label="配置名称">
          <el-input v-model="form.name" placeholder="例如：电影目录" />
        </el-form-item>
        <el-form-item label="本地目录">
          <el-input v-model="form.local_path" placeholder="例如：/data/movies" />
        </el-form-item>
        <el-form-item label="115 目标目录">
          <el-input v-model="form.remote_path" placeholder="例如：/同步上传/电影" />
        </el-form-item>
        <el-form-item label="上传模式">
          <el-select v-model="form.upload_mode" style="width: 100%">
            <el-option label="仅秒传" value="fast_only" />
            <el-option label="秒传优先，失败后分片" value="fast_then_multipart" />
            <el-option label="仅分片上传" value="multipart_only" />
          </el-select>
        </el-form-item>
        <el-form-item label="后缀白名单">
          <el-input
            v-model="form.suffix_rules_text"
            type="textarea"
            :rows="3"
            placeholder="一行一个，或用英文逗号分隔，例如：.mp4,.mkv"
          />
        </el-form-item>
        <el-form-item label="排除规则">
          <el-input
            v-model="form.exclude_rules_text"
            type="textarea"
            :rows="3"
            placeholder="例如：sample,.part"
          />
        </el-form-item>
        <el-form-item label="Cron 表达式">
          <el-input v-model="form.cron_expr" placeholder="留空表示仅手动执行，例如：0 */6 * * *" />
        </el-form-item>
        <el-form-item label="启用任务">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item>
          <el-space>
            <el-button type="primary" @click="handleSubmit">保存配置</el-button>
            <el-button @click="router.push('/sources')">返回列表</el-button>
          </el-space>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import { getSource, saveSource } from '@/api/sources'
import type { SourceFormInput } from '@/types/source'

const route = useRoute()
const router = useRouter()
const sourceId = computed(() => Number(route.params.id || 0))
const pageTitle = computed(() => (sourceId.value ? '编辑同步源' : '新增同步源'))

const form = reactive<SourceFormInput>({
  name: '',
  local_path: '',
  remote_path: '',
  upload_mode: 'fast_then_multipart',
  suffix_rules_text: '.mp4,.mkv',
  exclude_rules_text: '',
  cron_expr: '',
  enabled: true,
})

async function loadSource() {
  if (!sourceId.value) {
    return
  }
  const source = await getSource(sourceId.value)
  if (!source) {
    ElMessage.warning('未找到同步源，已返回列表')
    router.push('/sources')
    return
  }
  form.name = source.name
  form.local_path = source.local_path
  form.remote_path = source.remote_path
  form.upload_mode = source.upload_mode
  form.suffix_rules_text = source.suffix_rules.join(',')
  form.exclude_rules_text = source.exclude_rules.join(',')
  form.cron_expr = source.cron_expr ?? ''
  form.enabled = source.enabled
}

async function handleSubmit() {
  await saveSource(form, sourceId.value || undefined)
  ElMessage.success('配置已保存')
  router.push('/sources')
}

onMounted(loadSource)
</script>

<style scoped>
.source-form {
  max-width: 760px;
}
</style>
