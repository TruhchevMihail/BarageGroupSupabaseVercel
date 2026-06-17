import './styles/main.css';

import { initAssetImageUpload } from './modules/assetImageUpload';
import { initAutoSubmit } from './modules/autoSubmit';
import { getCsrfToken, injectCsrfInputs } from './modules/csrf';
import { initCopyButtons } from './modules/copy';
import { initListSearch } from './modules/listSearch';
import { initRowMenu } from './modules/rowMenu';
import { initTeamSearch } from './modules/teamSearch';
import { initThemeToggle } from './modules/theme';
import { initTableEnhancements } from './modules/tableEnhancements';
import { initSearchForms } from './modules/searchForms';

document.addEventListener('DOMContentLoaded', () => {
  const csrfToken = getCsrfToken();

  initThemeToggle();
  injectCsrfInputs(csrfToken);
  initCopyButtons();
  initAutoSubmit();
  initListSearch();
  initTeamSearch();
  initAssetImageUpload(csrfToken);
  initRowMenu();
  initTableEnhancements();
  initSearchForms();
});
