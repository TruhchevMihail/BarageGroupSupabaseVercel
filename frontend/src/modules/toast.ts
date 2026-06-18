let toastRoot: HTMLElement | null = null;

function ensureToastRoot(): HTMLElement {
  if (toastRoot) {
    return toastRoot;
  }

  toastRoot = document.createElement('div');
  toastRoot.className = 'toast-stack';
  toastRoot.setAttribute('aria-live', 'polite');
  toastRoot.setAttribute('aria-atomic', 'true');
  document.body.appendChild(toastRoot);
  return toastRoot;
}

export function showToast(message: string, variant: 'success' | 'error' = 'success'): void {
  const root = ensureToastRoot();
  const toast = document.createElement('div');
  toast.className = `toast toast-${variant}`;
  toast.textContent = message;
  root.appendChild(toast);

  window.setTimeout(() => {
    toast.classList.add('toast-out');
    window.setTimeout(() => toast.remove(), 180);
  }, 2200);
}
