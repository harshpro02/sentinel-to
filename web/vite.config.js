import { defineConfig } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  define: { CESIUM_BASE_URL: JSON.stringify('/cesium/') },
  plugins: [viteStaticCopy({
    targets: ['Workers', 'ThirdParty', 'Assets', 'Widgets'].map((folder) => ({
      src: `node_modules/cesium/Build/Cesium/${folder}`,
      dest: 'cesium',
    })),
  })],
});
