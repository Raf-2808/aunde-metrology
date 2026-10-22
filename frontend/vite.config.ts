import {defineConfig} from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],test:{include:['src/**/*.test.ts']},server:{proxy:{'/api':process.env.API_TARGET||'http://127.0.0.1:8765'}},build:{rollupOptions:{output:{manualChunks:{charts:['echarts'],react:['react','react-dom']}}}}});
