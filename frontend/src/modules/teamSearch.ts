function normalize(value: string | null | undefined): string {
  return (value || '').toString().trim().toLowerCase();
}

function initGenericTeamSearch(): void {
  document.querySelectorAll<HTMLInputElement>('[data-team-search]').forEach((searchInput) => {
    const scope = searchInput.closest('form') || document;
    const options = Array.from(scope.querySelectorAll<HTMLElement>('[data-team-option]'));
    const counter = scope.querySelector<HTMLElement>('[data-team-count]');

    const sync = (): void => {
      const query = normalize(searchInput.value);
      let visible = 0;

      options.forEach((option) => {
        const text = normalize(option.textContent);
        const show = !query || text.includes(query);
        option.style.display = show ? '' : 'none';
        if (show) {
          visible += 1;
        }
      });

      if (counter) {
        counter.textContent = `Показани ${visible} от ${options.length}`;
      }
    };

    searchInput.addEventListener('input', sync);
    sync();
  });
}

function initLocationFormControls(): void {
  const form = document.querySelector<HTMLElement>('[data-location-form]');
  const typeSelect = document.querySelector<HTMLSelectElement>('[data-location-type]');
  const teamSection = document.querySelector<HTMLElement>('[data-location-team-section]');
  const hiddenFields = document.querySelector<HTMLElement>('[data-location-hidden-fields]');

  if (!form || !typeSelect || !teamSection || !hiddenFields) {
    return;
  }

  const updateVisibility = (): void => {
    const minimal = typeSelect.value === 'service' || typeSelect.value === 'scrap';
    const noLead = typeSelect.value === 'warehouse';
    const cityField = form.querySelector<HTMLElement>('[data-location-field="city"]');
    const leadField = form.querySelector<HTMLElement>('[data-location-field="technical_lead_id"]');

    teamSection.hidden = minimal;
    hiddenFields.hidden = !minimal;
    if (cityField) {
      cityField.hidden = minimal;
    }
    if (leadField) {
      leadField.hidden = noLead || minimal;
    }

    if (noLead) {
      const leadSelect = leadField?.querySelector<HTMLSelectElement>('select[name="technical_lead_id"]');
      if (leadSelect) {
        leadSelect.value = '';
      }
    }

    form.querySelectorAll<HTMLElement>('[data-team-member-select], [data-add-team-member], [data-team-member-list], [data-team-member-inputs]').forEach((node) => {
      node.hidden = minimal;
    });
  };

  typeSelect.addEventListener('change', updateVisibility);
  updateVisibility();

  const memberSelect = document.querySelector<HTMLSelectElement>('[data-team-member-select]');
  const memberList = document.querySelector<HTMLElement>('[data-team-member-list]');
  const memberInputs = document.querySelector<HTMLElement>('[data-team-member-inputs]');
  const addButton = document.querySelector<HTMLButtonElement>('[data-add-team-member]');

  if (!memberSelect || !memberList || !memberInputs || !addButton) {
    return;
  }

  const selected = new Set(
    Array.from(memberList.querySelectorAll<HTMLElement>('[data-team-member-chip]')).map(
      (node) => node.dataset.userId || '',
    ),
  );

  const syncOptions = (): void => {
    Array.from(memberSelect.options).forEach((option) => {
      if (!option.value) {
        return;
      }
      option.hidden = selected.has(option.value);
    });

    if (memberSelect.value && selected.has(memberSelect.value)) {
      memberSelect.value = '';
    }
  };

  const addTeamMember = (userId: string, labelText: string): void => {
    if (!userId || selected.has(userId)) {
      return;
    }

    selected.add(userId);

    const chip = document.createElement('span');
    chip.className = 'mini-chip chip-link';
    chip.dataset.teamMemberChip = '';
    chip.dataset.userId = userId;
    chip.textContent = `${labelText} `;

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'chip-remove';
    removeButton.setAttribute('aria-label', 'Премахни');
    removeButton.dataset.removeTeamMember = userId;
    removeButton.textContent = '×';

    chip.appendChild(removeButton);
    memberList.appendChild(chip);

    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = 'technicians';
    hiddenInput.value = userId;
    hiddenInput.dataset.teamMemberInput = userId;
    memberInputs.appendChild(hiddenInput);

    syncOptions();
  };

  const removeTeamMember = (userId: string): void => {
    selected.delete(userId);
    memberList.querySelector<HTMLElement>(`[data-user-id="${CSS.escape(userId)}"]`)?.remove();
    memberInputs.querySelector<HTMLElement>(`[data-team-member-input="${CSS.escape(userId)}"]`)?.remove();
    syncOptions();
  };

  addButton.addEventListener('click', () => {
    const option = memberSelect.options[memberSelect.selectedIndex];
    if (!option || !option.value) {
      return;
    }

    addTeamMember(option.value, option.textContent.trim());
    memberSelect.value = '';
  });

  memberList.addEventListener('click', (event) => {
    const target = event.target as HTMLElement | null;
    const button = target?.closest<HTMLElement>('[data-remove-team-member]');
    if (!button?.dataset.removeTeamMember) {
      return;
    }
    removeTeamMember(button.dataset.removeTeamMember);
  });

  syncOptions();
}

function initAssignedLocationControls(): void {
  document.querySelectorAll<HTMLElement>('[data-multi-select="assigned-locations"]').forEach((shell) => {
    const section = shell.closest<HTMLElement>('#assigned-locations-section');
    const select = shell.querySelector<HTMLSelectElement>('#assigned-location-select');
    const addButton = shell.querySelector<HTMLButtonElement>('#assigned-location-add');
    const chips = shell.querySelector<HTMLElement>('#assigned-location-chips');
    const primaryInput = shell.querySelector<HTMLInputElement>('#primary-assigned-location-id');

    if (!section || !select || !addButton || !chips || !primaryInput) {
      return;
    }

    const selectedIds = (): string[] =>
      Array.from(section.querySelectorAll<HTMLInputElement>('input[name="team_location_ids"]')).map((input) => String(input.value));

    const refreshOptions = (): void => {
      const ids = new Set(selectedIds());
      Array.from(select.options).forEach((option) => {
        if (!option.value) {
          return;
        }
        option.hidden = ids.has(String(option.value));
      });

      if (ids.has(String(select.value))) {
        select.value = '';
      }
    };

    const updatePrimary = (): void => {
      primaryInput.value = selectedIds()[0] || '';
    };

    const addLocation = (id: string, text: string): void => {
      if (!id || selectedIds().includes(String(id))) {
        return;
      }

      const hiddenInput = document.createElement('input');
      hiddenInput.type = 'hidden';
      hiddenInput.name = 'team_location_ids';
      hiddenInput.value = id;
      hiddenInput.dataset.hiddenLocationId = id;
      shell.appendChild(hiddenInput);

      const chip = document.createElement('span');
      chip.className = 'chip user-location-chip';
      chip.dataset.locationId = id;

      const link = document.createElement('a');
      link.className = 'chip-link';
      link.href = `/locations/${id}`;
      link.textContent = text;

      const removeButton = document.createElement('button');
      removeButton.type = 'button';
      removeButton.className = 'chip-remove';
      removeButton.setAttribute('aria-label', 'Премахни обект');
      removeButton.dataset.removeLocation = id;
      removeButton.textContent = '×';

      chip.append(link, removeButton);
      chips.appendChild(chip);

      updatePrimary();
      refreshOptions();
    };

    addButton.addEventListener('click', () => {
      const option = select.options[select.selectedIndex];
      if (!select.value) {
        return;
      }
      addLocation(select.value, option ? option.text : select.value);
      select.value = '';
    });

    chips.addEventListener('click', (event) => {
      const target = event.target as HTMLElement | null;
      const button = target?.closest<HTMLElement>('[data-remove-location]');
      const id = button?.dataset.removeLocation;
      if (!id) {
        return;
      }

      chips.querySelector<HTMLElement>(`[data-location-id="${CSS.escape(id)}"]`)?.remove();
      section.querySelector<HTMLElement>(`input[data-hidden-location-id="${CSS.escape(id)}"]`)?.remove();
      updatePrimary();
      refreshOptions();
    });

    refreshOptions();
    updatePrimary();
  });
}

export function initTeamSearch(): void {
  initGenericTeamSearch();
  initLocationFormControls();
  initAssignedLocationControls();
}
