<template>
  <div class="pb-24">


    <div v-if="loading" class="flex justify-center py-20">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-tg-link"></div>
    </div>

    <div v-else-if="cards.length === 0" class="px-4 text-center py-20">
      <div class="text-[60px] mb-4">🎉</div>
      <h2 class="text-xl font-bold text-tg-text mb-2">Всё повторено!</h2>
      <button @click="$router.push('/')" class="mt-8 bg-tg-button text-white px-6 py-3 rounded-xl font-medium">
        На главную
      </button>
    </div>

    <div v-else class="px-4 flex flex-col items-center h-[60vh]">
      <!-- Progress -->
      <div class="w-full flex justify-between text-tg-hint text-sm mb-4 px-2">
        <span>Осталось: {{ cards.length }}</span>
        <span>Прогресс: {{ currentIndex + 1 }}/{{ totalCount }}</span>
      </div>

      <!-- Card -->
      <div 
        class="relative w-full aspect-[3/4] max-h-[400px] perspective-1000 cursor-pointer"
        @click="flipCard"
      >
        <div 
          class="w-full h-full relative transition-all duration-500 transform-style-3d shadow-xl rounded-2xl"
          :class="{ 'rotate-y-180': isFlipped }"
        >
          <!-- Front -->
          <div class="absolute w-full h-full backface-hidden bg-tg-bg-secondary rounded-2xl flex flex-col items-center justify-center border border-tg-hint/10">
            <span class="text-xs font-bold text-tg-hint uppercase tracking-wider mb-4">Немецкий</span>
            <h2 class="text-4xl font-bold text-tg-text text-center px-4">{{ currentCard.word_de }}</h2>
            <span class="text-tg-hint mt-8 text-sm opacity-60">(нажми, чтобы перевернуть)</span>
          </div>

          <!-- Back -->
          <div class="absolute w-full h-full backface-hidden bg-tg-bg-secondary rounded-2xl flex flex-col items-center justify-center border border-tg-hint/10 rotate-y-180">
            <span class="text-xs font-bold text-tg-hint uppercase tracking-wider mb-4">Русский</span>
            <h2 class="text-3xl font-medium text-tg-text text-center px-4 mb-2">{{ currentCard.word_ru }}</h2>
            <div class="w-16 h-0.5 bg-tg-hint/20 my-4"></div>
            <p class="text-tg-text font-bold text-xl">{{ currentCard.word_de }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Controls (Anki style) -->
    <div 
      v-if="isFlipped && cards.length > 0"
      class="fixed bottom-24 left-0 w-full px-4 flex justify-between space-x-2 animate-fade-in-up"
    >
      <button 
        v-for="btn in buttons" 
        :key="btn.value"
        @click="rateCard(btn.value)"
        class="flex-1 py-3 rounded-xl font-medium text-sm transition-transform active:scale-95 flex flex-col items-center justify-center space-y-1"
        :class="btn.class"
      >
        <span>{{ btn.label }}</span>
        <span class="text-[10px] opacity-70 font-normal">{{ btn.time }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useTelegram } from '../composables/useTelegram';
import { useApi, type VocabularyItem } from '../composables/useApi';

const { hapticFeedback, userId } = useTelegram();
const { getDueFlashcards, submitFlashcardReview } = useApi();

const loading = ref(true);
const cards = ref<VocabularyItem[]>([]);
const currentIndex = ref(0);
const isFlipped = ref(false);
const totalCount = ref(0); // Total cards in this session

const currentCard = computed(() => cards.value[currentIndex.value]);

const buttons = [
  { value: 1, label: 'Снова', time: '< 1м', class: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' },
  { value: 2, label: 'Трудно', time: '2д', class: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400' },
  { value: 3, label: 'Хорошо', time: '4д', class: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' },
  { value: 4, label: 'Легко', time: '7д', class: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' }
];

onMounted(async () => {
  await loadCards();
});

const loadCards = async () => {
  if (!userId.value) return;
  
  loading.value = true;
  try {
    const data = await getDueFlashcards(userId.value, 15);
    cards.value = data.words;
    totalCount.value = data.words.length;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const flipCard = () => {
  isFlipped.value = !isFlipped.value;
  hapticFeedback('light'); // Changed from selectionChanged
};

const rateCard = async (quality: number) => {
  if (!currentCard.value) return;
  
  hapticFeedback('medium'); // Changed from impactOccurred
  
  try {
    // Optimistic UI update
    const cardId = currentCard.value.id;
    
    // Remove current card from queue
    cards.value.splice(currentIndex.value, 1);
    isFlipped.value = false;
    
    // Send to API in background
    await submitFlashcardReview(cardId, quality);
    
    // If cards empty, we are done
    if (cards.value.length === 0) {
        hapticFeedback('success'); // Changed from notificationOccurred
    }
  } catch (e) {
    console.error(e);
  }
};
</script>

<style scoped>
.perspective-1000 {
  perspective: 1000px;
}
.transform-style-3d {
  transform-style: preserve-3d;
}
.backface-hidden {
  backface-visibility: hidden;
}
.rotate-y-180 {
  transform: rotateY(180deg);
}
.animate-fade-in-up {
  animation: fadeInUp 0.3s ease-out;
}
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
