<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Eye, EyeOff, ShieldCheck } from '@lucide/vue'
const { t } = useI18n()
const props = defineProps(['show', 'attempts'])
const emit = defineEmits(['close', 'submit'])

const pin = ref('')
const showPin = ref(false)

// فلترة المدخلات لتكون أرقاماً فقط وتقييدها بـ 16 رقماً كحد أقصى
const onInput = () => {
  pin.value = pin.value.replace(/\D/g, '').substring(0, 16)
}

// تحجيم الخط ديناميكياً لضمان تناسق العرض مع الأرقام الطويلة
const inputStyle = computed(() => ({
  fontSize: pin.value.length > 12 ? '0.7rem' : '0.9rem'
}))

const isValid = computed(() => {
  return pin.value.length >= 8 && pin.value.length <= 16 && props.attempts < 8
})

const handleSubmit = () => {
  if (isValid.value) {
    emit('submit', pin.value)
  }
}

// تصفير المدخلات عند إغلاق النافذة
watch(() => props.show, (val) => {
  if (!val) {
    pin.value = ''
    showPin.value = false
  }
})
</script>

<template>
  <Transition name="modal">
    <div v-if="show" class="modal-overlay">
      <div class="modal-content">
        <h3 class="modal-title">
          <ShieldCheck :size="20" class="text-primary" />
          {{ t('login_token') }}
        </h3>
        <div style="position: relative">
          <input v-model="pin" :type="showPin ? 'text' : 'password'" 
                 @input="onInput"
                 @keyup.enter="handleSubmit"
                 class="input-field" :style="[inputStyle, { letterSpacing: '0.4em' }]"
                 placeholder="••••••••" autofocus>
          <button @click="showPin = !showPin" class="btn-icon" style="position: absolute; inset-inline-start: 10px; top: 8px; opacity: 0.5">
            <Eye v-if="!showPin" :size="18" />
            <EyeOff v-else :size="18" />
          </button>
        </div>

        <!-- رسائل عدد المحاولات المتبقية -->
        <div v-if="attempts > 0" class="modal-warning-text">
          <template v-if="attempts < 8">
            {{ t('attempts_left', { count: 8 - attempts }) }}
          </template>
          <template v-else>
            {{ t('attempts_exhausted') }}
          </template>
        </div>

        <div class="modal-footer">
          <button @click="emit('close')" class="btn-secondary">{{ t('cancel') }}</button>
          <button @click="handleSubmit" :disabled="!isValid" class="btn-primary">
            {{ t('confirm') }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>