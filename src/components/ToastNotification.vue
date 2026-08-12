<script setup>
import { CheckCircle2, AlertCircle } from '@lucide/vue'
defineProps(['toasts'])
const emit = defineEmits(['remove'])
</script>

<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <div v-for="toast in toasts" :key="toast.id" 
           class="toast-item" :class="toast.type === 'error' ? 'toast-error' : 'toast-success'">
        <AlertCircle v-if="toast.type === 'error'" :size="16" class="icon-error" />
        <CheckCircle2 v-else :size="16" class="icon-success" />
        <span class="toast-message">{{ toast.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active, .toast-leave-active { 
    transition: all 0.4s ease;
}

.toast-enter-from { 
    opacity: 0; 
    transform: translateY(20px); /* يظهر من الأسفل للأعلى */
}

.toast-leave-to { 
    opacity: 0; 
    transform: scale(0.9) translateY(10px); 
}
</style>