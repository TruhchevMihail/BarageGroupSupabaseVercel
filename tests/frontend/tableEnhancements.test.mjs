import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildFilteredExportUrl,
  initAssetsTable,
} from '../../frontend/src/modules/tableEnhancements.ts';

function createAssetsTableFixture() {
  const searchInput = new EventTarget();
  const locationSelect = new EventTarget();
  let submitCount = 0;

  const form = {
    querySelector(selector) {
      if (selector === '[data-list-search]') return searchInput;
      if (selector === 'select[name="location"]') return locationSelect;
      return null;
    },
    requestSubmit() {
      submitCount += 1;
    },
  };

  const table = {
    dataset: {},
    querySelectorAll() {
      return [];
    },
  };

  globalThis.window = {
    location: { search: '' },
    setTimeout,
    clearTimeout,
  };
  globalThis.document = {
    getElementById(id) {
      return id === 'assets-table' ? table : null;
    },
    querySelector(selector) {
      return selector === '[data-assets-filter-form]' ? form : null;
    },
  };

  return { searchInput, locationSelect, submitCount: () => submitCount };
}

test('asset search waits for submit while location changes apply immediately', async () => {
  const fixture = createAssetsTableFixture();

  initAssetsTable();
  fixture.searchInput.dispatchEvent(new Event('input'));
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal(fixture.submitCount(), 0);

  fixture.locationSelect.dispatchEvent(new Event('change'));
  assert.equal(fixture.submitCount(), 1);
});

test('filtered export URL uses the filters visible in the current list', () => {
  globalThis.window = { location: { href: 'https://example.test/assets' } };
  const result = buildFilteredExportUrl(
    'https://example.test/assets/export.xlsx?status=%D0%A1%D1%82%D0%B0%D1%80',
    '?q=bosch&location=13&status=%D0%9D%D0%B0+%D0%BE%D0%B5%D0%BA%D1%82&sort=brand&direction=asc&page=3',
  );

  assert.equal(
    result,
    'https://example.test/assets/export.xlsx?q=bosch&location=13&status=%D0%9D%D0%B0+%D0%BE%D0%B5%D0%BA%D1%82&sort=brand&direction=asc',
  );
});
