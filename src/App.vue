<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Languages, Sun, Moon, X, Minus, PlugZap, Loader2, Activity } from '@lucide/vue'

// Components
import LoginModal from './components/modals/LoginModal.vue'
import ChangePinModal from './components/modals/ChangePinModal.vue'
import ConfirmModal from './components/modals/ConfirmModal.vue'
import ToastNotification from './components/ToastNotification.vue'
import TokenCard from './components/TokenCard.vue'

const { t, locale } = useI18n()

// استيراد الصور مباشرة عبر Vite
import appLogo from './assets/ESA.png'
import dtsLogo from './assets/dts.png'

// --- State ---
const tokens = ref([])
const theme = ref('light')
const appPrefix = ref('ESA')
const version = ref('2.1.0')
const activeSerial = ref(null)
const isInitialLoading = ref(true) // حالة تحميل أولية لضمان استقرار البداية
const pinAttempts = ref(0) // عداد المحاولات الفاشلة

// دالة مساعدة لفتح المودالات وتصفير العداد
const openModal = (type, serial) => {
  if (activeSerial.value !== serial) pinAttempts.value = 0 // تصفير العداد عند تغيير التوكن
  activeSerial.value = serial
  modals.value[type] = true
}

// Modals State
const modals = ref({
  pin: false,
  changePin: false,
  exit: false,
  logout: false
})

// Toasts State
const toasts = ref([])

const showToast = (message, type = 'success') => {
  const id = Date.now()
  toasts.value.push({ id, message, type })
  // Offline-friendly: no remote audio fetch for toast UX
  setTimeout(() => toasts.value = toasts.value.filter(t => t.id !== id), 3000)
}

// --- Helpers ---
// --- API Bridge Calls ---
const fetchTokens = async () => {
  try {
    if (window.pywebview?.api?.get_tokens) {
      const data = await window.pywebview.api.get_tokens()
      tokens.value = data || []
      if (isInitialLoading.value) isInitialLoading.value = false
    }
  } catch (err) {
    console.error("Fetch Tokens Error:", err)
  }
}

const initialize = async () => {
    if (!window.pywebview?.api) return;
    
    try {
        isInitialLoading.value = true
        // 1. جلب البيانات الأساسية السريعة (اللغة، الإصدار)
        const data = await window.pywebview.api.get_current_translations?.()
        if (data) {
            locale.value = data.lang || 'ar'
            appPrefix.value = data.prefix || 'ESA'
            version.value = data.version || '2.1.0'
            applyThemeClass(data.theme || 'light')
            updateDocumentMeta()
        }
        
        // 2. إخفاء اللودر فوراً لفك تجميد الواجهة حتى لو البايثون مشغول
        isInitialLoading.value = false 
        
        // 3. جلب التوكنات (عملية قد تكون بطيئة) في الخلفية
        fetchTokens()
        setInterval(fetchTokens, 3000)
    } catch (err) {
        console.error("Critical UI Initialization Error:", err)
        isInitialLoading.value = false
    }
}

const toggleLanguage = async () => {
  const result = await window.pywebview.api.toggle_language?.()
  locale.value = result.lang
  updateDocumentMeta()
  showToast(t('lang_toggle_success'), 'success')
}

const updateDocumentMeta = () => {
  document.documentElement.dir = locale.value === 'ar' ? 'rtl' : 'ltr'
  document.documentElement.lang = locale.value
}

const applyThemeClass = (value) => {
  const next = value === 'dark' ? 'dark' : 'light'
  theme.value = next
  document.documentElement.classList.toggle('dark', next === 'dark')
  document.documentElement.classList.toggle('light', next === 'light')
  document.body.classList.toggle('dark', next === 'dark')
}

const toggleTheme = async () => {
  const next = theme.value === 'light' ? 'dark' : 'light'
  applyThemeClass(next)
  const result = await window.pywebview.api.set_theme?.(next)
  if (result && result.success === false) {
    showToast(result.message || t('BRIDGE_ERROR'), 'error')
  }
}

// --- Actions ---
const handleLogin = async (pin) => {
  const result = await window.pywebview.api.login?.(activeSerial.value, pin)
  
  if (result.success) {
    modals.value.pin = false
    pinAttempts.value = 0
  } else if (result.error_code === 'PIN_INVALID') {
    pinAttempts.value++
  }

  // إصلاح منطق الرسائل: إعطاء الأولوية لعداد المحاولات عند الخطأ
  let displayMsg;
  if (result.success) {
    displayMsg = result.message;
  } else if (result.error_code === 'PIN_INVALID') {
    displayMsg = pinAttempts.value >= 8 ? t('attempts_exhausted') : t('attempts_left', { count: 8 - pinAttempts.value });
  } else {
    displayMsg = result.error_code ? t(result.error_code) : result.message;
  }

  showToast(displayMsg, result.success ? 'success' : 'error')
  fetchTokens()
}

const handleLogout = async () => {
  modals.value.logout = false
  const result = await window.pywebview.api.logout?.(activeSerial.value)
  const displayMsg = result.success ? result.message : (result.error_code ? t(result.error_code) : result.message)
  showToast(displayMsg, result.success ? 'success' : 'error')
  fetchTokens()
}

const handleViewCert = async (serial) => {
  const result = await window.pywebview.api.view_cert?.(serial)
  if (!result.success) showToast(result.message, 'error')
}

const handleChangePin = async (data) => {
  const result = await window.pywebview.api.change_pin?.(activeSerial.value, data.old, data.new)
  
  if (result.success) {
    pinAttempts.value = 0
    modals.value.changePin = false
  } else if (result.error_code === 'PIN_INVALID') {
    pinAttempts.value++
  }

  let displayMsg;
  if (result.success) {
    displayMsg = result.message;
  } else if (result.error_code === 'PIN_INVALID') {
    displayMsg = pinAttempts.value >= 8 ? t('attempts_exhausted') : t('attempts_left', { count: 8 - pinAttempts.value });
  } else {
    displayMsg = result.error_code ? t(result.error_code) : result.message;
  }

  showToast(displayMsg, result.success ? 'success' : 'error')
  fetchTokens()
}

const openExitModal = () => modals.value.exit = true
const closeApp = () => {
  isInitialLoading.value = true // Show loader to prevent further interaction
  window.pywebview?.api?.close_app()
}

const handleMinimize = () => {
  window.pywebview?.api?.hide_to_tray()
}


onMounted(() => {
  const checkApi = setInterval(() => {
    if (window.pywebview?.api) {
      clearInterval(checkApi)
      initialize()
    }
  }, 100)
})
</script>

<template>
  <div class="app-wrapper">
    
    <!-- Title Bar -->
    <div class="title-bar drag-area">
      <div class="title-bar-content">
        <span class="app-title-animated">{{ t('app_title') }}</span>
      </div>
      <div class="header-controls no-drag">
        <button @click="toggleLanguage" class="btn-lang-elite">
          <Languages :size="14" />
          <span>{{ locale === 'ar' ? 'EN' : 'ع' }}</span>
        </button>
        <button @click="toggleTheme" class="btn-icon">
          <Sun v-if="theme === 'light'" :size="16" color="#f59e0b" />
          <Moon v-else :size="16" />
        </button>

        <button @click="handleMinimize" class="btn-icon" :title="t('to_tray')">
          <Minus :size="20" />
        </button>

        <button @click="openExitModal" class="btn-close">
          <X :size="20" />
        </button>
      </div>
    </div>

    <main id="app-body" class="main-content">
      <!-- Header Logo -->
      <div class="logo-section">
        <div class="logo-container">
          <img :src="appLogo" class="app-logo" :alt="appPrefix">
          <span v-if="!appLogo" class="fallback-logo">{{ appPrefix }}</span>
        </div>
      </div>

      <!-- Initial Loading State -->
      <div v-if="isInitialLoading" class="empty-state">
        <Loader2 class="spinner animate-spin" :size="40" />
        <p class="mt-4 opacity-50">{{ locale === 'ar' ? 'جاري فحص التوكنات...' : 'Scanning for tokens...' }}</p>
      </div>

      <!-- No Tokens Message -->
      <div v-else-if="tokens.length === 0" class="empty-state">
        <PlugZap class="empty-icon" :size="48" />
        <p>{{ t('no_tokens') }}</p>
      </div>

      <!-- Tokens List -->
      <template v-else>
        <header class="status-bar">
          <Activity :size="16" class="text-success pulse" />
          <span class="label">{{ t('tokens_heading') }}</span>
        </header>
        
        <div class="tokens-list">
            <TokenCard 
              v-for="token in tokens" 
              :key="token.serial" 
              :token="token"
              @login="(s) => openModal('pin', s)"
              @logout="(s) => openModal('logout', s)"
              @changePin="(s) => openModal('changePin', s)"
              @viewCert="handleViewCert"
            />
        </div>
      </template>
    </main>

    <!-- Footer -->
    <div class="footer-logo">
      <img :src="dtsLogo" class="dts-mini-logo" style="width: 2.5rem; height: 2.5rem;">
    </div>
    <footer class="app-footer">
      <div class="footer-content">
        <a href="https://dts-eg.com" target="_blank" class="powered-link">
          {{ t('powered_by') }}
        </a>
        <span class="opacity-40">v{{ version }}</span>
      </div>
    </footer>

    <!-- New Modals Architecture -->
    <LoginModal :show="modals.pin" :attempts="pinAttempts" @close="modals.pin = false" @submit="handleLogin" />
    <ChangePinModal :show="modals.changePin" :attempts="pinAttempts" @close="modals.changePin = false" @submit="handleChangePin" />
    <ConfirmModal :show="modals.exit" :title="t('confirm_exit')" type="danger" @close="modals.exit = false" @confirm="closeApp" />
    <ConfirmModal :show="modals.logout" :title="t('confirm_logout')" type="danger" @close="modals.logout = false" @confirm="handleLogout" />
    
    <!-- Global Toasts -->
    <ToastNotification :toasts="toasts" />

  </div>
</template>

<style>
/* تم تفريغ التنسيقات من هنا لتوحيدها في الملف الخارجي كما طلبت */
/* الـ app-wrapper يأخذ تنسيقه الآن بالكامل من ui-styles.css */
</style>