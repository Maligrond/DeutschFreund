/**
 * Composable для работы с Backend API.
 * Предоставляет методы для запросов к GermanBuddy API.
 */

import { ref } from 'vue'
import axios, { AxiosInstance, AxiosError } from 'axios'

// Типы ответов API
export interface MessagesByDay {
    date: string
    count: number
}

export interface StatsResponse {
    streak_days: number
    total_messages: number
    level: string
    goal: string | null
    new_words_count: number
    learned_words_count: number
    recent_words: VocabularyItem[]
    messages_by_day: MessagesByDay[]
    accuracy: number
    created_at: string
    // Progress fields
    total_xp: number
    next_level?: string | null
    level_xp_start: number
    level_xp_end?: number | null
    progress_percent: number
    xp_needed: number
}

export interface MessageItem {
    role: 'user' | 'assistant'
    content: string
    created_at: string
    tokens_used?: number
}

export interface HistoryResponse {
    messages: MessageItem[]
    total: number
    limit: number
    offset: number
}

export interface VocabularyItem {
    id: number
    word_de: string
    word_ru: string
    times_seen: number
    learned: boolean
    created_at: string
}

export interface VocabularyResponse {
    words: VocabularyItem[]
    total: number
    total_learned: number
}

export interface SettingsUpdate {
    level?: string
    goal?: string
    reminder_enabled?: boolean
    reminder_frequency?: number
    bot_personality?: string
}

export interface SettingsResponse {
    level: string
    goal: string | null
    reminder_enabled: boolean
    reminder_frequency: number
    bot_personality: string
}

export interface UserContext {
    name?: string
    city?: string
    job?: string
    interests?: string[]
    problems?: string[]
    extra?: Record<string, unknown>
}

export interface ContextResponse {
    context: UserContext
    updated_at: string | null
}

export interface UserProfile {
    user_id: number
    username: string | null
    first_name: string
    level: string
    goal: string | null
    streak_days: number
    total_messages: number
    reminder_enabled: boolean
    bot_personality: string
    created_at: string
}

import { useTelegram } from './useTelegram'

export interface ApiError {
    detail: string
    error_code?: string
}

export interface UpdateResponse {
    status: string
    message: string
}

export function useApi() {
    const API_URL = import.meta.env.VITE_API_URL || ''

    const loading = ref(false)
    const error = ref<string | null>(null)

    // Создание axios instance
    const api: AxiosInstance = axios.create({
        baseURL: API_URL,
        timeout: 10000,
        headers: {
            'Content-Type': 'application/json',
        },
    })

    // Interceptor для добавления initData
    api.interceptors.request.use((config) => {
        // Получаем initData из Telegram
        const tg = window.Telegram?.WebApp
        if (tg?.initData) {
            config.headers['X-Telegram-Init-Data'] = tg.initData
        }
        return config
    })

    // Interceptor для обработки ошибок
    api.interceptors.response.use(
        (response) => response,
        (err: AxiosError<ApiError>) => {
            const message = err.response?.data?.detail || err.message || 'Unknown error'
            console.error('[API Error]', message)
            throw new Error(message)
        }
    )

    /**
     * Обёртка для API запросов с обработкой loading и error.
     */
    async function apiCall<T>(fn: () => Promise<T>): Promise<T | null> {
        loading.value = true
        error.value = null

        try {
            const result = await fn()
            return result
        } catch (err) {
            error.value = err instanceof Error ? err.message : 'Unknown error'
            return null
        } finally {
            loading.value = false
        }
    }

    // ============ API METHODS ============

    /**
     * Получить статистику пользователя.
     */
    async function getUserStats(userId: number): Promise<StatsResponse | null> {
        return apiCall(async () => {
            const response = await api.get<StatsResponse>(`/api/user/${userId}/stats`)
            return response.data
        })
    }

    /**
     * Получить историю сообщений с пагинацией.
     */
    async function getHistory(
        userId: number,
        limit = 50,
        offset = 0
    ): Promise<HistoryResponse | null> {
        return apiCall(async () => {
            const response = await api.get<HistoryResponse>(`/api/user/${userId}/history`, {
                params: { limit, offset }
            })
            return response.data
        })
    }

    /**
     * Получить словарь пользователя.
     */
    async function getVocabulary(
        userId: number,
        learnedOnly = false
    ): Promise<VocabularyResponse | null> {
        return apiCall(async () => {
            const response = await api.get<VocabularyResponse>(`/api/user/${userId}/vocabulary`, {
                params: { learned_only: learnedOnly }
            })
            return response.data
        })
    }

    /**
     * Получить настройки пользователя.
     */
    async function getSettings(userId: number): Promise<SettingsResponse | null> {
        return apiCall(async () => {
            const response = await api.get<SettingsResponse>(`/api/user/${userId}/settings`)
            return response.data
        })
    }

    /**
     * Обновить настройки пользователя.
     */
    async function updateSettings(
        userId: number,
        settings: SettingsUpdate
    ): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.put(`/api/user/${userId}/settings`, settings)
            return true
        })
        return result === true
    }

    /**
     * Получить контекст пользователя.
     */
    async function getContext(userId: number): Promise<ContextResponse | null> {
        return apiCall(async () => {
            const response = await api.get<ContextResponse>(`/api/user/${userId}/context`)
            return response.data
        })
    }

    /**
     * Обновить контекст пользователя.
     */
    async function updateContext(
        userId: number,
        context: UserContext
    ): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.put(`/api/user/${userId}/context`, context)
            return true
        })
        return result === true
    }

    /**
     * Получить профиль пользователя.
     */
    async function getProfile(userId: number): Promise<UserProfile | null> {
        return apiCall(async () => {
            const response = await api.get<UserProfile>(`/api/user/${userId}/profile`)
            return response.data
        })
    }

    /**
     * Проверка health API.
     */
    async function healthCheck(): Promise<boolean> {
        try {
            await api.get('/health')
            return true
        } catch {
            return false
        }
    }

    // ============ INTERACTIVE TEXT METHODS ============

    /**
     * Получить сообщение по ID.
     */
    async function getMessage(messageId: number): Promise<{ id: number; content: string; created_at: string } | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/message/${messageId}`)
            return response.data
        })
    }

    /**
     * Перевести слово.
     */
    async function translateWord(
        messageId: number,
        word: string
    ): Promise<{ word: string; translation: string } | null> {
        return apiCall(async () => {
            const response = await api.post(`/api/message/${messageId}/translate`, { word })
            return response.data
        })
    }

    /**
     * Перевести всё сообщение.
     */
    async function translateFullMessage(
        messageId: number
    ): Promise<{ original: string; translation: string } | null> {
        return apiCall(async () => {
            const response = await api.post(`/api/message/${messageId}/translate-all`)
            return response.data
        })
    }

    /**
     * Добавить слово в избранное.
     */
    async function addToFavorites(
        userId: number,
        word_de: string,
        word_ru: string,
        context?: string
    ): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.post('/api/vocabulary/favorite', {
                user_id: userId,
                word_de,
                word_ru,
                context
            })
            return true
        })
        return result === true
    }

    /**
     * Получить избранные слова.
     */
    async function getFavorites(
        userId: number,
        limit = 50
    ): Promise<{ words: VocabularyItem[]; total: number } | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/vocabulary/favorites/${userId}`, {
                params: { limit }
            })
            return response.data
        })
    }

    /**
     * Переключить статус "выучено".
     */
    async function toggleLearned(wordId: number): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.post(`/api/vocabulary/${wordId}/toggle-learned`)
            return true
        })
        return result === true
    }

    /**
     * Сбросить прогресс слова (Study Now).
     */
    async function resetWordProgress(wordId: number): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.post(`/api/vocabulary/${wordId}/reset`)
            return true
        })
        return result === true
    }

    /**
     * Получить статистику произношения за период.
     */
    async function getPronunciationStats(
        userId: number,
        days: number = 30
    ): Promise<PronunciationStatsResponse | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/user/${userId}/pronunciation/stats`, {
                params: { days }
            })
            return response.data
        })
    }

    /**
     * Получить историю практик произношения.
     */
    async function getPronunciationHistory(
        userId: number,
        limit: number = 20,
        offset: number = 0
    ): Promise<PronunciationHistoryResponse | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/user/${userId}/pronunciation/history`, {
                params: { limit, offset }
            })
            return response.data
        })
    }

    /**
     * Переключить режим практики произношения.
     */
    async function togglePracticeMode(userId: number): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.post(`/api/user/${userId}/pronunciation/toggle`)
            return true
        })
        return result === true
    }

    // ============ CHALLENGE METHODS ============

    /**
     * Получить настройки челленджей.
     */
    async function getChallengeSettings(userId: number): Promise<ChallengeSettings | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/challenges/settings/${userId}`)
            return response.data
        })
    }

    /**
     * Обновить настройки челленджей.
     */
    async function updateChallengeSettings(
        userId: number,
        settings: Partial<ChallengeSettings>
    ): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.put(`/api/challenges/settings/${userId}`, settings)
            return true
        })
        return result === true
    }

    /**
     * Получить статистику челленджей.
     */
    async function getChallengeStats(userId: number): Promise<ChallengeStats | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/challenges/stats/${userId}`)
            return response.data
        })
    }

    /**
     * Получить сегодняшний челлендж и статус лимитов.
     */
    async function getTodaysChallenge(userId: number): Promise<TodayChallengeData | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/challenges/today/${userId}`)
            return response.data
        })
    }

    /**
     * Запросить новый челлендж (лимит 2 в день).
     */
    async function requestNewChallenge(userId: number): Promise<ChallengeSelectResponse | null> {
        return apiCall(async () => {
            const response = await api.post(`/api/challenges/request/${userId}`)
            return response.data
        })
    }

    /**
     * Получить историю челленджей.
     */
    async function getChallengeHistory(
        userId: number,
        limit = 30
    ): Promise<ChallengeHistoryResponse | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/challenges/history/${userId}`, {
                params: { limit }
            })
            return response.data
        })
    }

    // ============ GRAMMAR EXERCISES METHODS ============

    /**
     * Получить настройки грамматических упражнений.
     */
    async function getGrammarSettings(userId: number): Promise<GrammarSettings | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/user/${userId}/grammar/settings`)
            return response.data
        })
    }

    /**
     * Обновить настройки грамматических упражнений.
     */
    async function updateGrammarSettings(
        userId: number,
        settings: Partial<GrammarSettings>
    ): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.put(`/api/user/${userId}/grammar/settings`, settings)
            return true
        })
        return result === true
    }

    /**
     * Получить статистику грамматических упражнений.
     */
    async function getGrammarStats(userId: number): Promise<GrammarStatsResponse | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/user/${userId}/grammar/stats`)
            return response.data
        })
    }

    /**
     * Получить список тем.
     */
    async function getGrammarTopics(): Promise<GrammarTopicsResponse | null> {
        return apiCall(async () => {
            const response = await api.get('/api/grammar/topics')
            return response.data
        })
    }

    // ============ STREAK METHODS ============

    /**
     * Получить информацию о streak.
     */
    async function getStreakInfo(userId: number): Promise<StreakInfoResponse | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/streak/${userId}`)
            return response.data
        })
    }

    /**
     * Использовать streak freeze.
     */
    async function useStreakFreeze(userId: number): Promise<StreakFreezeResponse | null> {
        return apiCall(async () => {
            const response = await api.post(`/api/streak/${userId}/freeze`)
            return response.data
        })
    }

    /**
     * Обновить настройки streak.
     */
    async function updateStreakSettings(
        userId: number,
        settings: { reminder_enabled?: boolean; anonymous_leaderboard?: boolean }
    ): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.put(`/api/streak/${userId}/settings`, settings)
            return true
        })
        return result === true
    }

    // ============ LEADERBOARD METHODS ============

    /**
     * Получить leaderboard по категории.
     */
    async function getLeaderboard(
        category: 'weekly' | 'monthly' | 'streak',
        userId?: number,
        limit = 50
    ): Promise<LeaderboardResponse | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/leaderboard/${category}`, {
                params: { user_id: userId, limit }
            })
            return response.data
        })
    }

    /**
     * Получить позицию пользователя.
     */
    async function getUserPosition(userId: number): Promise<UserPositionResponse | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/leaderboard/position/${userId}`)
            return response.data
        })
    }

    /**
     * Получить публичный профиль.
     */
    async function getPublicProfile(userId: number): Promise<PublicProfileResponse | null> {
        return apiCall(async () => {
            const response = await api.get(`/api/profile/${userId}/public`)
            return response.data
        })
    }

    // ============ PLACEMENT TEST METHODS ============

    /**
     * Получить вопросы для теста.
     */
    async function getPlacementQuestions(): Promise<PlacementTestQuestionsResponse | null> {
        return apiCall(async () => {
            const response = await api.get('/api/test/questions')
            return response.data
        })
    }

    /**
     * Отправить результаты теста.
     */
    async function completePlacementTest(data: PlacementTestSubmit): Promise<boolean> {
        const result = await apiCall(async () => {
            await api.post('/api/test/complete', data)
            return true
        })
        return result === true
    }

    return {
        // State
        loading,
        error,

        // Methods
        getUserStats,
        getHistory,
        getVocabulary,
        getSettings,
        updateSettings,
        getContext,
        updateContext,
        getProfile,
        healthCheck,

        // Interactive Text Methods
        getMessage,
        translateWord,
        translateFullMessage,
        addToFavorites,
        getFavorites,
        toggleLearned,

        async getDueFlashcards(limit: number = 15): Promise<VocabularyResponse> {
            const { userId } = useTelegram();
            if (!userId.value) throw new Error('User not found');
            const response = await api.get(`/api/vocabulary/review`, { params: { user_id: userId.value, limit } });
            return response.data;
        },

        async submitFlashcardReview(wordId: number, quality: number): Promise<UpdateResponse> {
            const response = await api.post(`/api/vocabulary/review/${wordId}`, null, { params: { quality } });
            return response.data;
        },

        // Raw API instance
        api,

        // Pronunciation Methods
        getPronunciationStats,
        getPronunciationHistory,
        togglePracticeMode,

        // Challenge Methods
        getChallengeSettings,
        updateChallengeSettings,
        getChallengeStats,
        getTodaysChallenge,
        getChallengeHistory,
        requestNewChallenge,

        // Grammar Exercises Methods
        getGrammarSettings,
        updateGrammarSettings,
        getGrammarStats,
        getGrammarTopics,

        // Streak Methods
        getStreakInfo,
        useStreakFreeze,
        updateStreakSettings,

        // Leaderboard Methods
        getLeaderboard,
        getUserPosition,
        getPublicProfile,

        // Placement Test Methods
        getPlacementQuestions,
        completePlacementTest,
    }
}

// ============ PLACEMENT TEST TYPES ============

export interface PlacementQuestion {
    id: number
    level: string
    question: string
    options: string[]
    correct_index: number
}

export interface PlacementTestQuestionsResponse {
    questions: PlacementQuestion[]
}

export interface PlacementTestSubmit {
    user_id: number
    level_result: string
    questions_total: number
    correct_total: number
    details: Record<string, string>
}

// ============ PRONUNCIATION TYPES ============

export interface PronunciationFeedback {
    score: number
    good: string[]
    improve: string[]
    tip: string
}

export interface PronunciationPractice {
    id: number
    transcription: string
    score: number
    feedback: PronunciationFeedback
    attempt_number: number
    created_at: string
}

export interface ScoreByDay {
    date: string
    avg_score: number
    count: number
}

export interface ProblematicSound {
    sound: string
    frequency: number
}

export interface PronunciationStatsResponse {
    average_score: number
    total_practices: number
    scores_by_day: ScoreByDay[]
    problematic_sounds: ProblematicSound[]
    recent_practices: PronunciationPractice[]
}

export interface PronunciationHistoryResponse {
    practices: PronunciationPractice[]
    total: number
}

// ============ CHALLENGE TYPES ============

export interface ChallengeSettings {
    enabled: boolean
    notification_time: string
    difficulty: string
    topics: string[]
    formats: string[]
}

export interface Badge {
    id: string
    name: string
    emoji: string
    description: string
    earned: boolean
    progress: string | null
}

export interface ChallengeStats {
    total_xp: number
    level: string
    current_streak: number
    best_streak: number
    completed_total: number
    completed_this_month: number
    average_score: number
    badges: Badge[]
    topics_progress: Record<string, number>
}

export interface TodayChallenge {
    id: number
    date: string
    title: string
    description: string
    topic: string
    topic_name: string
    challenge_type: string
    grammar_focus: string | null
    min_requirements: string
    example_start: string | null
    completed: boolean
    score: number | null
    xp_earned: number
    deadline: string
}

export interface ChallengeHistoryItem {
    id: number
    date: string
    title: string
    topic: string
    topic_name: string
    type: string
    completed: boolean
    score: number | null
    xp_earned: number
}

export interface ChallengeHistoryResponse {
    challenges: ChallengeHistoryItem[]
    total: number
}

export interface TodayChallengeData {
    challenge: TodayChallenge | null
    remaining_today: number
    max_per_day: number
    message?: string
}

export interface ChallengeOption {
    id: number
    topic: string
    topic_name: string
    format: string
    format_name: string
    preview: string
}

export interface ChallengeOptionsResponse {
    options: ChallengeOption[]
    remaining_today: number
    max_per_day: number
}

export interface ChallengeSelectResponse {
    success: boolean
    challenge: TodayChallenge
    remaining_today: number
    message: string
}

// ============ GRAMMAR EXERCISES TYPES ============

export interface GrammarSettings {
    enabled: boolean
    frequency: 'rare' | 'medium' | 'often'
}

export interface WeakTopic {
    topic: string
    name: string
    accuracy: number
    total: number
    correct: number
}

export interface TopicStats {
    name: string
    total: number
    correct: number
    accuracy: number
}

export interface GrammarStatsResponse {
    total_exercises: number
    correct_answers: number
    accuracy: number
    weak_topics: WeakTopic[]
    by_topic: Record<string, TopicStats>
}

export interface GrammarTopic {
    id: string
    name: string
    name_de: string
    description: string
    premium: boolean
}

export interface GrammarTopicsResponse {
    topics: GrammarTopic[]
}

// ============ STREAK TYPES ============

export interface DailyActivity {
    date: string
    weekday: string
    messages: number
    completed: boolean
}

export interface StreakBadge {
    id: string
    day: number
    name: string
    emoji: string
    description: string
    earned: boolean
    xp: number
}

export interface NextMilestoneReward {
    name: string
    emoji: string
    xp: number
    premium_days: number
}

export interface StreakInfoResponse {
    streak_days: number
    best_streak: number
    streak_start_date: string | null
    daily_progress: number
    daily_goal: number
    daily_goal_reached: boolean
    next_milestone: number | null
    next_milestone_reward: NextMilestoneReward | null
    xp_today: number
    xp_week: number
    xp_month: number
    total_xp: number
    freeze_available: number
    freeze_used_today: boolean
    weekly_activity: DailyActivity[]
    streak_badges: StreakBadge[]
}

export interface StreakFreezeResponse {
    success: boolean
    message: string
    remaining: number
}

// ============ LEADERBOARD TYPES ============

export interface LeaderboardEntry {
    rank: number
    user_id: number
    username: string | null
    display_name: string
    level: string
    xp: number
    streak: number
    badges_count: number
    is_current_user: boolean
}

export interface LeaderboardResponse {
    entries: LeaderboardEntry[]
    total_participants: number
    user_rank: number | null
    user_entry: LeaderboardEntry | null
    category: string
}

export interface UserPositionResponse {
    weekly_rank: number
    weekly_total: number
    monthly_rank: number
    streak_rank: number
    change_from_last_week: number
}

export interface PublicProfileResponse {
    user_id: number
    display_name: string
    level: string
    streak_days: number
    total_xp: number
    badges: BadgeItem[]
    studying_since: string
    recent_achievements: Record<string, unknown>[]
}

export interface BadgeItem {
    id: string
    name: string
    emoji: string
    description: string
    earned: boolean
    progress: string | null
}
