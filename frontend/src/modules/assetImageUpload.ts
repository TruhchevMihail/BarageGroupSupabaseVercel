import { showToast } from './toast';

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function initAssetUploadForms(csrfToken: string): void {
  document.querySelectorAll<HTMLFormElement>('[data-asset-image-form]').forEach((form) => {
    if (form.dataset.boundAssetImageForm === '1') {
      return;
    }
    form.dataset.boundAssetImageForm = '1';

    form.addEventListener('submit', async (event) => {
      const fileInput = form.querySelector<HTMLInputElement>('input[name="image_file"]');
      const urlInput = form.querySelector<HTMLInputElement>('input[name="image_url"]');
      const file = fileInput?.files?.[0];

      if (!file || form.dataset.uploading === '1') {
        return;
      }

      event.preventDefault();
      form.dataset.uploading = '1';

      try {
        const payload = new FormData();
        payload.append('image_file', file);

        const response = await fetch('/uploads/asset-image', {
          method: 'POST',
          body: payload,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken,
          },
        });
        const data = (await response.json()) as { ok?: boolean; image_url?: string; error?: string };

        if (!response.ok || !data.ok) {
          throw new Error(data.error || 'Качването на снимката не успя.');
        }

        if (urlInput && data.image_url) {
          urlInput.value = data.image_url;
        }

        fileInput.value = '';
        form.submit();
      } catch (error) {
        console.error(error);
        const message = error instanceof Error ? error.message : 'Качването на снимката не успя.';
        window.alert(message);
      } finally {
        form.dataset.uploading = '0';
      }
    });
  });
}

function initAssetPreviewInputs(): void {
  document.querySelectorAll<HTMLInputElement>('[data-asset-images]').forEach((input) => {
    if (input.dataset.assetImagesBound === 'true') {
      return;
    }
    input.dataset.assetImagesBound = 'true';

    const preview = input.parentElement?.querySelector<HTMLElement>('[data-image-preview]');
    if (!preview) {
      return;
    }

    input.addEventListener('change', () => {
      preview.querySelectorAll<HTMLElement>('.asset-image-thumb--new').forEach((node) => node.remove());
      let previewCount = 0;

      Array.from(input.files || [])
        .slice(0, 3)
        .forEach((file) => {
          if (!file.type.startsWith('image/')) {
            return;
          }

          const url = URL.createObjectURL(file);
          const figure = document.createElement('figure');
          figure.className = 'asset-image-thumb asset-image-thumb--new';

          const label = document.createElement('div');
          label.className = 'asset-image-preview-label';
          label.textContent = 'Преглед на снимката';

          const image = document.createElement('img');
          image.src = url;
          image.alt = file.name;
          image.className = 'asset-image-thumb-img';
          image.addEventListener(
            'load',
            () => {
              URL.revokeObjectURL(url);
            },
            { once: true },
          );

          const caption = document.createElement('figcaption');
          caption.className = 'asset-image-thumb-caption';
          caption.textContent = `Избрана снимка: ${file.name} · ${formatFileSize(file.size)}`;

          figure.append(label, image, caption);
          preview.appendChild(figure);
          previewCount += 1;
        });

      if (previewCount > 0) {
        showToast('Снимката е избрана');
      }
    });
  });
}

export function initAssetImageUpload(csrfToken: string): void {
  initAssetUploadForms(csrfToken);
  initAssetPreviewInputs();
}
