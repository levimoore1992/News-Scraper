// frontend/src/main.js
import './styles.css';

// Import libraries
import Alpine from 'alpinejs';
import htmx from 'htmx.org';
import _hyperscript from 'hyperscript.org';

// Initialize Alpine.js
window.Alpine = Alpine;
Alpine.start();

// Make HTMX available globally
window.htmx = htmx;

// Initialize hyperscript
window._hyperscript = _hyperscript;
