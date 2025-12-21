<template>
  <div class="min-h-screen bg-tg-secondary pb-24">
    <!-- Header -->
    <div class="px-4 pt-4 pb-2 bg-tg-secondary sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <h1 class="text-[34px] font-bold text-tg-text tracking-tight leading-tight">Лидерборд</h1>
    </div>

    <!-- Segmented Control -->
    <div class="px-4 mt-2 mb-4">
      <div class="bg-[#767680]/15 dark:bg-[#767680]/25 rounded-[9px] p-0.5 flex">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          @click="switchTab(tab.id)"
          class="flex-1 py-[6px] text-[13px] font-semibold text-center rounded-[7px] transition-all"
          :class="activeTab === tab.id ? 'bg-tg-bg text-tg-text shadow-sm' : 'text-tg-text'"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="w-6 h-6 border-2 border-tg-hint border-t-tg-button rounded-full animate-spin"></div>
    </div>

    <template v-else-if="leaderboard">
      <!-- User Ranking -->
      <div v-if="leaderboard.user_entry" class="px-4 mb-6">
        <div class="bg-tg-button rounded-[10px] p-4 flex items-center shadow-sm">
          <div class="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center font-bold text-white text-[17px] mr-3">
            {{ leaderboard.user_rank }}
          </div>
          <div class="flex-1">
            <p class="text-white font-semibold text-[17px]">{{ leaderboard.user_entry.display_name }}</p>
            <p class="text-white/80 text-[13px]">{{ leaderboard.user_entry.level }} • 🔥 {{ leaderboard.user_entry.streak }}</p>
          </div>
          <span class="text-white font-bold text-[17px]">{{ leaderboard.user_entry.xp }} XP</span>
        </div>
      </div>

      <!-- Top 3 -->
      <div v-if="topThree.length > 0" class="px-4 mb-6">
        <h2 class="px-4 mb-2 text-ios-footnote uppercase text-tg-hint font-medium">Топ Лидеры</h2>
        <div class="bg-tg-bg rounded-[10px] overflow-hidden">
          <div 
            v-for="(entry, index) in topThree" 
            :key="entry.user_id"
            class="pl-4 pr-4 py-3 flex items-center bg-tg-bg border-b-[0.5px] border-tg-separator last:border-none"
          >
            <span class="text-[24px] w-8 text-center mr-2">{{ getMedalEmoji(index) }}</span>
            <div 
              class="w-[36px] h-[36px] rounded-full flex items-center justify-center font-bold text-white text-[15px] mr-3 flex-shrink-0"
              :class="index === 0 ? 'bg-yellow-500' : index === 1 ? 'bg-gray-400' : 'bg-orange-600'"
            >
              {{ entry.display_name.charAt(0) }}
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-ios-body font-medium text-tg-text truncate">{{ entry.display_name }}</p>
              <p class="text-ios-caption text-tg-hint">{{ entry.level }}</p>
            </div>
            <span class="text-tg-button font-semibold text-[17px]">{{ entry.xp }}</span>
          </div>
        </div>
      </div>

      <!-- Other Entries -->
      <div v-if="otherEntries.length > 0" class="px-4">
        <h2 class="px-4 mb-2 text-ios-footnote uppercase text-tg-hint font-medium">Участники</h2>
        <div class="bg-tg-bg rounded-[10px] overflow-hidden">
          <div 
            v-for="(entry, idx) in otherEntries" 
            :key="entry.user_id"
            class="pl-4 pr-4 py-3 flex items-center bg-tg-bg border-b-[0.5px] border-tg-separator last:border-none"
            :class="{ 'bg-blue-50/50 dark:bg-blue-900/10': entry.is_current_user }"
          >
            <div class="w-8 text-center text-tg-hint font-medium text-[15px] mr-3">{{ entry.rank }}</div>
            <div class="flex-1 min-w-0">
              <p class="text-ios-body text-tg-text truncate">
                {{ entry.display_name }}
                <span v-if="entry.is_current_user" class="text-tg-button text-xs ml-1">(Вы)</span>
              </p>
              <p class="text-ios-caption text-tg-hint">{{ entry.level }} • 🔥 {{ entry.streak }}</p>
            </div>
            <span class="font-semibold text-tg-text text-[15px]">{{ entry.xp }}</span>
          </div>
        </div>
      </div>

      <p class="text-center text-tg-hint text-ios-caption py-6">
        Всего участников: {{ leaderboard.total_participants }}
      </p>

    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useApi, type LeaderboardResponse } from '../composables/useApi'
import { useTelegram } from '../composables/useTelegram'

const router = useRouter()
const { getLeaderboard, loading } = useApi()
const { userId, hapticFeedback } = useTelegram()

type Category = 'weekly' | 'monthly' | 'streak'
const activeTab = ref<Category>('weekly')
const leaderboard = ref<LeaderboardResponse | null>(null)

const tabs = [ { id: 'weekly', label: 'Неделя' }, { id: 'monthly', label: 'Месяц' }, { id: 'streak', label: 'Streak' } ] as const

onMounted(async () => { await loadData() })

async function loadData() {
  if (!userId.value) return
  leaderboard.value = await getLeaderboard(activeTab.value, userId.value)
}

async function switchTab(tab: Category) {
  hapticFeedback('light')
  activeTab.value = tab
  await loadData()
}

const topThree = computed(() => leaderboard.value?.entries.slice(0, 3) || [])
const otherEntries = computed(() => leaderboard.value?.entries.slice(3) || [])
function getMedalEmoji(i: number) { return ['🥇', '🥈', '🥉'][i] }
</script>
