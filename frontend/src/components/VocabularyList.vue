<template>
  <div class="pb-4">


    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="w-6 h-6 border-2 border-tg-hint border-t-tg-button rounded-full animate-spin"></div>
    </div>

    <!-- Empty State -->
    <div v-else-if="words.length === 0" class="flex flex-col items-center justify-center p-8 text-center mt-10">
      <div class="text-[60px] mb-4 opacity-50">📖</div>
      <h3 class="text-[20px] font-semibold text-tg-text mb-2">Словарь пуст</h3>
      <p class="text-tg-hint text-ios-body max-w-xs">Добавляйте слова, нажимая на них в сообщениях бота.</p>
    </div>

    <template v-else>
      <!-- Stats Row -->
      <div class="px-4 mb-4">
        <div class="bg-tg-bg rounded-[10px] p-4 flex justify-between items-center shadow-sm">
          <div class="text-center flex-1 border-r border-tg-separator">
            <div class="text-[20px] font-bold text-tg-text">{{ words.length }}</div>
            <div class="text-[11px] uppercase text-tg-hint font-medium">Всего слов</div>
          </div>
          <div class="text-center flex-1">
            <div class="text-[20px] font-bold text-green-500">{{ learnedCount }}</div>
            <div class="text-[11px] uppercase text-tg-hint font-medium">Выучено</div>
          </div>
        </div>
      </div>

      <!-- Words List -->
      <div class="px-4">
        <div class="bg-tg-bg rounded-[10px] overflow-hidden">
          <div 
            v-for="(word, idx) in words" 
            :key="word.id"
            class="pl-4 pr-2 py-3 flex items-center bg-tg-bg active:bg-tg-secondary transition-colors cursor-pointer relative"
            @click="speak(word.word_de)"
          >
            <!-- Speaker Icon -->
            <div class="w-[32px] h-[32px] rounded-full bg-tg-secondary flex items-center justify-center text-tg-button mr-3 flex-shrink-0">
              <span class="material-icons-round text-[18px]">volume_up</span>
            </div>

            <!-- Content -->
            <div class="flex-1 py-1 min-w-0 pr-2">
               <p class="text-[17px] font-medium text-tg-text truncate">{{ word.word_de }}</p>
               <p class="text-[15px] text-tg-hint truncate">{{ word.word_ru }}</p>
            </div>

            <!-- Checkbox -->
            <button 
              @click.stop="toggleLearned(word)"
              class="w-[44px] h-[44px] flex items-center justify-center"
            >
              <div 
                class="w-[22px] h-[22px] rounded-full border-[1.5px] flex items-center justify-center transition-all"
                :class="word.learned ? 'bg-green-500 border-green-500' : 'border-tg-hint/30'"
              >
                <span v-if="word.learned" class="material-icons-round text-white text-[14px] font-bold">check</span>
              </div>
            </button>

            <!-- Separator -->
            <div v-if="idx < words.length - 1" class="absolute bottom-0 left-[60px] right-0 h-[0.5px] bg-tg-separator"></div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTelegram } from '@/composables/useTelegram'
import { useApi, VocabularyItem } from '@/composables/useApi'

const { userId, hapticFeedback } = useTelegram()
const api = useApi()
const words = ref<VocabularyItem[]>([])
const loading = ref(true)
const learnedCount = computed(() => words.value.filter(w => w.learned).length)

onMounted(async () => {
  if (userId.value) {
    const data = await api.getFavorites(userId.value)
    if (data) words.value = data.words
  }
  loading.value = false
})

async function toggleLearned(word: VocabularyItem) {
  hapticFeedback?.('selection')
  await api.toggleLearned(word.id)
  word.learned = !word.learned
}

function speak(text: string) {
  hapticFeedback?.('light')
  const u = new SpeechSynthesisUtterance(text)
  u.lang = 'de-DE'; u.rate = 0.8; window.speechSynthesis.speak(u)
}
</script>
