function getThemeLabel(theme: string): string {
  return theme === 'dark' ? '☀' : '☾';
}

function getThemeAriaLabel(theme: string): string {
  return theme === 'dark' ? 'Светла тема' : 'Черна тема';
}

function setTheme(theme: string, buttons: HTMLButtonElement[]): void {
  const root = document.documentElement;
  const nextTheme = theme === 'dark' ? 'dark' : 'light';
  root.dataset.theme = nextTheme;
  root.style.colorScheme = nextTheme;
  window.localStorage.setItem('theme', nextTheme);

  buttons.forEach((button) => {
    button.textContent = getThemeLabel(nextTheme);
    button.setAttribute('aria-label', `${getThemeAriaLabel(nextTheme)} - смени`);
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
