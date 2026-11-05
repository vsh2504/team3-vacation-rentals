import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// PR 15 fix: the proxy MUST strip /api. Without rewrite, a request to
// /api/listings/search was forwarded to the backend as
// /api/listings/search (not /listings/search), FastAPI returned 404
// {"detail": "Not Found"}, the client returned data=undefined, and
// SearchPage crashed on results.length. That was the console error
// in the 2026-11-04 screenshot: 404 on /api + TypeError at SearchPage:45.
// preview.proxy is set too, so `npm run preview` works the same way.
const proxy = {
  '/api': { target: 'http://localhost:8000', changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, '') },
};
export default defineConfig({ plugins: [react()], server: { port: 5173, proxy }, preview: { port: 5173, proxy } });
