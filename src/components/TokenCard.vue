<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Copy, KeyRound, ShieldCheck, LogIn, LogOut, Building2, User, Circle, ChevronDown, ChevronUp } from '@lucide/vue'
const { t } = useI18n()

const props = defineProps(['token'])
defineEmits(['login', 'logout', 'changePin', 'viewCert'])

const showDetails = ref(false)

// منطق معالجة تاريخ الانتهاء وحساب الحالات التحذيرية
const expiryInfo = computed(() => {
  if (!props.token.certificate_expiry) return null
  
  // تنظيف التاريخ من أي حروف زائدة (مثل Z)
  const cleanDateStr = props.token.certificate_expiry.split('T')[0]
  const expiryDate = new Date(cleanDateStr)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  const diffTime = expiryDate - today
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  
  return {
    date: cleanDateStr,
    days: Math.abs(diffDays),
    isExpired: diffDays < 0,
    isWarning: diffDays >= 0 && diffDays <= 30
  }
})

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    console.log('Copied to clipboard:', text);
  }).catch(err => {
    console.error('Failed to copy:', err);
  });
}
</script>

<template>
  <div class="token-card">
    <div class="token-info">
      <!-- الجزء الأول: العنوان (Label) -->
      <div class="token-header">
        <div class="token-label" :title="t(token.token_type)">
          <!-- نوع التوكن: ايقونة شركة للختم / ايقونة شخص للتوقيع -->
          <Building2 v-if="token.token_type === 'E-Seal'" :size="14" class="token-type-icon" />
          <User v-else :size="14" class="token-type-icon" />
          
          <span>{{ token.label || t('unknown_token') }}</span>

          <!-- لمبة الحالة: أخضر/رمادي بدون هوفر -->
          <Circle 
            :size="8" 
            :fill="token.logged_in ? 'var(--success-color)' : '#94a3b8'"
            :class="token.logged_in ? 'text-success pulse' : 'text-slate-400'"
          />
        </div>
      </div>

      <!-- زر عرض المزيد: يظهر فقط عند تسجيل الدخول ومتمركز في المنتصف -->
      <div v-if="token.logged_in" class="details-toggle-container">
        <button @click="showDetails = !showDetails" class="btn-show-more">
        <component :is="showDetails ? ChevronUp : ChevronDown" :size="12" />
        {{ showDetails ? t('hide_details') : t('show_details') }}
      </button>
      </div>

      <!-- حل الثغرة: الحاوية تفتح فقط إذا كان المستخدم مسجل دخول والتفاصيل مفعلة -->
      <div class="token-details-wrapper" :class="{'is-open': showDetails && token.logged_in}">
        <div class="token-meta">
        <div class="meta-row">
          <span class="meta-label">{{ t('serial') }}:</span>
          <span>{{ token.serial }}</span>
          <button @click="copyToClipboard(token.serial)" class="copy-button btn-icon"><Copy :size="12" /></button>
        </div>
        <div class="meta-row">
          <span class="meta-label">{{ t('issuer') }}:</span>
          <span>{{ token.certificate_issuer || t('not_available') }}</span>
          <button v-if="token.certificate_issuer" @click="copyToClipboard(token.certificate_issuer)" class="copy-button btn-icon"><Copy :size="12" /></button>
        </div>
        <div class="meta-row">
          <span class="meta-label">{{ t('expiry') }}:</span>
            <div v-if="expiryInfo" class="flex flex-col items-end">
              <span :class="{'text-danger': expiryInfo.isExpired}">{{ expiryInfo.date }}</span>
              <span v-if="expiryInfo.isExpired" class="status-expiry expiry-critical">
                {{ t('expired_since', { days: expiryInfo.days }) }}
              </span>
              <span v-else-if="expiryInfo.isWarning" class="status-expiry expiry-warning">
                {{ t('expires_in', { days: expiryInfo.days }) }}
              </span>
            </div>
          <button v-if="token.certificate_expiry" @click="copyToClipboard(expiryInfo?.date)" class="copy-button btn-icon"><Copy :size="12" /></button>
        </div>
        </div>
      </div>
    </div>

    <div class="token-actions" :class="{ 'centered': !token.logged_in }">
      <template v-if="token.logged_in">
        <button @click="$emit('logout', token.serial)" class="btn-action-outline btn-action-danger">
          <LogOut :size="12" style="margin-inline-end: 4px;" /> {{ t('logout') }}
        </button>
        <div class="action-group">
          <button @click="$emit('changePin', token.serial)" class="btn-action-outline">
            <KeyRound :size="10" /> PIN
          </button>
          <button @click="$emit('viewCert', token.serial)" class="btn-action-outline">
            <ShieldCheck :size="10" /> {{ t('show') }}
          </button>
        </div>
      </template>
      <button v-else @click="$emit('login', token.serial)" class="btn-action-main">
        <LogIn :size="14" style="margin-inline-end: 8px;" /> {{ t('login') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
/* لا يوجد CSS خاص هنا، كل شيء في ui-styles.css */
</style>