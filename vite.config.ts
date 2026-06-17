import { defineConfig } from 'vite';

export default defineConfig({
  root: 'frontend',
  build: {
    outDir: '../public/static',
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: './frontend/src/main.ts',
      output: {
        entryFileNames: 'app.js',
        chunkFileNames: 'app.js',
        assetFileNames: (assetInfo) => {
          if ((assetInfo.name || '').endsWith('.css')) {
            return 'styles.css';
          }
          return '[name][extname]';
        },
      },
    },
  },
});
