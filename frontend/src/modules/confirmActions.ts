export function initConfirmActions(): void {
  document.querySelectorAll<HTMLFormElement>('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.dataset.confirm || 'Сигурни ли сте, че искате да продължите?';
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll<HTMLElement>('[data-confirm]:not(form)').forEach((control) => {
    control.addEventListener('click', (event) => {
      const message = control.dataset.confirm || 'Сигурни ли сте, че искате да продължите?';
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
}
