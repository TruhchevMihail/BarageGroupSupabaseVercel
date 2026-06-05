document.addEventListener('DOMContentLoaded', () => {
  const root = document.documentElement;
  const themeToggles = Array.from(document.querySelectorAll('[data-theme-toggle]'));
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

  const getThemeLabel = (theme) => (theme === 'dark' ? '☀' : '☾');
  const getThemeAriaLabel = (theme) => (theme === 'dark' ? 'Светла тема' : 'Черна тема');

  const setTheme = (theme) => {
    const next = theme === 'dark' ? 'dark' : 'light';
    root.dataset.theme = next;
    root.style.colorScheme = next;
    localStorage.setItem('theme', next);
    themeToggles.forEach((button) => {
      button.textContent = getThemeLabel(next);
      button.setAttribute('aria-label', `${getThemeAriaLabel(next)} - смени`);
    });
  };

  if (themeToggles.length) {
    setTheme(root.dataset.theme || 'light');
    themeToggles.forEach((button) => button.addEventListener('click', () => {
      setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark');
    }));
  }

  if (csrfToken) {
    document.querySelectorAll('form[method="post"]').forEach((form) => {
      if (form.querySelector('input[name="csrf_token"]')) return;
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'csrf_token';
      input.value = csrfToken;
      form.prepend(input);
    });
  }

  document.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', async () => {
      const text = button.getAttribute('data-copy') || '';
      if (!text) return;
      try {
        await navigator.clipboard.writeText(text);
        const original = button.textContent;
        button.textContent = 'Копирано';
        window.setTimeout(() => {
          button.textContent = original;
        }, 1200);
      } catch (error) {
        console.error('Copy failed', error);
      }
    });
  });

  document.querySelectorAll('form[data-auto-submit]').forEach((form) => {
    let timer = null;
    const submitSoon = () => {
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(() => form.requestSubmit(), 250);
    };

    form.querySelectorAll('select').forEach((select) => {
      select.addEventListener('change', submitSoon);
    });

    form.querySelectorAll('input[type="text"], input[type="search"]').forEach((input) => {
      input.addEventListener('input', submitSoon);
    });
  });

  document.querySelectorAll('form[data-list-search-form]').forEach((form) => {
    const searchInput = form.querySelector('[data-list-search]');
    const scope = form.closest('main') || document;
    const items = Array.from(scope.querySelectorAll('[data-list-search-item]'));
    if (!searchInput || !items.length) return;

    const normalize = (value) => (value || '').toString().trim().toLowerCase();

    const applyFilter = () => {
      const query = normalize(searchInput.value);
      items.forEach((item) => {
        const haystack = normalize(item.getAttribute('data-search-text') || item.textContent || '');
        item.style.display = !query || haystack.includes(query) ? '' : 'none';
      });
    };

    searchInput.addEventListener('input', applyFilter);
    applyFilter();
  });

  document.querySelectorAll('[data-team-search]').forEach((searchInput) => {
    const scope = searchInput.closest('form') || document;
    const options = Array.from(scope.querySelectorAll('[data-team-option]'));
    const counter = scope.querySelector('[data-team-count]');
    const normalize = (value) => value.toLowerCase().trim();

    searchInput.addEventListener('input', () => {
      const query = normalize(searchInput.value);
      let visible = 0;
      options.forEach((option) => {
        const text = normalize(option.textContent || '');
        const show = !query || text.includes(query);
        option.style.display = show ? '' : 'none';
        if (show) visible += 1;
      });
      if (counter) {
        counter.textContent = `Показани ${visible} от ${options.length}`;
      }
    });

    if (counter) {
      counter.textContent = `Показани ${options.length} от ${options.length}`;
    }
  });

  document.querySelectorAll('[data-asset-image-form]').forEach((form) => {
    if (form.dataset.boundAssetImageForm === '1') return;
    form.dataset.boundAssetImageForm = '1';

    form.addEventListener('submit', async (event) => {
      const fileInput = form.querySelector('input[name="image_file"]');
      const urlInput = form.querySelector('input[name="image_url"]');
      if (!fileInput || !fileInput.files || !fileInput.files.length) return;
      if (form.dataset.uploading === '1') return;

      event.preventDefault();
      form.dataset.uploading = '1';
      try {
        const payload = new FormData();
        payload.append('image_file', fileInput.files[0]);
        const response = await fetch('/uploads/asset-image', {
          method: 'POST',
          body: payload,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken,
          },
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
          throw new Error(data.error || 'Качването на снимката не успя.');
        }
        if (urlInput) {
          urlInput.value = data.image_url;
        }
        fileInput.value = '';
        form.submit();
      } catch (error) {
        console.error(error);
        alert(error.message || 'Качването на снимката не успя.');
      } finally {
        form.dataset.uploading = '0';
      }
    });
  });
});
