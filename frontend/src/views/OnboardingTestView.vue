<template>
    <div class="page-container flex flex-col items-center justify-center p-4">
        <!-- LOADING STATE -->
        <div v-if="loading" class="flex flex-col items-center">
            <div class="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <p>Загрузка теста...</p>
        </div>

        <!-- INTRO SCREEN -->
        <div v-else-if="step === 'intro'" class="w-full max-w-md animate-fade-in text-center">
            <h1 class="text-3xl font-bold mb-6">Привет! Я Макс 🇩🇪</h1>
            <p class="text-lg mb-6">Давай определим твой уровень немецкого!</p>
            
            <div class="bg-secondary/10 p-6 rounded-xl mb-8 text-left space-y-3">
                <div class="flex items-center gap-3">
                    <span class="text-2xl">📝</span>
                    <span>Тест до 50 вопросов</span>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-2xl">⏱️</span>
                    <span>10-15 минут</span>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-2xl">🎯</span>
                    <span>A1 → A2 → B1 → B2 → C1</span>
                </div>
            </div>
            
            <p class="text-sm text-gray-500 mb-8">Тест адаптируется под твои ответы и остановится, когда мы найдём твой точный уровень.</p>
            
            <button 
                @click="startTest" 
                class="w-full py-4 bg-blue-600 text-white rounded-xl font-bold text-lg hover:bg-blue-700 transition"
            >
                Начать тест 🚀
            </button>
        </div>

        <!-- QUESTION SCREEN -->
        <div v-else-if="step === 'question'" class="w-full max-w-md animate-fade-in flex flex-col h-full">
            <!-- Progress Header -->
            <div class="mb-6">
                <div class="flex justify-between text-sm text-gray-400 mb-2">
                    <span>Блок {{ currentLevel }}</span>
                    <span>Вопрос {{ currentBlockIndex + 1 }}/10</span>
                </div>
                <div class="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                        class="h-full bg-blue-500 transition-all duration-300" 
                        :style="{ width: `${(currentBlockIndex / 10) * 100}%` }"
                    ></div>
                </div>
            </div>

            <!-- Question Card -->
            <div class="flex-grow flex flex-col justify-center">
                <h2 class="text-xl font-bold mb-8 text-center">{{ currentQuestion?.question }}</h2>
                
                <div class="space-y-3">
                    <button 
                        v-for="(option, idx) in currentQuestion?.options" 
                        :key="idx"
                        @click="selectOption(idx)"
                        :class="[
                            'w-full p-4 rounded-xl text-left transition border-2',
                            selectedOption === idx 
                                ? 'border-blue-500 bg-blue-500/10' 
                                : 'border-gray-700 hover:border-gray-500 bg-secondary'
                        ]"
                    >
                        <span class="font-bold mr-2">{{ ['A', 'B', 'C', 'D'][idx] }})</span>
                        {{ option }}
                    </button>
                </div>
            </div>

            <!-- Next Button (only visible after selection) -->
            <div class="mt-8">
                <button 
                    v-if="selectedOption !== null"
                    @click="submitAnswer"
                    class="w-full py-4 bg-blue-600 text-white rounded-xl font-bold text-lg hover:bg-blue-700 transition"
                >
                    Ответить
                </button>
            </div>
        </div>

        <!-- RESULT SCREEN -->
        <div v-else-if="step === 'result'" class="w-full max-w-md animate-fade-in text-center">
            <h1 class="text-3xl font-bold mb-2">🎉 Тест завершен!</h1>
            <p class="text-gray-400 mb-8">Пройдено вопросов: {{ totalQuestionsAnswered }}/{{ questions.length }}</p>

            <div class="bg-secondary p-8 rounded-2xl mb-8 border border-blue-500/30">
                <div class="text-sm text-gray-400 mb-1">Твой уровень</div>
                <div class="text-5xl font-bold text-blue-400 mb-2">{{ finalLevel }}</div>
                <div class="text-lg text-gray-300">{{ getLevelDescription(finalLevel) }}</div>
            </div>

            <div class="text-left space-y-4 mb-8">
                <h3 class="font-bold text-lg mb-2">📊 Детализация:</h3>
                <div v-for="(result, lvl) in levelResults" :key="lvl" class="flex justify-between items-center bg-secondary/50 p-3 rounded-lg">
                    <div class="flex items-center gap-2">
                        <span v-if="result.passed" class="text-green-500">✅</span>
                        <span v-else class="text-yellow-500">⚠️</span>
                        <span class="font-bold">{{ lvl }}</span>
                    </div>
                    <span>{{ result.score }}/10 ({{ result.percent }}%)</span>
                </div>
            </div>

            <button 
                @click="finishOnboarding" 
                class="w-full py-4 bg-green-600 text-white rounded-xl font-bold text-lg hover:bg-green-700 transition"
            >
                Начать общение 🚀
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useApi, type PlacementQuestion } from '../composables/useApi'
import { useTelegram } from '../composables/useTelegram'

const router = useRouter()
const api = useApi()
const { userId } = useTelegram()

// State
const step = ref<'intro' | 'question' | 'result'>('intro')
const loading = ref(false)
const questions = ref<PlacementQuestion[]>([])
const selectedOption = ref<number | null>(null)

// Adaptive Logic State
const levels = ['A1', 'A2', 'B1', 'B2', 'C1']
const currentLevelIndex = ref(0)
const currentBlockIndex = ref(0) // 0 to 9
const currentLevelScore = ref(0)
const totalQuestionsAnswered = ref(0)
const levelResults = ref<Record<string, { score: number, percent: number, passed: boolean }>>({})
const finalLevel = ref('A1')

// Computed
const currentLevel = computed(() => levels[currentLevelIndex.value])

const currentBlockQuestions = computed(() => {
    return questions.value.filter(q => q.level === currentLevel.value)
})

const currentQuestion = computed(() => {
    return currentBlockQuestions.value[currentBlockIndex.value]
})

// Methods
onMounted(async () => {
    loading.value = true
    const response = await api.getPlacementQuestions()
    if (response) {
        questions.value = response.questions
    }
    loading.value = false
})

const startTest = () => {
    step.value = 'question'
}

const selectOption = (idx: number) => {
    selectedOption.value = idx
}

const submitAnswer = async () => {
    if (selectedOption.value === null || !currentQuestion.value) return

    // Check answer
    const isCorrect = selectedOption.value === currentQuestion.value.correct_index
    if (isCorrect) {
        currentLevelScore.value++
    }
    
    selectedOption.value = null
    currentBlockIndex.value++
    totalQuestionsAnswered.value++

    // Check if block finished
    if (currentBlockIndex.value >= 10 || currentBlockIndex.value >= currentBlockQuestions.value.length) {
        evaluateBlock()
    }
}

const evaluateBlock = () => {
    const score = currentLevelScore.value
    const levelName = currentLevel.value
    
    // Save details
    levelResults.value[levelName] = {
        score: score,
        percent: score * 10,
        passed: score >= 6 // Preliminary pass status for display
    }

    // Logic:
    // 8-10 correct -> Go to next level
    // 6-7 correct -> Stop, confirm current level
    // 0-5 correct -> Stop, user is previous level (or A1 if A1 failed)
    
    if (score >= 8) {
        // Excellent, promote to next level if exists
        if (currentLevelIndex.value < levels.length - 1) {
            currentLevelIndex.value++
            currentBlockIndex.value = 0
            currentLevelScore.value = 0
            // Continue test
        } else {
            // Finished C1 with high score -> C1
            finishTest(levelName)
        }
    } else if (score >= 6) {
        // Good enough, but reached limit -> This is their level
        finishTest(levelName)
    } else {
        // Failed this level -> User is previous level
        const prevLevel = currentLevelIndex.value > 0 ? levels[currentLevelIndex.value - 1] : 'A1' // Fallback to A1 even if failed A1 (A0 not supported yet)
        finishTest(prevLevel)
    }
}

const finishTest = async (resultLevel: string) => {
    finalLevel.value = resultLevel
    step.value = 'result'
    
    // Prepare details for backend
    const details: Record<string, string> = {}
    for (const [lvl, res] of Object.entries(levelResults.value)) {
        details[lvl] = `${res.score}/10`
    }
    
    // Total correct across all blocks (approximate, since we reset score)
    // Needs global correct counter if we want total.
    // Let's just sum scores from levelResults
    let totalCorrect = 0
    for (const res of Object.values(levelResults.value)) {
        totalCorrect += res.score
    }

    if (userId.value) {
        await api.completePlacementTest({
            user_id: userId.value,
            level_result: resultLevel,
            questions_total: totalQuestionsAnswered.value,
            correct_total: totalCorrect,
            details: details
        })
    }
}

const finishOnboarding = () => {
    router.push('/')
}

const getLevelDescription = (level: string) => {
    const map: Record<string, string> = {
        'A1': 'Beginner (Начинающий)',
        'A2': 'Elementary (Базовый)',
        'B1': 'Intermediate (Средний)',
        'B2': 'Upper Intermediate (Выше среднего)',
        'C1': 'Advanced (Продвинутый)'
    }
    return map[level] || level
}
</script>

<style scoped>
.animate-fade-in {
    animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
