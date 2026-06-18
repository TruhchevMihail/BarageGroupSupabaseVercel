import { closeCommandPalette } from './commandPalette';
import { isEditableTarget } from './domGuards';

const GO_TIMEOUT_MS = 900;

function focusMainSearch(): void {
  const search = document.querySelector<HTMLInputElement>(
    '[data-main-search], input[type="search"], .assets-search-input',
  );
  if (search) {
    search.focus();
    search.select?.();
  }
}

export function initKeyboardShortcuts(): void {
  let goModeUntil = 0;

  document.addEventListener('keydown', (event) => {
    if (isEditableTarget(event.target)) {
      return;
    }

    const key = event.key.toLowerCase();
    const now = Date.now();

    if (event.key === 'Escape') {
      closeCommandPalette();
      return;
    }

    if (event.key === '/') {
      event.preventDefault();
      focusMainSearch();
      return;
    }

    if (key === 'g') {
      goModeUntil = now + GO_TIMEOUT_MS;
      return;
    }

    if (now > goModeUntil) {
      return;
    }

    const targetUrl: Record<string, string> = {
      d: '/dashboard',
      a: '/assets',
      l: '/locations',
      r: '/requests',
      u: '/users',
    };

    const url = targetUrl[key];
    if (!url) {
      return;
    }

    event.preventDefault();
    goModeUntil = 0;
    window.location.href = url;
  });
}
