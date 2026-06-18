type ReinitializeCallback = () => void;

interface AjaxPageElements {
  page: HTMLElement;
  pageId: string;
  container: HTMLElement;
  containerId: string;
}

let abortController: AbortController | null = null;
let reinitialize: ReinitializeCallback = () => undefined;

function getCurrentPage(): AjaxPageElements | null {
  const page = document.querySelector<HTMLElement>('[data-ajax-page]');
  const container = page?.querySelector<HTMLElement>('[data-ajax-container]');
  const pageId = page?.dataset.ajaxPage || '';
  const containerId = container?.dataset.ajaxContainer || pageId;

  if (!page || !container || !pageId || !containerId) {
    return null;
  }

  return { page, pageId, container, containerId };
}

function findIncomingContainer(doc: Document, pageId: string, containerId: string): HTMLElement | null {
  return doc.querySelector<HTMLElement>(
    `[data-ajax-page="${CSS.escape(pageId)}"] [data-ajax-container="${CSS.escape(containerId)}"]`,
  );
}

function isSameOriginUrl(url: URL): boolean {
  return url.origin === window.location.origin;
}

function isModifiedClick(event: MouseEvent): boolean {
  return event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0;
}

function showLoading(container: HTMLElement): void {
  container.setAttribute('aria-busy', 'true');
  container.classList.add('ajax-list-loading');

  if (container.querySelector('[data-ajax-loading]')) {
    return;
  }

  const loading = document.createElement('div');
  loading.className = 'ajax-loading-indicator';
  loading.dataset.ajaxLoading = 'true';
  loading.setAttribute('role', 'status');
  loading.setAttribute('aria-live', 'polite');
  loading.textContent = 'Зареждане...';
  container.appendChild(loading);
}

function hideLoading(container: HTMLElement): void {
  container.classList.remove('ajax-list-loading');
  container.removeAttribute('aria-busy');
  container.querySelector('[data-ajax-loading]')?.remove();
}

function focusUpdatedContainer(container: HTMLElement, previousActiveElement: Element | null): void {
  if (!previousActiveElement || !container.contains(previousActiveElement)) {
    return;
  }

  if (!container.hasAttribute('tabindex')) {
    container.setAttribute('tabindex', '-1');
    container.dataset.ajaxTemporaryTabindex = 'true';
  }
  container.focus({ preventScroll: true });
  if (container.dataset.ajaxTemporaryTabindex === 'true') {
    container.removeAttribute('tabindex');
    delete container.dataset.ajaxTemporaryTabindex;
  }
}

async function fetchAndReplace(url: URL, pushHistory: boolean): Promise<boolean> {
  const current = getCurrentPage();
  if (!current || !isSameOriginUrl(url)) {
    return false;
  }

  abortController?.abort();
  abortController = new AbortController();

  const previousActiveElement = document.activeElement;
  showLoading(current.container);

  try {
    const response = await fetch(url.toString(), {
      credentials: 'same-origin',
      headers: {
        Accept: 'text/html',
        'X-Requested-With': 'fetch',
      },
      signal: abortController.signal,
    });

    if (!response.ok) {
      return false;
    }

    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const incomingContainer = findIncomingContainer(doc, current.pageId, current.containerId);

    if (!incomingContainer) {
      return false;
    }

    current.container.replaceWith(incomingContainer);

    if (pushHistory) {
      window.history.pushState(
        { ajaxListNavigation: true, pageId: current.pageId, containerId: current.containerId },
        '',
        url.toString(),
      );
    }

    focusUpdatedContainer(incomingContainer, previousActiveElement);
    reinitialize();
    return true;
  } catch (error) {
    if ((error as DOMException).name === 'AbortError') {
      return true;
    }
    console.error('AJAX list navigation failed', error);
    return false;
  } finally {
    const latest = getCurrentPage();
    if (latest) {
      hideLoading(latest.container);
    }
  }
}

function buildFormUrl(form: HTMLFormElement): URL | null {
  const method = (form.getAttribute('method') || 'get').toLowerCase();
  if (method !== 'get') {
    return null;
  }

  const url = new URL(form.action || window.location.href, window.location.href);
  url.search = '';
  const params = new URLSearchParams();
  new FormData(form).forEach((value, key) => {
    if (typeof value === 'string') {
      params.append(key, value);
    }
  });
  params.delete('page');
  url.search = params.toString();
  return url;
}

async function handleNavigation(url: URL, fallback: () => void): Promise<void> {
  const ok = await fetchAndReplace(url, true);
  if (!ok) {
    fallback();
  }
}

export function initAjaxListNavigation(callback?: ReinitializeCallback): void {
  if (callback) {
    reinitialize = callback;
  }

  const current = getCurrentPage();
  if (current && !window.history.state?.ajaxListNavigation) {
    window.history.replaceState(
      { ajaxListNavigation: true, pageId: current.pageId, containerId: current.containerId },
      '',
      window.location.href,
    );
  }

  if (document.body.dataset.ajaxListNavigationInitialized === 'true') {
    return;
  }
  document.body.dataset.ajaxListNavigationInitialized = 'true';

  document.addEventListener('click', (event) => {
    if (isModifiedClick(event)) {
      return;
    }

    const target = event.target as Element | null;
    const link = target?.closest<HTMLAnchorElement>('a[data-ajax-link]');
    if (!link || link.target || link.hasAttribute('download')) {
      return;
    }

    const currentPage = getCurrentPage();
    if (!currentPage || !currentPage.container.contains(link)) {
      return;
    }

    const url = new URL(link.href, window.location.href);
    if (!isSameOriginUrl(url)) {
      return;
    }

    event.preventDefault();
    void handleNavigation(url, () => window.location.assign(url.toString()));
  });

  document.addEventListener('submit', (event) => {
    const form = (event.target as Element | null)?.closest<HTMLFormElement>('form[data-ajax-form]');
    const currentPage = getCurrentPage();
    if (!form || !currentPage || !currentPage.container.contains(form)) {
      return;
    }

    const url = buildFormUrl(form);
    if (!url || !isSameOriginUrl(url)) {
      return;
    }

    event.preventDefault();
    void handleNavigation(url, () => window.location.assign(url.toString()));
  });

  window.addEventListener('popstate', () => {
    const currentPage = getCurrentPage();
    if (!currentPage) {
      return;
    }

    const url = new URL(window.location.href);
    void fetchAndReplace(url, false).then((ok) => {
      if (!ok) {
        window.location.reload();
      }
    });
  });
}
