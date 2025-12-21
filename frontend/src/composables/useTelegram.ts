/**
 * Composable для работы с Telegram WebApp API.
 * Предоставляет доступ к функциям Telegram Mini App.
 */

import { ref, shallowRef, onMounted, onUnmounted } from 'vue'

// Типы для Telegram WebApp API
interface TelegramUser {
    id: number
    first_name: string
    last_name?: string
    username?: string
    language_code?: string
    is_premium?: boolean
}

interface ThemeParams {
    bg_color?: string
    text_color?: string
    hint_color?: string
    link_color?: string
    button_color?: string
    button_text_color?: string
    secondary_bg_color?: string
}

interface WebApp {
    ready: () => void
    expand: () => void
    close: () => void
    enableClosingConfirmation: () => void
    disableClosingConfirmation: () => void
    initData: string
    initDataUnsafe: {
        user?: TelegramUser
        query_id?: string
        auth_date?: number
        hash?: string
    }
    themeParams: ThemeParams
    colorScheme: 'light' | 'dark'
    viewportHeight: number
    viewportStableHeight: number
    isExpanded: boolean
    BackButton: {
        isVisible: boolean
        show: () => void
        hide: () => void
        onClick: (callback: () => void) => void
        offClick: (callback: () => void) => void
    }
    MainButton: {
        text: string
        color: string
        textColor: string
        isVisible: boolean
        isActive: boolean
        isProgressVisible: boolean
        show: () => void
        hide: () => void
        enable: () => void
        disable: () => void
        showProgress: (leaveActive?: boolean) => void
        hideProgress: () => void
        onClick: (callback: () => void) => void
        offClick: (callback: () => void) => void
        setText: (text: string) => void
        setParams: (params: { text?: string; color?: string; text_color?: string; is_active?: boolean; is_visible?: boolean }) => void
    }
    HapticFeedback: {
        impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void
        notificationOccurred: (type: 'error' | 'success' | 'warning') => void
        selectionChanged: () => void
    }
    showPopup: (params: {
        title?: string
        message: string
        buttons?: Array<{ id?: string; type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive'; text: string }>
    }, callback?: (buttonId: string) => void) => void
    showAlert: (message: string, callback?: () => void) => void
    showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void
    setHeaderColor: (color: string) => void
    setBackgroundColor: (color: string) => void
}

declare global {
    interface Window {
        Telegram?: {
            WebApp: WebApp
        }
    }
}

export function useTelegram() {
    // ВАЖНО: используем shallowRef чтобы избежать конфликта Vue proxy с Telegram WebApp proxy
    const tg = shallowRef<WebApp | null>(null)
    const userId = ref<number | null>(null)
    const username = ref<string | null>(null)
    const firstName = ref<string | null>(null)
    const colorScheme = ref<'light' | 'dark'>('light')
    const isReady = ref(false)

    // Хранение callback для BackButton
    let backButtonCallback: (() => void) | null = null

    onMounted(() => {
        const webApp = window.Telegram?.WebApp

        if (webApp) {
            tg.value = webApp

            // Инициализация
            webApp.ready()
            webApp.expand()
            webApp.enableClosingConfirmation()

            // Получение данных пользователя
            const user = webApp.initDataUnsafe?.user
            if (user) {
                userId.value = user.id
                username.value = user.username || null
                firstName.value = user.first_name
            }

            // Тема
            colorScheme.value = webApp.colorScheme

            // Применение CSS переменных темы
            applyTheme(webApp.themeParams)

            isReady.value = true

            console.log('[Telegram] WebApp initialized', {
                userId: userId.value,
                colorScheme: colorScheme.value
            })
        } else {
            // Режим разработки без Telegram
            console.warn('[Telegram] WebApp not available, using mock data')

            // Mock данные для разработки
            userId.value = 12345
            username.value = 'dev_user'
            firstName.value = 'Developer'
            colorScheme.value = 'light'
            isReady.value = true

            // Дефолтная тема
            applyTheme({
                bg_color: '#ffffff',
                text_color: '#000000',
                hint_color: '#999999',
                link_color: '#2481cc',
                button_color: '#2481cc',
                button_text_color: '#ffffff',
                secondary_bg_color: '#f0f0f0',
            })
        }
    })

    onUnmounted(() => {
        // Очистка при размонтировании
        if (backButtonCallback && tg.value) {
            tg.value.BackButton.offClick(backButtonCallback)
        }
    })

    /**
     * Применение темы Telegram к CSS переменным.
     */
    function applyTheme(params: ThemeParams) {
        const root = document.documentElement

        if (params.bg_color) {
            root.style.setProperty('--tg-bg', params.bg_color)
            root.style.setProperty('--tg-theme-bg-color', params.bg_color)
        }
        if (params.text_color) {
            root.style.setProperty('--tg-text', params.text_color)
            root.style.setProperty('--tg-theme-text-color', params.text_color)
        }
        if (params.hint_color) {
            root.style.setProperty('--tg-hint', params.hint_color)
            root.style.setProperty('--tg-theme-hint-color', params.hint_color)
        }
        if (params.link_color) {
            root.style.setProperty('--tg-link', params.link_color)
            root.style.setProperty('--tg-theme-link-color', params.link_color)
        }
        if (params.button_color) {
            root.style.setProperty('--tg-button', params.button_color)
            root.style.setProperty('--tg-theme-button-color', params.button_color)
        }
        if (params.button_text_color) {
            root.style.setProperty('--tg-button-text', params.button_text_color)
            root.style.setProperty('--tg-theme-button-text-color', params.button_text_color)
        }
        if (params.secondary_bg_color) {
            root.style.setProperty('--tg-secondary-bg', params.secondary_bg_color)
            root.style.setProperty('--tg-theme-secondary-bg-color', params.secondary_bg_color)
        }
    }

    /**
     * Показать кнопку "Назад" с callback.
     */
    function showBackButton(callback: () => void) {
        if (!tg.value) return

        // Удаляем предыдущий callback если был
        if (backButtonCallback) {
            tg.value.BackButton.offClick(backButtonCallback)
        }

        backButtonCallback = callback
        tg.value.BackButton.onClick(callback)
        tg.value.BackButton.show()
    }

    /**
     * Скрыть кнопку "Назад".
     */
    function hideBackButton() {
        if (!tg.value) return

        if (backButtonCallback) {
            tg.value.BackButton.offClick(backButtonCallback)
            backButtonCallback = null
        }
        tg.value.BackButton.hide()
    }

    /**
     * Закрыть Mini App.
     */
    function close() {
        tg.value?.close()
    }

    /**
     * Haptic feedback (вибрация).
     */
    function hapticFeedback(type: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error' | 'selection') {
        if (!tg.value) return

        if (type === 'selection') {
            tg.value.HapticFeedback.selectionChanged()
        } else if (['success', 'warning', 'error'].includes(type)) {
            tg.value.HapticFeedback.notificationOccurred(type as 'success' | 'warning' | 'error')
        } else {
            tg.value.HapticFeedback.impactOccurred(type as 'light' | 'medium' | 'heavy')
        }
    }

    /**
     * Показать главную кнопку.
     */
    function showMainButton(text: string, callback: () => void) {
        if (!tg.value) return

        tg.value.MainButton.setText(text)
        tg.value.MainButton.onClick(callback)
        tg.value.MainButton.show()
    }

    /**
     * Скрыть главную кнопку.
     */
    function hideMainButton() {
        tg.value?.MainButton.hide()
    }

    /**
     * Показать всплывающее сообщение.
     */
    function showAlert(message: string): Promise<void> {
        return new Promise((resolve) => {
            if (tg.value) {
                tg.value.showAlert(message, resolve)
            } else {
                alert(message)
                resolve()
            }
        })
    }

    /**
     * Показать диалог подтверждения.
     */
    function showConfirm(message: string): Promise<boolean> {
        return new Promise((resolve) => {
            if (tg.value) {
                tg.value.showConfirm(message, resolve)
            } else {
                resolve(confirm(message))
            }
        })
    }

    /**
     * Получить initData для аутентификации на бэкенде.
     */
    function getInitData(): string {
        return tg.value?.initData || ''
    }

    return {
        tg,
        userId,
        username,
        firstName,
        colorScheme,
        isReady,
        showBackButton,
        hideBackButton,
        close,
        hapticFeedback,
        showMainButton,
        hideMainButton,
        showAlert,
        showConfirm,
        getInitData,
    }
}
