/**
 * Vue Router конфигурация для Mini App.
 */

import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            redirect: '/stats'
        },
        {
            path: '/stats',
            name: 'stats',
            component: () => import('../views/Stats.vue'),
            meta: { title: 'Статистика' }
        },
        {
            path: '/history',
            name: 'history',
            component: () => import('../views/History.vue'),
            meta: { title: 'История' }
        },
        {
            path: '/settings',
            name: 'settings',
            component: () => import('../views/Settings.vue'),
            meta: { title: 'Настройки' }
        },
        {
            path: '/text/:id',
            name: 'text-viewer',
            component: () => import('../views/TextViewer.vue'),
            meta: { title: 'Изучить текст' }
        },
        {
            path: '/vocabulary',
            name: 'vocabulary',
            component: () => import('../views/VocabularyContainer.vue'),
            meta: { title: 'Словарь' }
        },
        {
            path: '/streak',
            name: 'streak',
            component: () => import('../views/StreakView.vue'),
            meta: { title: 'Streak' }
        },
        // Flashcards is now a tab inside Vocabulary
        {
            path: '/flashcards',
            redirect: '/vocabulary'
        },
        {
            path: '/leaderboard',
            name: 'leaderboard',
            component: () => import('../views/LeaderboardView.vue'),
            meta: { title: 'Топ' }
        },
        {
            path: '/onboarding',
            name: 'onboarding',
            component: () => import('../views/OnboardingTestView.vue'),
            meta: { title: 'Тест уровня' }
        },
        {
            path: '/:pathMatch(.*)*',
            redirect: '/stats'
        }
    ]
})

export default router
