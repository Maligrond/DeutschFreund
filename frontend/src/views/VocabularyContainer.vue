<template>
  <div class="min-h-screen bg-tg-secondary pb-24">
    <!-- Header with Tabs -->
    <div class="px-4 pt-4 pb-0 bg-tg-secondary sticky top-0 z-10 backdrop-blur-md bg-opacity-90">
      <h1 class="text-[34px] font-bold text-tg-text tracking-tight leading-tight mb-3">Словарь</h1>
      
      <!-- Segmented Control -->
      <div class="bg-tg-bg rounded-[9px] p-[2px] flex mb-2">
        <button 
          @click="activeTab = 'list'"
          class="flex-1 py-[6px] text-[13px] font-medium rounded-[7px] transition-all"
          :class="activeTab === 'list' ? 'bg-tg-secondary text-tg-text shadow-sm' : 'text-tg-hint'"
        >
          Мои слова
        </button>
        <button 
          @click="activeTab = 'cards'"
          class="flex-1 py-[6px] text-[13px] font-medium rounded-[7px] transition-all"
          :class="activeTab === 'cards' ? 'bg-tg-secondary text-tg-text shadow-sm' : 'text-tg-hint'"
        >
          Карточки
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="mt-2">
      <transition name="fade" mode="out-in">
        <component :is="activeTab === 'list' ? VocabularyList : FlashcardsSession" />
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import VocabularyList from '@/components/VocabularyList.vue'
import FlashcardsSession from '@/components/FlashcardsSession.vue'

const route = useRoute()
const activeTab = ref<'list' | 'cards'>('list')

onMounted(() => {
  if (route.query.tab === 'cards') {
    activeTab.value = 'cards'
  }
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
