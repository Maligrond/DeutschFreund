<template>
  <div class="min-h-screen bg-tg-secondary pb-24">
    <!-- Navigation Bar -->
    <div class="px-4 pt-4 pb-2 bg-tg-secondary sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <h1 class="text-[34px] font-bold text-tg-text tracking-tight leading-tight">Настройки</h1>
    </div>

    <!-- Group 1: Learning -->
    <div class="mt-4 px-4">
      <h2 class="px-4 mb-2 text-ios-footnote uppercase text-tg-hint font-medium">Обучение</h2>
      <div class="bg-tg-bg rounded-[10px] overflow-hidden">
        
        <!-- Toggle: Reminder -->
        <div class="pl-4 pr-3 py-3 flex items-center bg-tg-bg border-b-[0.5px] border-tg-separator">
          <div class="w-[29px] h-[29px] rounded-[7px] bg-red-500 flex items-center justify-center text-white text-[18px] mr-3 flex-shrink-0">
            🔔
          </div>
          <div class="flex-1 flex justify-between items-center pr-2">
            <span class="text-ios-body text-tg-text">Напоминания</span>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="settings.reminder_enabled" @change="saveSettings" class="sr-only peer">
              <div class="w-[51px] h-[31px] bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:bg-green-500 transition-colors duration-200"></div>
              <div class="absolute left-[2px] top-[2px] bg-white w-[27px] h-[27px] rounded-full transition-transform duration-200 peer-checked:translate-x-[20px] shadow-sm"></div>
            </label>
          </div>
        </div>


        <!-- Action: Retake Test -->
        <div 
          @click="startPlacementTest"
          class="pl-4 pr-3 py-3 flex items-center bg-tg-bg relative active:bg-gray-100 transition-colors cursor-pointer"
        >
          <div class="w-[29px] h-[29px] rounded-[7px] bg-orange-500 flex items-center justify-center text-white text-[18px] mr-3 flex-shrink-0">
            🧩
          </div>
          <div class="flex-1 flex justify-between items-center pr-2">
            <span class="text-ios-body text-tg-text">Пройти тест уровня</span>
             <span class="absolute right-3 top-1/2 -translate-y-1/2 material-icons-round text-tg-hint/50 text-[20px] pointer-events-none">chevron_right</span>
          </div>
        </div>

      </div>
      <p class="px-4 mt-2 text-ios-footnote text-tg-hint">Выберите уровень и включите напоминания для регулярных занятий.</p>
    </div>


    <!-- Group 3: Grammar -->
    <div class="mt-6 px-4">
      <div class="bg-tg-bg rounded-[10px] overflow-hidden">
        <div class="pl-4 pr-3 py-3 flex items-center bg-tg-bg">
          <div class="w-[29px] h-[29px] rounded-[7px] bg-green-500 flex items-center justify-center text-white text-[18px] mr-3 flex-shrink-0">
            📝
          </div>
          <div class="flex-1 flex justify-between items-center pr-2">
            <div>
              <span class="text-ios-body text-tg-text block">Грамматика</span>
              <span class="text-ios-caption text-tg-hint block">Включить упражнения в чате</span>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="grammarSettings.enabled" @change="saveSettings" class="sr-only peer">
              <div class="w-[51px] h-[31px] bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:bg-green-500 transition-colors duration-200"></div>
              <div class="absolute left-[2px] top-[2px] bg-white w-[27px] h-[27px] rounded-full transition-transform duration-200 peer-checked:translate-x-[20px] shadow-sm"></div>
            </label>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTelegram } from '../composables/useTelegram'
import { useApi, SettingsUpdate } from '../composables/useApi'

const router = useRouter()
const { userId, hapticFeedback } = useTelegram()
const { getSettings, updateSettings, getGrammarSettings, updateGrammarSettings } = useApi()

const settings = ref<SettingsUpdate>({ level: 'A2', goal: 'speak_freely', reminder_enabled: true, reminder_frequency: 2, bot_personality: 'friendly' })
const grammarSettings = ref({ enabled: true, frequency: 'medium' })

const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
const personalities = [
  { value: 'friendly', label: 'Дружелюбный' },
  { value: 'strict', label: 'Строгий' },
  { value: 'romantic', label: 'Кокетливый' },
]

onMounted(async () => {
  if (userId.value) {
    const [s, g] = await Promise.all([getSettings(userId.value), getGrammarSettings(userId.value)])
    if (s) settings.value = { ...settings.value, ...s }
    if (g) grammarSettings.value = { ...grammarSettings.value, ...g }
  }
})

async function saveSettings() {
  if (!userId.value) return
  hapticFeedback('selection')
  await Promise.all([updateSettings(userId.value, settings.value), updateGrammarSettings(userId.value, grammarSettings.value)])
}

function startPlacementTest() {
  hapticFeedback('impact_light')
  router.push('/onboarding')
}
</script>
