<template>
  <nav class="fixed bottom-0 left-0 right-0 bg-white/80 dark:bg-[#1c1c1d]/80 backdrop-blur-lg border-t-[0.5px] border-tg-separator pb-[env(safe-area-inset-bottom)] z-50">
    <div class="flex justify-around items-center h-[49px]">
      <router-link 
        v-for="tab in tabs" 
        :key="tab.path"
        :to="tab.path"
        class="flex-1 flex flex-col items-center justify-center h-full gap-[3px] text-[#8e8e93] dark:text-[#8e8e93]"
        active-class="!text-tg-button"
      >
        <span class="material-icons-round text-[26px] leading-none">{{ tab.icon }}</span>
        <span class="text-[10px] font-medium leading-none">{{ tab.label }}</span>
      </router-link>
    </div>
  </nav>
</template>

<script setup lang="ts">
const tabs = [
  { path: '/stats', icon: 'home', label: 'Главная' },
  { path: '/streak', icon: 'local_fire_department', label: 'Streak' },
  { path: '/leaderboard', icon: 'leaderboard', label: 'Топ' },
  { path: '/vocabulary', icon: 'menu_book', label: 'Словарь' },
  { path: '/settings', icon: 'settings', label: 'Настройки' },
]
</script>
