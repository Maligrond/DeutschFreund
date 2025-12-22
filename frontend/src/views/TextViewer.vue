<template>
  <div class="min-h-screen bg-tg-secondary pb-24">
    <!-- Header -->
    <div class="px-4 pt-4 pb-2 bg-tg-secondary sticky top-0 z-10 backdrop-blur-md bg-opacity-90 flex justify-between items-center">
      <h1 class="text-[20px] font-semibold text-tg-text text-center flex-1">Перевод</h1>
      <button @click="close" class="text-tg-button font-medium text-[17px]">Готово</button>
    </div>

    <!-- Text Card -->
    <div class="mt-2 px-4">
      <div class="bg-tg-bg rounded-[10px] p-4 min-h-[200px] text-[19px] leading-[1.6] text-tg-text">
        <span
          v-for="(word, index) in words"
          :key="index"
          @click="selectWord(word)"
          class="cursor-pointer rounded-[4px] hover:bg-tg-secondary active:bg-blue-200 dark:active:bg-blue-900 transition-colors"
          :class="selectedWord === word ? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300' : ''"
        >{{ word }}</span>
      </div>
      <p class="mt-2 text-ios-caption text-tg-hint text-center">Нажмите на любое слово для перевода.</p>
    </div>

    <!-- Translation Sheet (Bottom) -->
    <div v-if="selectedWord" class="fixed bottom-0 left-0 right-0 bg-tg-bg border-t border-tg-separator p-4 pb-8 shadow-xl z-50 animate-slide-up rounded-t-[12px]">
      <div class="flex justify-between items-start mb-4">
        <div>
          <h3 class="text-[22px] font-bold text-tg-text mb-1">{{ selectedWord }}</h3>
          <p class="text-[17px] text-tg-hint">{{ wordTranslation || 'Перевод...' }}</p>
        </div>
        <button @click="clearSelection" class="w-8 h-8 rounded-full bg-tg-secondary flex items-center justify-center text-tg-hint">
          <span class="material-icons-round text-[20px]">close</span>
        </button>
      </div>

      <div class="flex gap-3">
         <button @click="speak(selectedWord)" class="flex-1 bg-tg-secondary active:bg-gray-300 text-tg-text font-medium py-3 rounded-[10px] text-[17px] flex items-center justify-center gap-2">
            <span class="material-icons-round">volume_up</span> Слушать
         </button>
         <button @click="addToFavorites" class="flex-1 bg-tg-button active:opacity-80 text-white font-medium py-3 rounded-[10px] text-[17px] flex items-center justify-center gap-2">
            <span class="material-icons-round">star</span> В словарь
         </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useTelegram } from '@/composables/useTelegram'

const route = useRoute()
const api = useApi()
const { userId, close, hapticFeedback } = useTelegram()

const words = ref<string[]>([])
const selectedWord = ref('')
const wordTranslation = ref('')
const messageId = ref(0)
const messageText = ref('')

onMounted(async () => {
  const id = Number(route.params.id)
  if (id) {
    messageId.value = id
    const data = await api.getMessage(id)
    if (data) {
      messageText.value = data.content
      words.value = data.content.split(/(\s+)/)
    }
  }
})

function selectWord(word: string) {
  if (!word.trim() || /^\s+$/.test(word)) return
  hapticFeedback?.('selection')
  selectedWord.value = word.replace(/[.,!?;:()]/g, '')
  wordTranslation.value = '...'
  api.translateWord(messageId.value, selectedWord.value).then(res => wordTranslation.value = res?.translation || '')
}

function clearSelection() { selectedWord.value = '' }

function speak(text: string) {
  const u = new SpeechSynthesisUtterance(text); u.lang='de-DE'; window.speechSynthesis.speak(u)
}

async function addToFavorites() {
  if (!selectedWord.value || !userId.value) return
  
  try {
    hapticFeedback?.('medium')
    await api.addToFavorites(userId.value, selectedWord.value, wordTranslation.value, messageText.value)
    hapticFeedback?.('success')
    // Show a small toast or just close the sheet? For now just close.
    clearSelection()
  } catch (e) {
    console.error('Failed to add to favorites', e)
    hapticFeedback?.('error')
  }
}
</script>

<style scoped>
.animate-slide-up { animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
</style>
