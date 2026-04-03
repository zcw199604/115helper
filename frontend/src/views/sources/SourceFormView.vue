<template>
  <div class="source-form page-shell">
    <PageHeader :title="pageTitle" description="配置同步目录、上传模式、后缀白名单与定时任务。" />

    <el-card shadow="never" :body-style="{ padding: isMobile ? '18px 16px' : '24px' }">
      <el-form label-position="top" :model="form">
        <el-form-item label="任务名称">
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
        <el-form-item label="执行方式">
          <el-select v-model="form.upload_flow_mode" style="width: 100%">
            <el-option label="插件对齐" value="plugin_aligned" />
            <el-option label="批处理缓存兼容模式" value="batch_cached" />
          </el-select>
          <div class="form-tip">插件对齐模式会按文件逐个准备目录并在上传后轮询确认；批处理缓存模式保留旧版“预创建目录 + 目录缓存预热”行为。</div>
        </el-form-item>
        <el-form-item label="后缀白名单">
          <el-select
            v-model="form.suffix_rules"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            placeholder="请选择允许同步的文件后缀"
            style="width: 100%"
          >
            <el-option v-for="item in suffixOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <div class="form-tip">支持多选，未选择时表示不过滤任何后缀。</div>
        </el-form-item>
        <el-form-item label="排除规则">
          <el-select
            v-model="form.exclude_rules"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            placeholder="请选择要排除的规则"
            style="width: 100%"
          >
            <el-option v-for="item in excludeOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <div class="form-tip">支持多选，规则会按通配模式匹配相对路径。</div>
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
          <div class="form-tip">开启后会按需读取目标目录文件列表，再按所选模式判断是否跳过。</div>
        </el-form-item>
        <el-form-item label="强制同步远端目录文件" class="switch-item">
          <div class="switch-field">
            <el-switch v-model="form.force_refresh_remote_cache" />
            <div class="form-tip">开启后，每次执行任务都会强制调用 115 接口刷新当前目标目录文件列表；关闭时优先复用本地 SQLite 缓存。</div>
          </div>
        </el-form-item>
        <el-form-item label="启用任务" class="switch-item">
          <div class="switch-field">
            <el-switch v-model="form.enabled" />
          </div>
        </el-form-item>
        <el-form-item>
          <div class="form-actions">
            <el-button type="primary" @click="handleSubmit">保存配置</el-button>
            <el-button @click="router.push('/sources')">返回列表</el-button>
          </div>
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
import { useResponsive } from '@/composables/useResponsive'
import { getSource, saveSource } from '@/api/sources'
import type { SourceFormInput } from '@/types/source'

const route = useRoute()
const router = useRouter()
const { isMobile } = useResponsive()
const sourceId = computed(() => Number(route.params.id || 0))
const pageTitle = computed(() => (sourceId.value ? '编辑同步源' : '新增同步源'))

const suffixOptions = ['.mp4', '.mkv', '.avi', '.ts', '.m2ts', '.mov', '.wmv', '.flv', '.mpg', '.mpeg', '.iso', '.rmvb', '.srt', '.ass', '.ssa', '.sub']
const excludeOptions = ['sample*', '*.part', '*.tmp', '*.aria2', '*.torrent', '@eaDir/*', '.DS_Store', 'Thumbs.db', 'System Volume Information/*', '$RECYCLE.BIN/*']

const form = reactive<SourceFormInput>({
  name: '',
  local_path: '',
  remote_path: '',
  upload_mode: 'fast_then_multipart',
  upload_flow_mode: 'plugin_aligned',
  suffix_rules: ['.mp4', '.mkv'],
  exclude_rules: [],
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
  form.upload_flow_mode = source.upload_flow_mode
  form.suffix_rules = source.suffix_rules
  form.exclude_rules = source.exclude_rules
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

.switch-item :deep(.el-form-item__content) {
  align-items: flex-start;
}

.switch-field {
  width: 100%;
}

.form-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .source-form {
    max-width: 100%;
  }

  .form-actions {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>
