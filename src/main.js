import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import './assets/main.css'

// استيراد ملفات الترجمة مباشرة
import ar from './assets/locales/ar.json'
import en from './assets/locales/en.json'

const i18n = createI18n({
  legacy: false, // نستخدم Composition API
  locale: 'ar',  // اللغة الافتراضية
  fallbackLocale: 'en',
  messages: { ar, en }
})

const app = createApp(App)
app.use(i18n)
app.mount('#app')