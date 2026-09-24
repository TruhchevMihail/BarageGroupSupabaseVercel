function setTheme(theme: string, buttons: HTMLButtonElement[]): void {
  const nextTheme = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.dataset.theme = nextTheme;
  document.documentElement.style.colorScheme = nextTheme;
  window.localStorage.setItem('theme', nextTheme);

  buttons.forEach((button) => {
    const label = button.querySelector<HTMLElement>('.theme-toggle-label');
    const nextLabel = nextTheme === 'dark' ? 'Светла тема' : 'Тъмна тема';
    if (label) label.textContent = nextLabel;
    button.setAttribute('aria-label', `${nextLabel} - смени`);
  });
}

export function initThemeToggle(): void {
  const buttons = Array.from(
    document.querySelectorAll<HTMLButtonElement>('[data-theme-toggle]'),
  );
  if (!buttons.length) {
    return;
  }

  setTheme(document.documentElement.dataset.theme || 'light', buttons);
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark', buttons);
    });
  });
}
