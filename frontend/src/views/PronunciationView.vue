<template>
  <div class="min-h-screen bg-tg-secondary pb-24">
    <!-- Navigation Bar -->
    <div class="px-4 pt-4 pb-2 bg-tg-secondary sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <h1 class="text-[34px] font-bold text-tg-text tracking-tight leading-tight">Произношение</h1>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="w-6 h-6 border-2 border-tg-hint border-t-tg-button rounded-full animate-spin"></div>
    </div>

    <!-- Practice Mode Switch -->
    <div class="mt-4 px-4">
      <div class="bg-tg-bg rounded-[10px] overflow-hidden">
        <div class="pl-4 pr-3 py-3 flex items-center bg-tg-bg">
          <div class="w-[29px] h-[29px] rounded-[7px] bg-indigo-500 flex items-center justify-center text-white text-[18px] mr-3 flex-shrink-0">
            🎙️
          </div>
          <div class="flex-1 flex justify-between items-center pr-2">
            <div>
              <span class="text-ios-body text-tg-text block">Режим практики</span>
              <span class="text-ios-caption text-tg-hint block">Анализ всех голосовых сообщений</span>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="practiceMode" @change="toggleMode" class="sr-only peer">
              <div class="w-[51px] h-[31px] bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:bg-green-500 transition-colors duration-200"></div>
              <div class="absolute left-[2px] top-[2px] bg-white w-[27px] h-[27px] rounded-full transition-transform duration-200 peer-checked:translate-x-[20px] shadow-sm"></div>
            </label>
          </div>
        </div>
      </div>
      <p class="px-4 mt-2 text-ios-footnote text-tg-hint">Включите, чтобы бот проверял произношение каждого вашего голосового сообщения.</p>
    </div>

    <!-- Charts -->
    <div class="mt-6 px-4">
      <h2 class="px-4 mb-2 text-ios-footnote uppercase text-tg-hint font-medium">Динамика (30 дней)</h2>
      <div class="bg-tg-bg rounded-[10px] p-4 h-[200px] flex items-center justify-center">
        <canvas ref="chartCanvas" class="w-full h-full"></canvas>
      </div>
    </div>

    <!-- Problematic Sounds -->
    <div v-if="stats?.problematic_sounds.length" class="mt-6 px-4">
      <h2 class="px-4 mb-2 text-ios-footnote uppercase text-tg-hint font-medium">Проблемные звуки</h2>
      <div class="bg-tg-bg rounded-[10px] overflow-hidden">
        <div 
          v-for="(sound, idx) in stats.problematic_sounds" 
          :key="sound.sound" 
          class="pl-4 pr-4 py-3 flex items-center bg-tg-bg relative active:bg-tg-secondary"
        >
          <span class="w-[40px] text-[22px] font-bold text-tg-text text-center mr-2">{{ sound.sound }}</span>
          <div class="flex-1 h-3 bg-tg-secondary rounded-full overflow-hidden">
            <div 
              class="h-full bg-orange-500 rounded-full" 
              :style="{ width: (sound.frequency / maxFreq * 100) + '%' }"
            ></div>
          </div>
          <span class="text-ios-caption text-tg-hint w-[40px] text-right">{{ sound.frequency }}</span>

          <div v-if="idx < stats.problematic_sounds.length - 1" class="absolute bottom-0 left-[60px] right-0 h-[0.5px] bg-tg-separator"></div>
        </div>
      </div>
    </div>

    <div class="mt-6 px-4 mb-6">
      <button 
        @click="close" 
        class="w-full bg-tg-button active:opacity-80 text-white font-semibold py-3 rounded-[10px] text-[17px]"
      >
        Написать боту
      </button>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useTelegram } from '@/composables/useTelegram'
import { useApi, PronunciationStatsResponse } from '@/composables/useApi'
import { Chart, LineController, LineElement, PointElement, LinearScale, Title, CategoryScale } from 'chart.js'
Chart.register(LineController, LineElement, PointElement, LinearScale, Title, CategoryScale)

const { userId, close, hapticFeedback } = useTelegram()
const { getPronunciationStats, togglePracticeMode, getSettings } = useApi()

const loading = ref(true)
const stats = ref<PronunciationStatsResponse | null>(null)
const practiceMode = ref(false)
const chartCanvas = ref<HTMLCanvasElement | null>(null)

const maxFreq = computed(() => stats.value ? Math.max(...stats.value.problematic_sounds.map(s => s.frequency)) || 1 : 1)

onMounted(async () => {
  if (userId.value) {
    const [sData, setting] = await Promise.all([
      getPronunciationStats(userId.value, 30),
      getSettings(userId.value)
    ])
    stats.value = sData
    practiceMode.value = setting?.practice_mode_enabled || false
    if (chartCanvas.value && sData) initChart(sData.scores_by_day)
  }
  loading.value = false
})

async function toggleMode() {
  if (!userId.value) return
  hapticFeedback('selection')
  await togglePracticeMode(userId.value)
}

function initChart(data: any[]) {
  if (!chartCanvas.value) return
  new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels: data.map(d => new Date(d.date).getDate()),
      datasets: [{ data: data.map(d => d.avg_score), borderColor: '#3390ec', borderWidth: 2, pointRadius: 0, tension: 0.4 }]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display:false, min:0, max:10 } } }
  })
}
</script>
