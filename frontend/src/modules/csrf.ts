export function getCsrfToken(): string {
  const csrfMeta = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]');
  return csrfMeta?.content || '';
}

export function injectCsrfInputs(csrfToken: string): void {
  if (!csrfToken) {
    return;
  }

  document.querySelectorAll<HTMLFormElement>('form[method="post"]').forEach((form) => {
    if (form.querySelector('input[name="csrf_token"]')) {
      return;
    }

    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'csrf_token';
    input.value = csrfToken;
    form.prepend(input);
  });
}
