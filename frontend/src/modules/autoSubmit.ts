export function initAutoSubmit(): void {
  document.querySelectorAll<HTMLFormElement>('form[data-auto-submit]').forEach((form) => {
    if (form.dataset.autoSubmitBound === 'true') {
      return;
    }
    form.dataset.autoSubmitBound = 'true';

    let timerId: number | null = null;
    const submitSoon = (): void => {
      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
      timerId = window.setTimeout(() => form.requestSubmit(), 250);
    };

    form.querySelectorAll<HTMLSelectElement>('select').forEach((select) => {
      select.addEventListener('change', submitSoon);
    });

    form
      .querySelectorAll<HTMLInputElement>('input[type="text"], input[type="search"]')
      .forEach((input) => {
        input.addEventListener('input', submitSoon);
      });
  });
}
