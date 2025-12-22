<template>
  <div class="min-h-screen bg-tg-secondary pb-24">
    <!-- Navigation Bar (iOS Large Title style) -->
    <div class="px-4 pt-4 pb-2 bg-tg-secondary sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <h1 class="text-[34px] font-bold text-tg-text tracking-tight leading-tight">Главная</h1>
      <p class="text-ios-subhead text-tg-hint -mt-1">{{ stats.level }} • Немецкий</p>
    </div>

    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="w-6 h-6 border-2 border-tg-hint border-t-tg-button rounded-full animate-spin mb-4"></div>
      <p v-if="showLongLoadingMessage" class="text-tg-hint text-sm animate-pulse text-center px-4">
        Ожидание сервера... 😴<br>
        (Первая загрузка может занять 5-10 сек)
      </p>
    </div>

    <template v-else>
      <!-- Section: Streak & Stats -->
      <div class="mt-4 px-4">
        <div class="bg-tg-bg rounded-[10px] overflow-hidden">
          <!-- Item 1: Streak -->
          <div 
            class="pl-4 pr-3 py-3 flex items-center bg-tg-bg active:bg-tg-secondary transition-colors cursor-pointer"
            @click="$router.push('/streak')"
          >
            <div class="w-[29px] h-[29px] rounded-[7px] bg-orange-500 flex items-center justify-center text-white text-[18px] mr-3 flex-shrink-0">
              🔥
            </div>
            <div class="flex-1 py-1 border-b-[0.5px] border-tg-separator relative">
              <div class="flex justify-between items-center pr-2">
                <span class="text-ios-body text-tg-text">Streak</span>
                <div class="flex items-center">
                  <span class="text-ios-body text-tg-hint mr-2">{{ stats.streak_days }} дней</span>
                  <span class="material-icons-round text-tg-hint/50 text-[20px]">chevron_right</span>
                </div>
              </div>
              <!-- Separator hack to align with text -->
              <div class="absolute bottom-[-0.5px] left-0 right-0 h-[0.5px] bg-tg-secondary z-10"></div>
            </div>
          </div>
          
          <!-- Item 2: Messages -->
          <div class="pl-4 pr-3 py-3 flex items-center bg-tg-bg">
            <div class="w-[29px] h-[29px] rounded-[7px] bg-blue-500 flex items-center justify-center text-white text-[18px] mr-3 flex-shrink-0">
              💬
            </div>
            <div class="flex-1 py-1">
              <div class="flex justify-between items-center pr-2">
                <span class="text-ios-body text-tg-text">Сообщения</span>
                <span class="text-ios-body text-tg-hint">{{ stats.total_messages }}</span>
              </div>
            </div>
          </div>
        </div>
        <p class="px-4 mt-2 text-ios-footnote text-tg-hint">Статистика вашей активности в боте</p>
      </div>

      <!-- Section: Level -->
      <div class="mt-6 px-4">
        <h2 class="px-4 mb-2 text-ios-footnote uppercase text-tg-hint font-medium">Текущий уровень</h2>
        <div class="bg-tg-bg rounded-[10px] p-4">
          <div class="flex justify-between items-center mb-3">
            <div>
              <span class="text-[22px] font-bold text-tg-text mr-2">{{ stats.level }}</span>
              <span class="text-tg-hint text-sm" v-if="stats.level_xp_end">{{ stats.total_xp - stats.level_xp_start }} / {{ stats.level_xp_end - stats.level_xp_start }} XP</span>
            </div>
            <span class="text-tg-button font-semibold">{{ progressPercent }}%</span>
          </div>
          <div class="h-2 bg-tg-secondary rounded-full overflow-hidden mb-4">
            <div 
              class="h-full bg-tg-button rounded-full transition-all duration-500" 
              :style="{ width: progressPercent + '%' }"
            ></div>
          </div>
          <button 
            @click="continueLesson" 
            class="w-full bg-tg-button active:opacity-80 text-white font-semibold py-3 rounded-[10px] text-[17px]"
          >
            Продолжить обучение
          </button>
        </div>
      </div>

      <!-- Section: Vocabulary -->
      <div class="mt-6 px-4">
        <div class="bg-tg-bg rounded-[10px] overflow-hidden">
          
          <!-- Item 3: Flashcards -->
          <div 
            class="pl-4 pr-3 py-3 flex items-center bg-tg-bg active:bg-tg-secondary transition-colors cursor-pointer border-b-[0.5px] border-tg-separator"
            @click="$router.push('/vocabulary?tab=cards')"
          >
            <div class="w-[29px] h-[29px] rounded-[7px] bg-purple-500 flex items-center justify-center text-white text-[18px] mr-3 flex-shrink-0">
              🗂️
            </div>
            <div class="flex-1 py-1">
              <div class="flex justify-between items-center pr-2">
                <span class="text-ios-body text-tg-text">Карточки</span>
                <span class="material-icons-round text-tg-hint/50 text-[20px]">chevron_right</span>
              </div>
            </div>
          </div>

          <!-- Item 4: Vocabulary -->
          <div 
            class="pl-4 pr-3 py-3 flex items-center bg-tg-bg active:bg-tg-secondary transition-colors cursor-pointer"
            @click="$router.push('/vocabulary')"
          >
            <div class="w-[29px] h-[29px] rounded-[7px] bg-green-500 flex items-center justify-center text-white text-[18px] mr-3 flex-shrink-0">
              📚
            </div>
            <div class="flex-1 py-1">
              <div class="flex justify-between items-center pr-2">
                <span class="text-ios-body text-tg-text">Мой словарь</span>
                <div class="flex items-center">
                  <span class="text-ios-body text-tg-hint mr-2">{{ stats.learned_words_count }} / {{ stats.new_words_count }}</span>
                  <span class="material-icons-round text-tg-hint/50 text-[20px]">chevron_right</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTelegram } from '@/composables/useTelegram'
import { useApi, StatsResponse } from '@/composables/useApi'

const { userId, hapticFeedback } = useTelegram()
const api = useApi()

const stats = ref<StatsResponse>({
  streak_days: 0,
  total_messages: 0,
  level: 'A1',
  goal: null,
  new_words_count: 0,
  learned_words_count: 0,
  recent_words: [],
  messages_by_day: [],
  accuracy: 0,
  created_at: new Date().toISOString(),
  total_xp: 0,
  next_level: 'A2',
  level_xp_start: 0,
  level_xp_end: 1000,
  progress_percent: 0,
  xp_needed: 1000
})

const loading = ref(true)
const showLongLoadingMessage = ref(false)

const progressPercent = computed(() => {
  // Use the calculated percent from backend
  return stats.value.progress_percent || 0
})

onMounted(async () => {
  // Show "Long Loading" message if it takes > 2 seconds
  const timer = setTimeout(() => {
    if (loading.value) {
      showLongLoadingMessage.value = true
    }
  }, 2000)

  if (userId.value) {
    const data = await api.getUserStats(userId.value)
    if (data) stats.value = data
  }
  
  clearTimeout(timer)
  loading.value = false
})

function continueLesson() {
  hapticFeedback?.('light')
  window.Telegram?.WebApp?.close()
}
</script>
