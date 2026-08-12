import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: './', // لضمان عمل المسارات داخل ملفات EXE المجمعة
  build: {
    outDir: resolve(__dirname, 'interfaces/ui/dist'), // مسار مطلق لضمان الدقة
    emptyOutDir: true,
    assetsDir: 'assets'
  }
})