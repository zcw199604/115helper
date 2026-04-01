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
        <el-form-item label="远端防重">
          <el-select v-model="form.duplicate_check_mode" style="width: 100%">
            <el-option label="关闭" value="none" />
            <el-option label="按文件名跳过" value="name" />
            <el-option label="按 SHA1 跳过" value="sha1" />
          </el-select>
          <div class="form-tip">开启后会优先读取本地 SQLite 中的远端目录缓存，再按所选模式判断是否跳过。</div>
        </el-form-item>
        <el-form-item label="强制同步远端目录文件">
          <el-switch v-model="form.force_refresh_remote_cache" />
          <div class="form-tip">开启后，每次执行任务都会强制调用 115 接口刷新目标目录缓存；关闭时优先复用本地 SQLite 缓存。</div>
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
  duplicate_check_mode: 'none',
  force_refresh_remote_cache: false,
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
  form.duplicate_check_mode = source.duplicate_check_mode
  form.force_refresh_remote_cache = source.force_refresh_remote_cache
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

.form-tip {
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
</style>
