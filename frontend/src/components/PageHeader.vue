<template>
  <div class="page-header">
    <div>
      <div class="page-title">{{ title }}</div>
      <div v-if="description" class="page-description">{{ description }}</div>
    </div>
    <div>
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 16px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
}

.page-description {
  margin-top: 4px;
  color: #6b7280;
}
</style>
