import { showToast } from './toast';

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

export function initCopyButtons(): void {
  document.querySelectorAll<HTMLElement>('[data-copy], [data-copy-text], [data-copy-current-url]').forEach((button) => {
    button.addEventListener('click', async () => {
      const targetSelector = button.getAttribute('data-copy-target');
      const targetText = targetSelector ? document.querySelector<HTMLElement>(targetSelector)?.textContent?.trim() : '';
      const text = button.getAttribute('data-copy-text')
        || button.getAttribute('data-copy')
        || targetText
        || (button.hasAttribute('data-copy-current-url') ? window.location.href : '');
      if (!text) {
        return;
      }

      try {
        await writeText(text);
        const originalText = button.textContent;
        button.textContent = 'Копирано';
        showToast('Копирано');
        window.setTimeout(() => {
          button.textContent = originalText;
        }, 1200);
      } catch (error) {
        console.error('Copy failed', error);
        showToast('Неуспешно копиране', 'error');
      }
    });
  });
}
