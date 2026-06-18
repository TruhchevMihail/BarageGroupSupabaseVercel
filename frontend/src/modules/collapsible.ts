export function initCollapsibles(): void {
  document.querySelectorAll<HTMLElement>('[data-collapsible]').forEach((section, index) => {
    const heading = section.querySelector<HTMLElement>('[data-collapsible-title]');
    const body = section.querySelector<HTMLElement>('[data-collapsible-body]');
    if (!heading || !body) {
      return;
    }

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'collapsible-toggle btn-secondary btn-small';
    button.textContent = 'Скрий';
    const bodyId = body.id || `collapsible-section-${index}`;
    body.id = bodyId;
    button.setAttribute('aria-controls', bodyId);
    button.setAttribute('aria-expanded', 'true');
    heading.appendChild(button);

    button.addEventListener('click', () => {
      const expanded = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', String(!expanded));
      button.textContent = expanded ? 'Покажи' : 'Скрий';
      body.hidden = expanded;
    });
  });
}
