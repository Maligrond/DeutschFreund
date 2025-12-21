<template>
  <div class="min-h-screen bg-tg-secondary pb-24">
    <!-- Header -->
    <div class="px-4 pt-4 pb-2 bg-tg-secondary sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <h1 class="text-[34px] font-bold text-tg-text tracking-tight leading-tight">Streak</h1>
    </div>

    <!-- Hero Card -->
    <div class="mt-4 px-4">
      <div class="bg-gradient-to-br from-orange-400 to-orange-600 rounded-[20px] p-6 text-white text-center shadow-lg relative overflow-hidden">
        <!-- Background Pattern -->
        <div class="absolute top-0 left-0 w-full h-full opacity-10" style="background-image: radial-gradient(white 20%, transparent 20%); background-size: 20px 20px;"></div>
        
        <div class="relative z-10">
          <div class="text-[64px] mb-0 leading-[1]">🔥</div>
          <div class="text-[48px] font-bold leading-tight">{{ streakInfo?.streak_days || 0 }}</div>
          <div class="text-[17px] font-medium opacity-90">дней подряд</div>
        </div>
      </div>
    </div>

    <!-- Daily Goal -->
    <div class="mt-6 px-4">
      <h2 class="px-4 mb-2 text-ios-footnote uppercase text-tg-hint font-medium">Сегодня</h2>
      <div class="bg-tg-bg rounded-[10px] p-4">
        <div class="flex justify-between items-center mb-3">
          <span class="text-ios-body text-tg-text font-medium">Ежедневная цель</span>
          <span class="text-tg-button font-bold">{{ streakInfo?.daily_progress || 0 }}/{{ streakInfo?.daily_goal || 10 }}</span>
        </div>
        <div class="h-3 bg-tg-secondary rounded-full overflow-hidden mb-2">
          <div 
            class="h-full rounded-full transition-all duration-500"
            :class="(streakInfo?.daily_goal_reached) ? 'bg-green-500' : 'bg-orange-500'"
            :style="{ width: Math.min(100, ((streakInfo?.daily_progress || 0)/(streakInfo?.daily_goal || 1) * 100)) + '%' }"
          ></div>
        </div>
        <p v-if="streakInfo?.daily_goal_reached" class="text-green-500 text-ios-caption font-medium">
          ✨ Цель достигнута! Streak продлен.
        </p>
        <p v-else class="text-tg-hint text-ios-caption">
          Отправьте еще {{ (streakInfo?.daily_goal || 10) - (streakInfo?.daily_progress || 0) }} сообщений.
        </p>
      </div>
    </div>

    <!-- Settings Group -->
    <div class="mt-6 px-4">
      <div class="bg-tg-bg rounded-[10px] overflow-hidden">
        <!-- Freeze -->
        <div class="pl-4 pr-3 py-3 flex items-center bg-tg-bg">
          <div class="w-[29px] h-[29px] rounded-[7px] bg-cyan-500 flex items-center justify-center text-white text-[18px] mr-3 flex-shrink-0">
            ❄️
          </div>
          <div class="flex-1 flex justify-between items-center pr-2">
            <div>
              <span class="text-ios-body text-tg-text block">Заморозка</span>
              <span class="text-ios-caption text-tg-hint block">Доступно: {{ streakInfo?.freeze_available || 0 }}</span>
            </div>
            <button 
              @click="handleUseFreeze"
              :disabled="!streakInfo?.freeze_available || streakInfo?.freeze_used_today"
              class="bg-tg-secondary text-tg-button px-4 py-1.5 rounded-full text-[15px] font-semibold disabled:opacity-50"
            >
              {{ streakInfo?.freeze_used_today ? 'Активно' : 'Использовать' }}
            </button>
          </div>
        </div>
      </div>
      <p class="px-4 mt-2 text-ios-footnote text-tg-hint">Заморозка позволяет не потерять streak, если вы пропустите день.</p>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useApi, StreakInfoResponse } from '../composables/useApi'
import { useTelegram } from '../composables/useTelegram'

const { userId, hapticFeedback } = useTelegram()
const { getStreakInfo, useStreakFreeze } = useApi()
const streakInfo = ref<StreakInfoResponse | null>(null)

onMounted(async () => {
  if (userId.value) {
    const data = await getStreakInfo(userId.value)
    if (data) streakInfo.value = data
  }
})

async function handleUseFreeze() {
  if (!userId.value) return
  hapticFeedback('medium')
  const res = await useStreakFreeze(userId.value)
  if (res?.success && streakInfo.value) {
    streakInfo.value.freeze_available = res.remaining
    streakInfo.value.freeze_used_today = true
  }
}
</script>
