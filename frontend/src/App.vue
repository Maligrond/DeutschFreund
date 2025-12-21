<script setup lang="ts">
/**
 * Главный компонент приложения.
 * Инициализация Telegram WebApp и навигация.
 */

import { onMounted, watch } from 'vue'
import { useTelegram } from './composables/useTelegram'
import BottomNav from './components/BottomNav.vue'

const { isReady, colorScheme } = useTelegram()

onMounted(() => {
  updateTheme()
})

watch(colorScheme, () => {
  updateTheme()
})

function updateTheme() {
  document.body.classList.remove('light', 'dark')
  document.body.classList.add(colorScheme.value)
  document.documentElement.classList.remove('light', 'dark')
  document.documentElement.classList.add(colorScheme.value)
}
</script>

<template>
  <div class="app" :class="colorScheme">
    <!-- Loading -->
    <div v-if="!isReady" class="min-h-screen flex items-center justify-center" style="background: var(--tg-theme-secondary-bg-color);">
      <div class="flex flex-col items-center gap-4">
        <div class="tg-spinner"></div>
        <p class="tg-hint text-sm">Загрузка...</p>
      </div>
    </div>
    
    <!-- Content -->
    <template v-else>
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
      
      <BottomNav />
    </template>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.app {
  min-height: 100vh;
  min-height: 100dvh;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', Roboto, sans-serif;
}
</style>
