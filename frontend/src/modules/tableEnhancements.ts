type SortDirection = 'asc' | 'desc';

function normalize(value: string | null | undefined): string {
  return (value || '').toString().trim().toLowerCase();
}

function initAssetsTable(): void {
  const table = document.getElementById('assets-table') as HTMLTableElement | null;
  if (!table) {
    return;
  }

  const form = document.querySelector<HTMLFormElement>('[data-assets-filter-form]');
  const headers = Array.from(table.querySelectorAll<HTMLButtonElement>('.table-sort'));
  const searchInput = form?.querySelector<HTMLInputElement>('[data-list-search]');
  const locationSelect = form?.querySelector<HTMLSelectElement>('select[name="location"]');
  let submitTimer: number | null = null;

  const getCurrentSort = (): { key: string; direction: SortDirection } => {
    const params = new URLSearchParams(window.location.search);
    return {
      key: params.get('sort') || 'inventory',
      direction: (params.get('direction') || 'asc') as SortDirection,
    };
  };

  const updateArrows = (): void => {
    const current = getCurrentSort();
    headers.forEach((header) => {
      const arrow = header.querySelector<HTMLElement>('.sort-arrow');
      if (!arrow) {
        return;
      }
      arrow.textContent = header.dataset.sortKey === current.key ? (current.direction === 'asc' ? '▲' : '▼') : '';
    });
  };

  const scheduleSubmit = (): void => {
    if (!form) {
      return;
    }
    if (submitTimer !== null) {
      window.clearTimeout(submitTimer);
    }
    submitTimer = window.setTimeout(() => form.submit(), 250);
  };

  const navigateWithSort = (sortKey: string): void => {
    const current = getCurrentSort();
    const params = new URLSearchParams(window.location.search);
    let newDirection: SortDirection = 'asc';
    if (current.key === sortKey && current.direction === 'asc') {
      newDirection = 'desc';
    }
    params.set('sort', sortKey);
    params.set('direction', newDirection);
    params.set('page', '1');
    window.location.search = params.toString();
  };

  headers.forEach((header) => {
    header.addEventListener('click', () => navigateWithSort(header.dataset.sortKey || 'inventory'));
  });

  searchInput?.addEventListener('input', scheduleSubmit);
  locationSelect?.addEventListener('change', () => form?.submit());
  updateArrows();
}

function initUsersTable(): void {
  const table = document.getElementById('users-table') as HTMLTableElement | null;
  const search = document.getElementById('users-search') as HTMLInputElement | null;
  if (!table) {
    return;
  }

  const tbody = table.tBodies[0];
  const headers = Array.from(table.querySelectorAll<HTMLButtonElement>('.table-sort'));
  const sortableKeys = new Set(['name', 'role', 'location', 'status']);

  const compare = (a: string | null | undefined, b: string | null | undefined): number =>
    normalize(a).localeCompare(normalize(b), 'bg');

  const getCurrentSort = (): { key: string; direction: SortDirection } => {
    const params = new URLSearchParams(window.location.search);
    return {
      key: params.get('sort') || 'name',
      direction: (params.get('direction') || 'asc') as SortDirection,
    };
  };

  const updateArrows = (): void => {
    const current = getCurrentSort();
    headers.forEach((header) => {
      const arrow = header.querySelector<HTMLElement>('.sort-arrow');
      if (!arrow) {
        return;
      }
      arrow.textContent = header.dataset.sortKey === current.key ? (current.direction === 'asc' ? '▲' : '▼') : '';
    });
  };

  const matchesSearch = (row: HTMLTableRowElement, query: string): boolean => {
    if (!query) {
      return true;
    }
    const haystack = [
      row.dataset.name,
      row.dataset.email,
      row.dataset.phone,
      row.dataset.role,
      row.dataset.location,
      row.dataset.status,
    ]
      .map(normalize)
      .join(' ');
    return haystack.includes(query);
  };

  const applySearchFilter = (): void => {
    const query = normalize(search?.value);
    const rows = Array.from(tbody.querySelectorAll<HTMLTableRowElement>('tr')).filter((row) => row.dataset.name);
    rows.forEach((row) => {
      row.style.display = matchesSearch(row, query) ? '' : 'none';
    });
  };

  const navigateWithSort = (sortKey: string): void => {
    if (!sortableKeys.has(sortKey)) {
      return;
    }
    const current = getCurrentSort();
    const params = new URLSearchParams(window.location.search);
    let newDirection: SortDirection = 'asc';
    if (current.key === sortKey && current.direction === 'asc') {
      newDirection = 'desc';
    }
    params.set('sort', sortKey);
    params.set('direction', newDirection);
    params.set('page', '1');
    window.location.search = params.toString();
  };

  headers.forEach((header) => {
    header.addEventListener('click', () => navigateWithSort(header.dataset.sortKey || 'name'));
  });

  search?.addEventListener('input', applySearchFilter);
  applySearchFilter();
  updateArrows();
}

function initRequestsTable(): void {
  const table = document.getElementById('requests-table') as HTMLTableElement | null;
  const search = document.getElementById('requests-search') as HTMLInputElement | null;
  if (!table) {
    return;
  }

  const tbody = table.tBodies[0];
  const headers = Array.from(table.querySelectorAll<HTMLButtonElement>('.table-sort'));

  const getRowValue = (row: HTMLTableRowElement, key: string): string | undefined => {
    if (key === 'requested_by') {
      return row.dataset.requestedBy;
    }
    if (key === 'created_at') {
      return row.dataset.createdAt;
    }
    if (key === 'request_kind') {
      return row.dataset.requestKind;
    }
    return row.dataset[key];
  };

  const compareText = (a: string | null | undefined, b: string | null | undefined): number =>
    normalize(a).localeCompare(normalize(b), 'bg');

  const compareValues = (rowA: HTMLTableRowElement, rowB: HTMLTableRowElement, key: string): number => {
    if (key === 'id') {
      return Number(rowA.dataset.id) - Number(rowB.dataset.id);
    }
    if (key === 'created_at') {
      return new Date(rowA.dataset.createdAt || '').getTime() - new Date(rowB.dataset.createdAt || '').getTime();
    }
    return compareText(getRowValue(rowA, key), getRowValue(rowB, key));
  };

  const getCurrentSort = (): { key: string; direction: SortDirection } => {
    const params = new URLSearchParams(window.location.search);
    return {
      key: params.get('sort') || 'created_at',
      direction: (params.get('direction') || 'desc') as SortDirection,
    };
  };

  const updateArrows = (): void => {
    const current = getCurrentSort();
    headers.forEach((header) => {
      const arrow = header.querySelector<HTMLElement>('.sort-arrow');
      if (!arrow) {
        return;
      }
      arrow.textContent = header.dataset.sortKey === current.key ? (current.direction === 'asc' ? '▲' : '▼') : '';
    });
  };

  const applySearchFilter = (): void => {
    const query = normalize(search?.value);
    const rows = Array.from(tbody.querySelectorAll<HTMLTableRowElement>('tr')).filter((row) => row.dataset.id);
    rows.forEach((row) => {
      const haystack = [
        row.dataset.id,
        row.dataset.asset,
        row.dataset.location,
        row.dataset.status,
        row.dataset.requestKind,
        row.dataset.requestedBy,
        row.dataset.createdAt,
      ]
        .map(normalize)
        .join(' ');
      row.style.display = !query || haystack.includes(query) ? '' : 'none';
    });
  };

  const navigateWithSort = (sortKey: string): void => {
    const current = getCurrentSort();
    const params = new URLSearchParams(window.location.search);
    let newDirection: SortDirection = 'asc';
    if (current.key === sortKey && current.direction === 'asc') {
      newDirection = 'desc';
    }
    params.set('sort', sortKey);
    params.set('direction', newDirection);
    params.set('page', '1');
    window.location.search = params.toString();
  };

  headers.forEach((header) => {
    header.addEventListener('click', () => navigateWithSort(header.dataset.sortKey || 'created_at'));
  });

  search?.addEventListener('input', applySearchFilter);
  applySearchFilter();
  updateArrows();
}

function initRowHighlight(): void {
  const params = new URLSearchParams(window.location.search);
  const highlightId = params.get('highlight');
  if (!highlightId) {
    return;
  }

  const row = document.querySelector<HTMLElement>(`[data-highlight-id="${CSS.escape(highlightId)}"]`);
  if (!row) {
    return;
  }

  row.classList.add('row-highlighted');
  row.scrollIntoView({ behavior: 'smooth', block: 'center' });
  window.setTimeout(() => row.classList.remove('row-highlighted'), 3200);
}

export function initTableEnhancements(): void {
  initAssetsTable();
  initUsersTable();
  initRequestsTable();
  initRowHighlight();
}
