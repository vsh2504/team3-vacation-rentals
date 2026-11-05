// Vite dev/preview configuration.
//
// The proxy MUST strip /api: a request to /api/listings/search is forwarded
// to FastAPI as /listings/search. Without the rewrite FastAPI returns 404 and
// the UI used to crash on results.length (PR 15 regression).
//
// Proxy target resolution, in order:
//   1. STAYNEST_API_URL   — set by scripts/start_local.sh and Docker Compose
//   2. VITE_API_PROXY_TARGET — optional manual override in frontend/.env
//   3. http://127.0.0.1:8000 — the direct `uvicorn` default
// Keeping this configurable is what lets the same frontend image talk to
// `api:8000` inside Compose and to `127.0.0.1:8000` on the host.
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const fileEnv = loadEnv(mode, process.cwd(), '');
  const apiTarget =
    process.env.STAYNEST_API_URL ||
    fileEnv.STAYNEST_API_URL ||
    fileEnv.VITE_API_PROXY_TARGET ||
    'http://127.0.0.1:8000';

  const proxy = {
    '/api': {
      target: apiTarget,
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  };

  return {
    plugins: [react()],
    server: { port: 5173, proxy },
    preview: { port: 5173, proxy },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.js'],
      include: ['src/**/*.test.{js,jsx}'],
      coverage: {
        provider: 'v8',
        // The pattern layer (api, state, services, validation, guards, shell)
        // is held at 100%. Large page components are exercised by the
        // browser acceptance suite (tests/run-browser-acceptance.sh).
        include: [
          'src/api/**', 'src/state/**', 'src/services/**', 'src/validation/**',
          'src/theme.js', 'src/googleMaps.js', 'src/App.jsx',
          'src/components/RoleGuard.jsx', 'src/components/ErrorBoundary.jsx',
          'src/components/ThemeToggle.jsx', 'src/components/ui/**',
        ],
        thresholds: { lines: 100, statements: 100, functions: 100, branches: 100 },
      },
    },
  };
});
