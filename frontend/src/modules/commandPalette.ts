import { isEditableTarget } from './domGuards';

type Command = {
  label: string;
  url: string;
  keywords: string;
};

type PaletteState = {
  root: HTMLElement;
  panel: HTMLElement;
  input: HTMLInputElement;
  list: HTMLElement;
  commands: Command[];
  selectedIndex: number;
  previousFocus: HTMLElement | null;
};

let state: PaletteState | null = null;

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function visibleCommands(): Command[] {
  if (!state) {
    return [];
  }
  const query = normalize(state.input.value);
  if (!query) {
    return state.commands;
  }
  return state.commands.filter((command) => normalize(`${command.label} ${command.keywords}`).includes(query));
}

function render(): void {
  if (!state) {
    return;
  }

  const commands = visibleCommands();
  state.selectedIndex = Math.min(state.selectedIndex, Math.max(commands.length - 1, 0));
  state.list.replaceChildren();

  if (!commands.length) {
    const empty = document.createElement('div');
    empty.className = 'command-palette-empty';
    empty.textContent = 'Няма намерени команди.';
    state.list.appendChild(empty);
    return;
  }

  commands.forEach((command, index) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'command-palette-item';
    item.setAttribute('role', 'option');
    item.setAttribute('aria-selected', String(index === state?.selectedIndex));
    item.textContent = command.label;
    item.addEventListener('click', () => {
      window.location.href = command.url;
    });
    state?.list.appendChild(item);
  });
}

export function closeCommandPalette(): void {
  if (!state || state.root.hidden) {
    return;
  }
  state.root.hidden = true;
  state.input.value = '';
  state.selectedIndex = 0;
  state.previousFocus?.focus?.();
  state.previousFocus = null;
}

export function openCommandPalette(): void {
  if (!state) {
    return;
  }
  state.previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  state.root.hidden = false;
  render();
  window.requestAnimationFrame(() => state?.input.focus());
}

function navigateSelected(): void {
  const commands = visibleCommands();
  const command = commands[state?.selectedIndex || 0];
  if (command) {
    window.location.href = command.url;
  }
}

export function initCommandPalette(): void {
  const root = document.querySelector<HTMLElement>('[data-command-palette]');
  if (!root) {
    return;
  }

  const panel = root.querySelector<HTMLElement>('[data-command-palette-panel]');
  const input = root.querySelector<HTMLInputElement>('[data-command-palette-input]');
  const list = root.querySelector<HTMLElement>('[data-command-palette-list]');
  const commandNodes = Array.from(root.querySelectorAll<HTMLElement>('[data-command]'));

  if (!panel || !input || !list || !commandNodes.length) {
    return;
  }

  state = {
    root,
    panel,
    input,
    list,
    commands: commandNodes
      .map((node) => ({
        label: node.dataset.label || '',
        url: node.dataset.url || '',
        keywords: node.dataset.keywords || '',
      }))
      .filter((command) => command.label && command.url),
    selectedIndex: 0,
    previousFocus: null,
  };

  commandNodes.forEach((node) => node.remove());
  root.hidden = true;

  input.addEventListener('input', () => {
    if (!state) {
      return;
    }
    state.selectedIndex = 0;
    render();
  });

  input.addEventListener('keydown', (event) => {
    if (!state) {
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      state.selectedIndex = Math.min(state.selectedIndex + 1, visibleCommands().length - 1);
      render();
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      state.selectedIndex = Math.max(state.selectedIndex - 1, 0);
      render();
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      navigateSelected();
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      closeCommandPalette();
    }
  });

  root.addEventListener('click', (event) => {
    if (event.target === root) {
      closeCommandPalette();
    }
  });

  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      if (!state?.root.hidden) {
        closeCommandPalette();
        return;
      }
      openCommandPalette();
      return;
    }

    if (event.key === 'Escape' && !state?.root.hidden && !isEditableTarget(event.target)) {
      closeCommandPalette();
    }
  });
}
