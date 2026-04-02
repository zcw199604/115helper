<template>
  <div class="page-header" :class="{ 'page-header-mobile': isMobile }">
    <div class="page-header-text">
      <div class="page-title">{{ title }}</div>
      <div v-if="description" class="page-description">{{ description }}</div>
    </div>
    <div class="page-header-actions" :class="{ 'page-header-actions-mobile': isMobile }">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useResponsive } from '@/composables/useResponsive'

defineProps<{
  title: string
  description?: string
}>()

const { isMobile } = useResponsive()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 16px;
}

.page-header-text {
  min-width: 0;
}

.page-header-actions {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
}

.page-description {
  margin-top: 4px;
  color: #6b7280;
}

.page-header-mobile {
  flex-direction: column;
  align-items: stretch;
}

.page-header-actions-mobile {
  width: 100%;
  justify-content: stretch;
}

.page-header-actions-mobile :deep(*) {
  width: 100%;
}
</style>
