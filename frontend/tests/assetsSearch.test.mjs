import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

import { Window } from 'happy-dom';


function renderAssetsPage(query = '', location = '') {
  const escapedQuery = query.replaceAll('&', '&amp;').replaceAll('"', '&quot;');
  const selected = location === '1' ? ' selected' : '';
  return `<!doctype html>
    <html><body>
      <div data-ajax-page="assets">
        <div data-ajax-container="assets" data-rendered-query="${escapedQuery}">
          <form method="get" action="/assets" data-assets-filter-form data-ajax-form>
            <input name="q" value="${escapedQuery}" data-main-search>
            <button type="submit">Търси</button>
            <select name="location"><option value="">Всички</option><option value="1"${selected}>Обект</option></select>
            <input type="hidden" name="sort" value="inventory">
            <input type="hidden" name="direction" value="asc">
          </form>
          <table id="assets-table"><thead><tr><th><a class="table-sort" data-sort-key="inventory"><span class="sort-arrow"></span></a></th></tr></thead></table>
          <a id="sort-link" data-ajax-link href="/assets?q=${encodeURIComponent(query)}&location=${location}&sort=model&direction=desc&page=1">Сортиране</a>
          <a id="page-link" data-ajax-link href="/assets?q=${encodeURIComponent(query)}&location=${location}&sort=inventory&direction=asc&page=2">2</a>
        </div>
      </div>
    </body></html>`;
}

async function waitForRequests(requests, count) {
  for (let attempt = 0; attempt < 30 && requests.length < count; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
  assert.equal(requests.length, count);
}

async function waitForUrl(searchValue, expectedValue) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    if (new URL(window.location.href).searchParams.get(searchValue) === expectedValue) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
  assert.equal(new URL(window.location.href).searchParams.get(searchValue), expectedValue);
}

test('assets search submits only explicitly and AJAX navigation remains single-shot', async () => {
  const browserWindow = new Window({ url: 'http://127.0.0.1:5091/assets' });
  const { document } = browserWindow;
  document.write(renderAssetsPage());

  Object.assign(globalThis, {
    window: browserWindow,
    document,
    CSS: browserWindow.CSS,
    DOMParser: browserWindow.DOMParser,
    FormData: browserWindow.FormData,
  });

  const requests = [];
  globalThis.fetch = async (input) => {
    const url = new URL(String(input));
    requests.push(url);
    return {
      ok: true,
      text: async () => renderAssetsPage(url.searchParams.get('q') || '', url.searchParams.get('location') || ''),
    };
  };

  const { initTableEnhancements } = await import('../src/modules/tableEnhancements.ts');
  const { initAjaxListNavigation } = await import('../src/modules/ajaxListNavigation.ts');
  const reinitialize = () => initTableEnhancements();
  initTableEnhancements();
  initAjaxListNavigation(reinitialize);

  const searchInput = document.querySelector('input[name="q"]');
  searchInput.value = 'Тестова машина';
  searchInput.dispatchEvent(new browserWindow.Event('input', { bubbles: true }));
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal(requests.length, 0, 'typing must not send a request');

  searchInput.form.requestSubmit();
  await waitForRequests(requests, 1);
  await waitForUrl('q', 'Тестова машина');
  assert.equal(requests[0].searchParams.get('q'), 'Тестова машина');
  assert.equal(document.querySelector('input[name="q"]').value, 'Тестова машина');

  const updatedInput = document.querySelector('input[name="q"]');
  updatedInput.value = 'Багер';
  document.querySelector('button[type="submit"]').click();
  await waitForRequests(requests, 2);
  await waitForUrl('q', 'Багер');
  assert.equal(requests[1].searchParams.get('q'), 'Багер');
  assert.equal(document.querySelector('input[name="q"]').value, 'Багер');

  const locationSelect = document.querySelector('select[name="location"]');
  locationSelect.value = '1';
  locationSelect.dispatchEvent(new browserWindow.Event('change', { bubbles: true }));
  await waitForRequests(requests, 3);
  await waitForUrl('location', '1');
  assert.equal(requests[2].searchParams.get('location'), '1');

  document.querySelector('#sort-link').click();
  await waitForRequests(requests, 4);
  await waitForUrl('sort', 'model');
  assert.equal(requests[3].searchParams.get('sort'), 'model');
  assert.equal(requests[3].searchParams.get('direction'), 'desc');

  document.querySelector('#page-link').click();
  await waitForRequests(requests, 5);
  await waitForUrl('page', '2');
  assert.equal(requests[4].searchParams.get('page'), '2');

  await browserWindow.close();
});

test('role chips keep their normal colors inside list cards in light and dark themes', async () => {
  const browserWindow = new Window();
  const styles = await Promise.all(
    ['tokens.css', 'layout.css', 'cards.css'].map((file) =>
      readFile(new URL(`../src/styles/${file}`, import.meta.url), 'utf8'),
    ),
  );
  browserWindow.document.head.innerHTML = `<style>${styles.join('\n')}</style>`;
  browserWindow.document.body.innerHTML = `
    <div class="list-card">
      <span class="chip chip-role-tech" data-inside="tech">Технически ръководител</span>
      <span class="chip chip-role-warehouse" data-inside="warehouse">Складов работник</span>
      <span class="chip chip-role-lead" data-inside="lead">Проектов ръководител</span>
      <span class="chip chip-role-admin" data-inside="admin">Администратор</span>
    </div>
    <span class="chip chip-role-tech" data-outside="tech"></span>
    <span class="chip chip-role-warehouse" data-outside="warehouse"></span>
    <span class="chip chip-role-lead" data-outside="lead"></span>
    <span class="chip chip-role-admin" data-outside="admin"></span>`;

  for (const theme of ['light', 'dark']) {
    browserWindow.document.documentElement.dataset.theme = theme;
    for (const role of ['tech', 'warehouse', 'lead', 'admin']) {
      const inside = browserWindow.document.querySelector(`[data-inside="${role}"]`);
      const outside = browserWindow.document.querySelector(`[data-outside="${role}"]`);
      assert.equal(
        browserWindow.getComputedStyle(inside).color,
        browserWindow.getComputedStyle(outside).color,
        `${role} chip color must survive the list-card cascade in ${theme} theme`,
      );
    }
  }

  await browserWindow.close();
});
