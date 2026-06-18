function syncSubmitState(form: HTMLFormElement): void {
  if (form.dataset.searchFormBound === 'true') {
    return;
  }
  form.dataset.searchFormBound = 'true';

  const input = form.querySelector<HTMLInputElement>('input[name="q"]');
  const button = form.querySelector<HTMLButtonElement>('button[type="submit"]');
  if (!input || !button) {
    return;
  }

  const sync = (): void => {
    button.disabled = !input.value.trim();
  };

  input.addEventListener('input', sync);
  sync();
}

export function initSearchForms(): void {
  document.querySelectorAll<HTMLFormElement>('.dashboard-search').forEach(syncSubmitState);
}
