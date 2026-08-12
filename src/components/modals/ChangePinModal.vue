<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { KeyRound, ShieldAlert, Eye, EyeOff } from '@lucide/vue'

const { t } = useI18n()
const props = defineProps(['show', 'attempts']) // يستقبل عدد المحاولات الفاشلة من الأب
const emit = defineEmits(['close', 'submit'])

const form = ref({ old: '', new: '', confirm: '' })
const showPins = ref({ old: false, new: false, confirm: false })

// فلترة المدخلات لتكون أرقاماً فقط
const onInput = (field) => {
  form.value[field] = form.value[field].replace(/\D/g, '').substring(0, 16) // السماح حتى 16 رقماً
}

// حجم الخط يصغر تدريجياً إذا زاد طول الرمز عن 12
const inputStyle = (val) => ({
  fontSize: val.length > 12 ? '0.7rem' : '0.9rem',
  letterSpacing: '0.3em' // تباعد متناسق مع مودال الدخول
})

const isValid = computed(() => {
  return form.value.old.length >= 4 && 
         form.value.new.length >= 8 && // الحد الأدنى 8
         form.value.new.length <= 16 && // الحد الأقصى 16
         form.value.new === form.value.confirm &&
         props.attempts < 8
})

const submit = () => {
  if (isValid.value) {
    emit('submit', { old: form.value.old, new: form.value.new })
  }
}

// تصفير الفورم عند الإغلاق
watch(() => props.show, (val) => {
  if (!val) {
    form.value = { old: '', new: '', confirm: '' }
    showPins.value = { old: false, new: false, confirm: false }
  }
})
</script>

<template>
  <Transition name="modal">
    <div v-if="show" class="modal-overlay">
      <div class="modal-content">
        <h3 class="modal-title">
          <KeyRound :size="16" class="text-gold" />
          {{ t('change_pin') }}
        </h3>

        <div class="input-group">
          <div class="input-wrapper">
            <input v-model="form.old" @input="onInput('old')" :type="showPins.old ? 'text' : 'password'" class="input-field" 
                   :style="inputStyle(form.old)" :placeholder="t('old_pin')">
            <button @click="showPins.old = !showPins.old" class="btn-icon" style="position: absolute; inset-inline-start: 10px; top: 6px; opacity: 0.5">
              <Eye v-if="!showPins.old" :size="16" />
              <EyeOff v-else :size="16" />
            </button>
          </div>
          
          <div class="input-wrapper">
            <input v-model="form.new" @input="onInput('new')" :type="showPins.new ? 'text' : 'password'" class="input-field" 
                   :style="inputStyle(form.new)" :placeholder="t('new_pin')">
            <button @click="showPins.new = !showPins.new" class="btn-icon" style="position: absolute; inset-inline-start: 10px; top: 6px; opacity: 0.5">
              <Eye v-if="!showPins.new" :size="16" />
              <EyeOff v-else :size="16" />
            </button>
          </div>

          <div class="input-wrapper">
            <input v-model="form.confirm" @input="onInput('confirm')" :type="showPins.confirm ? 'text' : 'password'" class="input-field" 
                   :style="inputStyle(form.confirm)" :placeholder="t('confirm_pin')">
            <button @click="showPins.confirm = !showPins.confirm" class="btn-icon" style="position: absolute; inset-inline-start: 10px; top: 6px; opacity: 0.5">
              <Eye v-if="!showPins.confirm" :size="16" />
              <EyeOff v-else :size="16" />
            </button>
          </div>
        </div>

        <!-- رسائل التحذير الديناميكية -->
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
          <!-- زر التأكيد: أصبح دائماً موجوداً ولكنه "مجمد" بصرياً لحين استيفاء الشروط -->
          <button @click="submit" :disabled="!isValid" class="btn-primary">
            {{ t('confirm') }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>