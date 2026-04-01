<template>
  <el-container class="layout-shell">
    <el-aside width="220px" class="sidebar">
      <div class="brand">115 同步控制台</div>
      <el-menu :default-active="activeMenu" router>
        <el-menu-item index="/sources">同步源配置</el-menu-item>
        <el-menu-item index="/runs">运行记录</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div>
          <div class="title">本地目录同步到 115 网盘</div>
          <div class="subtitle">支持秒传、分片上传与定时任务管理</div>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => {
  if (route.path.startsWith('/runs')) {
    return '/runs'
  }
  return '/sources'
})
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

.header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
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
</style>
