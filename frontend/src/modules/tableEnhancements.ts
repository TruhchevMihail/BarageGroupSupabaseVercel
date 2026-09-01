type SortDirection = 'asc' | 'desc';

function getCurrentSort(defaultKey: string, defaultDirection: SortDirection): { key: string; direction: SortDirection } {
  const params = new URLSearchParams(window.location.search);
  const direction = params.get('direction') === 'desc' ? 'desc' : defaultDirection;
  return {
    key: params.get('sort') || defaultKey,
    direction,
  };
}

function updateSortArrows(table: HTMLTableElement, defaultKey: string, defaultDirection: SortDirection): void {
  const current = getCurrentSort(defaultKey, defaultDirection);
  table.querySelectorAll<HTMLElement>('.table-sort[data-sort-key]').forEach((control) => {
    const arrow = control.querySelector<HTMLElement>('.sort-arrow');
    if (!arrow) {
      return;
    }
    arrow.textContent = control.dataset.sortKey === current.key ? (current.direction === 'asc' ? '▲' : '▼') : '';
  });
}

function requestSubmit(form: HTMLFormElement): void {
  if (typeof form.requestSubmit === 'function') {
    form.requestSubmit();
    return;
  }

  if (form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))) {
    form.submit();
  }
}

function initAssetsTable(): void {
  const table = document.getElementById('assets-table') as HTMLTableElement | null;
  const form = document.querySelector<HTMLFormElement>('[data-assets-filter-form]');
  if (!table || table.dataset.tableEnhancementsBound === 'true') {
    return;
  }
  table.dataset.tableEnhancementsBound = 'true';

  const searchInput = form?.querySelector<HTMLInputElement>('[data-list-search]');
  const locationSelect = form?.querySelector<HTMLSelectElement>('select[name="location"]');
  let submitTimer: number | null = null;

  const scheduleSubmit = (): void => {
    if (!form) {
      return;
    }
    if (submitTimer !== null) {
      window.clearTimeout(submitTimer);
    }
    submitTimer = window.setTimeout(() => requestSubmit(form), 250);
  };

  searchInput?.addEventListener('input', scheduleSubmit);
  locationSelect?.addEventListener('change', () => {
    if (form) {
      requestSubmit(form);
    }
  });
  updateSortArrows(table, 'inventory', 'asc');
}

function initBackendSortedTable(tableId: string, defaultKey: string, defaultDirection: SortDirection): void {
  const table = document.getElementById(tableId) as HTMLTableElement | null;
  if (!table || table.dataset.tableEnhancementsBound === 'true') {
    return;
  }
  table.dataset.tableEnhancementsBound = 'true';
  updateSortArrows(table, defaultKey, defaultDirection);
}

function initRowHighlight(): void {
  const params = new URLSearchParams(window.location.search);
  const highlightId = params.get('highlight');
  if (!highlightId) {
    return;
  }

  const row = document.querySelector<HTMLElement>(`[data-highlight-id="${CSS.escape(highlightId)}"]`);
  if (!row || row.dataset.rowHighlightBound === 'true') {
    return;
  }
  row.dataset.rowHighlightBound = 'true';

  row.classList.add('row-highlighted');
  row.scrollIntoView({ behavior: 'smooth', block: 'center' });
  window.setTimeout(() => row.classList.remove('row-highlighted'), 3200);
}

export function initTableEnhancements(): void {
  initAssetsTable();
  initBackendSortedTable('users-table', 'name', 'asc');
  initBackendSortedTable('requests-table', 'newest', 'desc');
  initRowHighlight();
}
