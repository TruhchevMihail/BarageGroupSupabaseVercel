import { showToast } from './toast';

const COPY_SELECTOR = '[data-copyable], [data-copy], [data-copy-text], [data-copy-current-url]';
const EMPTY_COPY_VALUES = new Set(['', '-', '—']);

async function writeText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.top = '-999px';
  document.body.appendChild(textarea);
  textarea.select();
  const ok = document.execCommand('copy');
  textarea.remove();

  if (!ok) {
    throw new Error('Copy failed');
  }
}

function readCopyText(control: HTMLElement): string {
  const targetSelector = control.getAttribute('data-copy-target');
  const targetText = targetSelector ? document.querySelector<HTMLElement>(targetSelector)?.textContent?.trim() : '';

  return (
    control.getAttribute('data-copy-value')
    || control.getAttribute('data-copy-text')
    || control.getAttribute('data-copy')
    || targetText
    || (control.hasAttribute('data-copy-current-url') ? window.location.href : '')
    || control.textContent?.trim()
    || ''
  ).trim();
}

function shouldSkipCopy(_control: HTMLElement, text: string): boolean {
  return !text || EMPTY_COPY_VALUES.has(text);
}

function flashCopiedState(control: HTMLElement): void {
  control.classList.add('copy-feedback-active');
  window.setTimeout(() => control.classList.remove('copy-feedback-active'), 720);
}

async function handleCopy(control: HTMLElement): Promise<void> {
  const text = readCopyText(control);
  if (shouldSkipCopy(control, text)) {
    return;
  }

  try {
    await writeText(text);
    flashCopiedState(control);
    showToast('Копирано');
  } catch (error) {
    console.error('Copy failed', error);
    showToast('Неуспешно копиране', 'error');
  }
}

export function initCopyButtons(): void {
  if (document.body.dataset.copyDelegationBound === 'true') {
    return;
  }
  document.body.dataset.copyDelegationBound = 'true';

  document.addEventListener('click', (event) => {
    const target = event.target as HTMLElement | null;
    const control = target?.closest<HTMLElement>(COPY_SELECTOR);
    if (!control) {
      return;
    }

    if (control.matches('[data-copyable]')) {
      event.preventDefault();
      event.stopPropagation();
    }

    void handleCopy(control);
  });
}
