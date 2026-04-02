import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const MOBILE_MAX_WIDTH = 768

export function useResponsive() {
  const windowWidth = ref<number>(typeof window === 'undefined' ? MOBILE_MAX_WIDTH + 1 : window.innerWidth)

  function updateWindowWidth() {
    if (typeof window === 'undefined') {
      return
    }
    windowWidth.value = window.innerWidth
  }

  onMounted(() => {
    updateWindowWidth()
    window.addEventListener('resize', updateWindowWidth)
  })

  onBeforeUnmount(() => {
    if (typeof window === 'undefined') {
      return
    }
    window.removeEventListener('resize', updateWindowWidth)
  })

  const isMobile = computed(() => windowWidth.value <= MOBILE_MAX_WIDTH)

  return {
    isMobile,
    windowWidth,
  }
}
