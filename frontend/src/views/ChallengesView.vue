<template>
  <div class="min-h-screen bg-tg-secondary pb-24">
    <!-- Header -->
    <div class="px-4 pt-4 pb-2 bg-tg-secondary sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <h1 class="text-[34px] font-bold text-tg-text tracking-tight leading-tight">Челленджи</h1>
    </div>

    <!-- Active Challenge Card -->
    <div class="mt-4 px-4">
      <div v-if="activeChallenge" class="bg-tg-bg rounded-[10px] p-5 shadow-sm border border-tg-separator/20">
        <div class="flex items-start justify-between mb-3">
          <div class="px-2 py-0.5 rounded-[5px] bg-tg-secondary text-ios-caption text-tg-hint uppercase font-bold tracking-wide">
            {{ activeChallenge.topic_name }}
          </div>
          <span class="text-ios-caption text-tg-button font-medium">{{ activeChallenge.challenge_type }}</span>
        </div>
        
        <h3 class="text-[20px] font-semibold text-tg-text leading-snug mb-2">{{ activeChallenge.title }}</h3>
        <p class="text-[15px] text-tg-hint leading-normal mb-4">{{ activeChallenge.description }}</p>
        
        <button 
          @click="goToChat" 
          class="w-full bg-tg-button text-white font-semibold py-3 rounded-[10px] text-[17px] active:opacity-80"
        >
          Начать выполнение
        </button>
      </div>

      <div v-else class="bg-tg-bg rounded-[10px] p-8 text-center">
        <div class="text-[50px] mb-2">🎯</div>
        <h3 class="text-[20px] font-semibold text-tg-text mb-2">Нет активного задания</h3>
        <p class="text-tg-hint text-ios-body mb-6">Получите новое задание, чтобы заработать XP и прокачать немецкий.</p>
        <button 
          @click="requestChallenge" 
          :disabled="remainingToday <= 0"
          class="w-full bg-tg-button text-white font-semibold py-3 rounded-[10px] text-[17px] active:opacity-80 disabled:opacity-50"
        >
          Получить челлендж ({{ remainingToday }}/{{ maxPerDay }})
        </button>
      </div>
    </div>

    <!-- Stats Group -->
    <div class="mt-6 px-4">
      <h2 class="px-4 mb-2 text-ios-footnote uppercase text-tg-hint font-medium">Прогресс</h2>
      <div class="bg-tg-bg rounded-[10px] overflow-hidden">
         <div class="pl-4 pr-4 py-3 flex items-center bg-tg-bg border-b-[0.5px] border-tg-separator">
            <span class="text-[20px] w-8 text-center mr-2">⭐</span>
            <span class="text-ios-body text-tg-text flex-1">Всего XP</span>
            <span class="text-[17px] font-semibold text-tg-text">{{ stats?.total_xp || 0 }}</span>
         </div>
         <div class="pl-4 pr-4 py-3 flex items-center bg-tg-bg">
            <span class="text-[20px] w-8 text-center mr-2">✅</span>
            <span class="text-ios-body text-tg-text flex-1">Выполнено</span>
            <span class="text-[17px] font-semibold text-tg-text">{{ stats?.completed_total || 0 }}</span>
         </div>
      </div>
    </div>

    <!-- Badges Horizontal Scroll -->
    <div class="mt-6">
      <h2 class="px-8 mb-2 text-ios-footnote uppercase text-tg-hint font-medium">Награды</h2>
      <div class="overflow-x-auto no-scrollbar px-4 pb-4 flex gap-3">
        <div 
          v-for="badge in stats?.badges" 
          :key="badge.id"
          class="min-w-[100px] h-[120px] bg-tg-bg rounded-[10px] flex flex-col items-center justify-center p-2 text-center border-none shadow-sm"
          :class="{ 'opacity-50 grayscale': !badge.earned }"
        >
          <div class="text-[40px] mb-2">{{ badge.emoji }}</div>
          <div class="text-[11px] font-medium leading-tight text-tg-text">{{ badge.name }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTelegram } from '../composables/useTelegram'
import { useApi, TodayChallenge, ChallengeStats } from '../composables/useApi'

const { userId, hapticFeedback, close } = useTelegram()
const api = useApi()

const activeChallenge = ref<TodayChallenge | null>(null)
const stats = ref<ChallengeStats | null>(null)
const remainingToday = ref(0)
const maxPerDay = ref(2)

onMounted(async () => {
  if (userId.value) {
    const [today, s] = await Promise.all([
      api.getTodaysChallenge(userId.value),
      api.getChallengeStats(userId.value)
    ])
    if (today) { 
      activeChallenge.value = today.challenge
      remainingToday.value = today.remaining_today
      maxPerDay.value = today.max_per_day 
    }
    if (s) stats.value = s
  }
})

async function requestChallenge() {
  if (!userId.value) return
  hapticFeedback('medium')
  const res = await api.requestNewChallenge(userId.value)
  if (res?.success) {
    close()
  }
}

function goToChat() {
  hapticFeedback('light')
  close()
}
</script>
