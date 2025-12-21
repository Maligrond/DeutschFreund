<template>
  <div class="min-h-screen bg-tg-secondary pb-24">
    <!-- Header -->
    <div class="px-4 pt-4 pb-2 bg-tg-secondary sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <h1 class="text-[34px] font-bold text-tg-text tracking-tight leading-tight">История</h1>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && messages.length === 0" class="flex flex-col items-center justify-center py-20 px-6 text-center">
      <div class="w-16 h-16 bg-tg-hint/10 rounded-full flex items-center justify-center mb-4">
        <span class="text-[30px]">💭</span>
      </div>
      <h3 class="text-[20px] font-semibold text-tg-text mb-2">История пуста</h3>
      <p class="text-tg-hint text-ios-body">Начните общение с ботом, чтобы увидеть диалог здесь.</p>
    </div>

    <!-- Messages List -->
    <div v-else class="px-4 py-2 space-y-3">
      <div 
        v-for="(msg, idx) in messages" 
        :key="idx"
        class="flex w-full"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div 
          class="max-w-[85%] px-4 py-2 rounded-[18px] text-[17px] leading-[22px] relative shadow-sm"
          :class="msg.role === 'user' 
            ? 'bg-tg-button text-white rounded-br-[4px]' 
            : 'bg-white dark:bg-[#1c1c1d] text-tg-text rounded-bl-[4px]'"
        >
          <div class="whitespace-pre-wrap break-words">{{ msg.content }}</div>
          <div 
            class="text-[11px] text-right mt-1 opacity-70 select-none"
            :class="msg.role === 'user' ? 'text-white' : 'text-tg-hint'"
          >
            {{ formatTime(msg.created_at) }}
          </div>
        </div>
      </div>
      
      <button 
        v-if="hasMore" 
        @click="loadMore"
        :disabled="loading"
        class="w-full py-4 text-tg-button text-[15px] font-medium"
      >
        {{ loading ? 'Загрузка...' : 'Показать предыдущие сообщения' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTelegram } from '../composables/useTelegram'
import { useApi, MessageItem } from '../composables/useApi'

const { userId, close } = useTelegram()
const { getHistory, loading } = useApi()
const messages = ref<MessageItem[]>([])
const offset = ref(0)
const hasMore = ref(false)

async function load(append = false) {
  if (!userId.value) return
  const data = await getHistory(userId.value, 30, offset.value)
  if (data) {
    messages.value = append ? [...messages.value, ...data.messages] : data.messages
    hasMore.value = offset.value + 30 < data.total
  }
}

function loadMore() { offset.value += 30; load(true) }
function formatTime(d: string) { 
  const date = new Date(d)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => load())
</script>
