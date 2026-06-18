import './styles/main.css';

import { initAssetImageUpload } from './modules/assetImageUpload';
import { initAjaxListNavigation } from './modules/ajaxListNavigation';
import { initAutoSubmit } from './modules/autoSubmit';
import { initCollapsibles } from './modules/collapsible';
import { initCommandPalette } from './modules/commandPalette';
import { initConfirmActions } from './modules/confirmActions';
import { getCsrfToken, injectCsrfInputs } from './modules/csrf';
import { initCopyButtons } from './modules/copy';
import { initKeyboardShortcuts } from './modules/keyboardShortcuts';
import { initListSearch } from './modules/listSearch';
import { initRowMenu } from './modules/rowMenu';
import { initTeamSearch } from './modules/teamSearch';
import { initThemeToggle } from './modules/theme';
import { initTableEnhancements } from './modules/tableEnhancements';
import { initSearchForms } from './modules/searchForms';

function initDynamicUi(csrfToken: string): void {
  injectCsrfInputs(csrfToken);
  initConfirmActions();
  initCopyButtons();
  initAutoSubmit();
  initListSearch();
  initTeamSearch();
  initAssetImageUpload(csrfToken);
  initRowMenu();
  initTableEnhancements();
  initSearchForms();
  initCollapsibles();
}

document.addEventListener('DOMContentLoaded', () => {
  const csrfToken = getCsrfToken();

  initThemeToggle();
  initCommandPalette();
  initKeyboardShortcuts();
  initDynamicUi(csrfToken);
  initAjaxListNavigation(() => initDynamicUi(csrfToken));
});
