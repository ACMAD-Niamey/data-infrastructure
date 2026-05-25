import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react-swc';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

const DEFAULT_BASE_URL = 'https://e-safari.acmad.org';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const baseUrl = env.VITE_BASE_URL || env.BASE_URL || DEFAULT_BASE_URL;

  return {
    plugins: [tailwindcss(), react()],
    define: {
      'import.meta.env.VITE_BASE_URL': JSON.stringify(baseUrl),
    },
    resolve: {
      extensions: ['.js', '.jsx', '.ts', '.tsx', '.json'],
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      target: 'esnext',
      outDir: 'build',
    },
    server: {
      port: 3000,
      open: true,
      proxy: {
        '/api': {
          target: 'http://localhost',
          changeOrigin: true,
        },
      },
    },
    optimizeDeps: {
      include: ['react', 'react-dom', 'zustand'],
    },
  };
});
