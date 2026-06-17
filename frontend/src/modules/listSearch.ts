function normalize(value: string | null | undefined): string {
  return (value || '').toString().trim().toLowerCase();
}

export function initListSearch(): void {
  document.querySelectorAll<HTMLFormElement>('form[data-list-search-form]').forEach((form) => {
    const searchInput = form.querySelector<HTMLInputElement>('[data-list-search]');
    const scope = form.closest('main') || document;
    const items = Array.from(scope.querySelectorAll<HTMLElement>('[data-list-search-item]'));

    if (!searchInput || !items.length) {
      return;
    }

    const applyFilter = (): void => {
      const query = normalize(searchInput.value);
      items.forEach((item) => {
        const haystack = normalize(item.getAttribute('data-search-text') || item.textContent || '');
        item.style.display = !query || haystack.includes(query) ? '' : 'none';
      });
    };

    searchInput.addEventListener('input', applyFilter);
    applyFilter();
  });
}
