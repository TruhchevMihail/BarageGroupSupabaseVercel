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
  const tbody = table.tBodies[0];
  const headers = Array.from(table.querySelectorAll<HTMLButtonElement>('.table-sort'));
  const searchInput = form?.querySelector<HTMLInputElement>('[data-list-search]');
  const locationSelect = form?.querySelector<HTMLSelectElement>('select[name="location"]');
  const state: { key: string; dir: SortDirection } = { key: 'inventory', dir: 'asc' };
  let submitTimer: number | null = null;

  const parseInventory = (value: string | null | undefined): number => {
    const match = (value || '').toString().match(/\d+/);
    return match ? Number.parseInt(match[0], 10) : Number.POSITIVE_INFINITY;
  };

  const compare = (a: string | null | undefined, b: string | null | undefined): number =>
    normalize(a).localeCompare(normalize(b), 'bg');

  const compareByKey = (key: string, a: string | null | undefined, b: string | null | undefined): number => {
    if (key !== 'inventory') {
      return compare(a, b);
    }
    const inventoryResult = parseInventory(a) - parseInventory(b);
    return inventoryResult || compare(a, b);
  };

  const updateArrows = (): void => {
    headers.forEach((header) => {
      const arrow = header.querySelector<HTMLElement>('.sort-arrow');
      if (!arrow) {
        return;
      }
      arrow.textContent = header.dataset.sortKey === state.key ? (state.dir === 'asc' ? '▲' : '▼') : '';
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

  const sortRows = (key: string): void => {
    if (state.key === key) {
      state.dir = state.dir === 'asc' ? 'desc' : 'asc';
    } else {
      state.key = key;
      state.dir = 'asc';
    }

    const rows = Array.from(tbody.querySelectorAll<HTMLTableRowElement>('tr')).filter(
      (row) => row.dataset.name && !row.hidden,
    );
    rows.sort((rowA, rowB) => {
      const result = compareByKey(key, rowA.dataset[key], rowB.dataset[key]);
      return state.dir === 'asc' ? result : -result;
    });
    rows.forEach((row) => tbody.appendChild(row));
    updateArrows();
  };

  headers.forEach((header) => {
    header.addEventListener('click', () => sortRows(header.dataset.sortKey || 'inventory'));
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
  const state: { key: string; dir: SortDirection } = { key: 'name', dir: 'asc' };
  const sortableKeys = new Set(['name', 'role', 'location', 'status']);

  const compare = (a: string | null | undefined, b: string | null | undefined): number =>
    normalize(a).localeCompare(normalize(b), 'bg');

  const updateArrows = (): void => {
    headers.forEach((header) => {
      const arrow = header.querySelector<HTMLElement>('.sort-arrow');
      if (!arrow) {
        return;
      }
      arrow.textContent = header.dataset.sortKey === state.key ? (state.dir === 'asc' ? '▲' : '▼') : '';
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

  const sortRows = (key: string): void => {
    if (!sortableKeys.has(key)) {
      return;
    }
    if (state.key === key) {
      state.dir = state.dir === 'asc' ? 'desc' : 'asc';
    } else {
      state.key = key;
      state.dir = 'asc';
    }

    const rows = Array.from(tbody.querySelectorAll<HTMLTableRowElement>('tr')).filter((row) => row.dataset.name);
    rows.sort((rowA, rowB) => {
      const result = compare(rowA.dataset[key], rowB.dataset[key]);
      return state.dir === 'asc' ? result : -result;
    });
    rows.forEach((row) => tbody.appendChild(row));
    updateArrows();
  };

  headers.forEach((header) => {
    header.addEventListener('click', () => sortRows(header.dataset.sortKey || 'name'));
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
  const state: { key: string; dir: SortDirection } = { key: 'created_at', dir: 'desc' };

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

  const updateArrows = (): void => {
    headers.forEach((header) => {
      const arrow = header.querySelector<HTMLElement>('.sort-arrow');
      if (!arrow) {
        return;
      }
      arrow.textContent = header.dataset.sortKey === state.key ? (state.dir === 'asc' ? '▲' : '▼') : '';
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

  const sortRows = (key: string): void => {
    if (state.key === key) {
      state.dir = state.dir === 'asc' ? 'desc' : 'asc';
    } else {
      state.key = key;
      state.dir = key === 'created_at' ? 'desc' : 'asc';
    }

    const rows = Array.from(tbody.querySelectorAll<HTMLTableRowElement>('tr')).filter((row) => row.dataset.id);
    rows.sort((rowA, rowB) => {
      const result = compareValues(rowA, rowB, key);
      return state.dir === 'asc' ? result : -result;
    });
    rows.forEach((row) => tbody.appendChild(row));
    updateArrows();
    applySearchFilter();
  };

  headers.forEach((header) => {
    header.addEventListener('click', () => sortRows(header.dataset.sortKey || 'created_at'));
  });

  search?.addEventListener('input', applySearchFilter);
  applySearchFilter();
  updateArrows();
}

export function initTableEnhancements(): void {
  initAssetsTable();
  initUsersTable();
  initRequestsTable();
}
