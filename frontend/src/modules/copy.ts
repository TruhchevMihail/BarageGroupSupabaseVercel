export function initCopyButtons(): void {
  document.querySelectorAll<HTMLElement>('[data-copy]').forEach((button) => {
    button.addEventListener('click', async () => {
      const text = button.getAttribute('data-copy') || '';
      if (!text) {
        return;
      }

      try {
        await navigator.clipboard.writeText(text);
        const originalText = button.textContent;
        button.textContent = 'Копирано';
        window.setTimeout(() => {
          button.textContent = originalText;
        }, 1200);
      } catch (error) {
        console.error('Copy failed', error);
      }
    });
  });
}
