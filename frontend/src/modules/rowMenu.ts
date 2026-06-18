function closeMenu(panel: HTMLElement | null): void {
  if (!panel) {
    return;
  }
  panel.classList.remove('open');
  panel.hidden = true;
}

function openMenu(trigger: HTMLElement, panel: HTMLElement): void {
  const rect = trigger.getBoundingClientRect();
  panel.hidden = false;
  panel.classList.add('open');
  panel.style.top = `${rect.bottom + 8}px`;
  panel.style.left = `${Math.max(12, rect.right - panel.offsetWidth)}px`;
}

export function initRowMenu(): void {
  const menus = Array.from(document.querySelectorAll<HTMLElement>('[data-row-menu]'));
  if (!menus.length) {
    return;
  }

  menus.forEach((menu) => {
    if (menu.dataset.rowMenuBound === 'true') {
      return;
    }
    menu.dataset.rowMenuBound = 'true';

    const trigger = menu.querySelector<HTMLElement>('[data-row-menu-trigger]');
    const panel = menu.querySelector<HTMLElement>('[data-row-menu-panel]');
    if (!trigger || !panel) {
      return;
    }

    panel.hidden = true;
    trigger.addEventListener('click', (event) => {
      event.preventDefault();
      const isOpen = panel.classList.contains('open');
      menus.forEach((otherMenu) => closeMenu(otherMenu.querySelector<HTMLElement>('[data-row-menu-panel]')));
      if (!isOpen) {
        openMenu(trigger, panel);
      }
    });
  });

  if (document.body.dataset.rowMenuGlobalBound !== 'true') {
    document.body.dataset.rowMenuGlobalBound = 'true';

    document.addEventListener('click', (event) => {
      const target = event.target as HTMLElement | null;
      document.querySelectorAll<HTMLElement>('[data-row-menu]').forEach((menu) => {
        if (target && menu.contains(target)) {
          return;
        }
        closeMenu(menu.querySelector<HTMLElement>('[data-row-menu-panel]'));
      });
    });

    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') {
        return;
      }
      document
        .querySelectorAll<HTMLElement>('[data-row-menu]')
        .forEach((menu) => closeMenu(menu.querySelector<HTMLElement>('[data-row-menu-panel]')));
    });
  }
}
