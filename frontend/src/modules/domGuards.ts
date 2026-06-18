export function isEditableTarget(target: EventTarget | null): boolean {
  const element = target instanceof HTMLElement ? target : null;
  if (!element) {
    return false;
  }

  return Boolean(
    element.closest('input, textarea, select, [contenteditable="true"], [contenteditable=""]'),
  );
}
