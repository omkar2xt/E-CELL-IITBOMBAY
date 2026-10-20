// StorePulse AI — Frontend Configuration
// Developer: Omkar Gurav

const isBrowser = typeof window !== 'undefined';
const isHttps = isBrowser && window.location.protocol === 'https:';

// In production on web, use configured VITE_API_BASE_URL / VITE_API_BASE; fallback to same-origin relative path, or localhost in local dev
const envApi = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || '').trim();
export const API_BASE = envApi || (isBrowser && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' ? '' : 'http://localhost:8000');

// In production, use configured VITE_WS_URL or protocol-aware WebSocket endpoint
const envWs = (import.meta.env.VITE_WS_URL || '').trim();
export const WS_URL = envWs || (isBrowser && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
  ? `${isHttps ? 'wss:' : 'ws:'}//${window.location.host}/ws`
  : 'ws://localhost:8000/ws');
