<script setup>
import { useI18n } from 'vue-i18n'
import { AlertTriangle, HelpCircle } from '@lucide/vue'
const { t } = useI18n()
defineProps(['show', 'title', 'type'])
const emit = defineEmits(['close', 'confirm'])
</script>

<template>
  <Transition name="modal">
    <div v-if="show" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-icon-container" :style="{color: type === 'danger' ? 'var(--danger-color)' : 'var(--accent-color)', marginBottom: '1rem'}">
          <AlertTriangle v-if="type === 'danger'" :size="48" />
          <HelpCircle v-else :size="48" />
        </div>
        <h3 class="modal-title">{{ title }}</h3>
        <div class="modal-footer">
          <button @click="emit('close')" class="btn-secondary">{{ t('cancel') }}</button>
          <button @click="emit('confirm')" class="btn-primary" :class="{'btn-danger': type === 'danger'}">
            {{ t('confirm') }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>