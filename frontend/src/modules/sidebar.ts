export function initSidebarToggle(): void {
  const sidebar = document.querySelector<HTMLElement>('.sidebar');
  const toggle = document.querySelector<HTMLButtonElement>('[data-sidebar-toggle]');
  if (!sidebar || !toggle || toggle.dataset.sidebarBound === 'true') {
    return;
  }

  toggle.dataset.sidebarBound = 'true';

  const setOpen = (open: boolean): void => {
    sidebar.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    toggle.setAttribute('aria-label', open ? 'Затвори меню' : 'Отвори меню');
  };

  toggle.addEventListener('click', () => {
    setOpen(!sidebar.classList.contains('is-open'));
  });

  sidebar.querySelectorAll<HTMLAnchorElement>('.sidebar-nav a').forEach((link) => {
    link.addEventListener('click', () => {
      if (window.matchMedia('(max-width: 1000px)').matches) {
        setOpen(false);
      }
    });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && sidebar.classList.contains('is-open')) {
      setOpen(false);
      toggle.focus();
    }
  });
}
