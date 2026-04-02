<template>
  <el-container class="layout-shell">
    <el-aside v-if="!isMobile" width="220px" class="sidebar">
      <div class="brand">115 同步控制台</div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/sources">同步源配置</el-menu-item>
        <el-menu-item index="/runs">运行记录</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header" :class="{ 'header-mobile': isMobile }">
        <div class="header-inner">
          <div class="header-leading">
            <el-button v-if="isMobile" circle @click="drawerVisible = true">
              <el-icon><Menu /></el-icon>
            </el-button>
            <div>
              <div class="title">本地目录同步到 115 网盘</div>
              <div class="subtitle">支持秒传、分片上传与定时任务管理</div>
            </div>
          </div>
        </div>
      </el-header>
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <el-drawer v-model="drawerVisible" direction="ltr" size="260px" class="mobile-drawer">
    <template #header>
      <div class="brand brand-mobile">115 同步控制台</div>
    </template>
    <el-menu :default-active="activeMenu" router @select="drawerVisible = false">
      <el-menu-item index="/sources">同步源配置</el-menu-item>
      <el-menu-item index="/runs">运行记录</el-menu-item>
    </el-menu>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Menu } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'

const route = useRoute()
const drawerVisible = ref(false)
const { isMobile } = useResponsive()

const activeMenu = computed(() => {
  if (route.path.startsWith('/runs')) {
    return '/runs'
  }
  return '/sources'
})

watch(
  () => route.fullPath,
  () => {
    drawerVisible.value = false
  },
)
</script>

<style scoped>
.layout-shell {
  min-height: 100vh;
}

.sidebar {
  background: #111827;
  color: #fff;
}

.brand {
  padding: 20px;
  font-size: 18px;
  font-weight: 700;
}

.brand-mobile {
  padding: 0;
  color: #111827;
}

.header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.header-inner {
  width: 100%;
}

.header-leading {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-mobile {
  padding-inline: 12px;
}

.title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
}

.subtitle {
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.layout-main {
  padding: 16px;
}

.mobile-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
}

@media (max-width: 768px) {
  .title {
    font-size: 17px;
    line-height: 1.4;
  }

  .subtitle {
    font-size: 12px;
  }

  .layout-main {
    padding: 12px;
  }
}
</style>
