#!/bin/bash
# PR 15 — local run diagnostic. Run this when the frontend shows a blank page or console 404s.
# It checks, in order: backend health, backend search, Vite proxy search.
# All three must return success:true. If the first two pass and the third 404s,
# you are on an old vite.config.js (pull main + restart `npm run dev` — Vite
# config changes need a restart, HMR alone is not enough).
set -e
echo "1. Backend direct:  http://localhost:8000/health"
curl -sf http://localhost:8000/health; echo
echo "2. Backend search:  http://localhost:8000/listings/search?guests=2"
curl -sf "http://localhost:8000/listings/search?guests=2" | head -c 200; echo
echo "3. Via Vite proxy:  http://localhost:5173/api/listings/search?guests=2"
curl -sf "http://localhost:5173/api/listings/search?guests=2" | head -c 200; echo
echo "OK: backend + proxy both work. If the page still crashes, hard-refresh (Ctrl+Shift+R)."
