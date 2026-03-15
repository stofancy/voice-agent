import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/voice-agent': {
        target: 'ws://localhost:8765',
        ws: true,
      },
    },
  },
});
