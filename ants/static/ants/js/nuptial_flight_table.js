/**
 * Nuptial Flight Table – JS companion for HTMX-driven page.
 */

function getFilterParams() {
    const form = document.getElementById('filter-form');
    return new URLSearchParams(new FormData(form)).toString();
}

// Sync address bar with current filter form state
function syncUrl() {
    const form = document.getElementById('filter-form');
    if (!form) return;
    const params = new URLSearchParams(new FormData(form));
    if (!params.get('name')) params.delete('name');
    if (params.get('month') === 'all') params.delete('month');
    if (params.get('country') === 'all') params.delete('country');
    if (params.get('state') === 'all') params.delete('state');
    const search = params.toString();
    history.replaceState(null, '', window.location.pathname + (search ? '?' + search : ''));
}

// Prevent Enter from submitting the filter form
document.getElementById('name-filter')?.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') e.preventDefault();
});

// Prevent country change from bubbling before states load
document.getElementById('country-select')?.addEventListener('change', function (event) {
    event.stopPropagation();
});

// Update page heading with active country/state filter labels
function updateTitleLocation() {
    const countrySelect = document.getElementById('country-select');
    const stateSelect = document.querySelector('#state-wrapper select');
    const parts = [];
    if (countrySelect && countrySelect.value !== 'all') {
        parts.push(countrySelect.options[countrySelect.selectedIndex].text);
    }
    if (stateSelect && stateSelect.value !== 'all') {
        parts.push(stateSelect.options[stateSelect.selectedIndex].text);
    }
    const locationEl = document.getElementById('nuptial-title-location');
    if (locationEl) {
        locationEl.textContent = parts.length ? ' (' + parts.join(', ') + ')' : '';
    }
}

// Quick filter button: toggle current month
const quickCurrentBtn = document.getElementById('quick-current-month-btn');
if (quickCurrentBtn) {
    quickCurrentBtn.addEventListener('click', function () {
        const monthSelect = document.getElementById('month-select');
        if (!monthSelect) return;
        if (monthSelect.value === 'current') {
            monthSelect.value = 'all';
            quickCurrentBtn.classList.remove('active');
        } else {
            monthSelect.value = 'current';
            quickCurrentBtn.classList.add('active');
        }
        htmx.trigger(document.getElementById('filter-form'), 'change');
    });
}

// Sync quick button when month-select changes
document.getElementById('month-select')?.addEventListener('change', function () {
    if (quickCurrentBtn) {
        if (this.value === 'current') {
            quickCurrentBtn.classList.add('active');
        } else {
            quickCurrentBtn.classList.remove('active');
        }
    }
});

// Sync URL and title whenever table content settles
document.getElementById('table-container')?.addEventListener('htmx:afterSettle', function () {
    syncUrl();
    updateTitleLocation();
});

// Export buttons
document.getElementById('export-csv-btn')?.addEventListener('click', function () {
    window.location.href = '/ants/nuptial-flight-table/export/csv/?' + getFilterParams();
});

document.getElementById('export-json-btn')?.addEventListener('click', function () {
    window.location.href = '/ants/nuptial-flight-table/export/json/?' + getFilterParams();
});

// Print button
document.getElementById('print-btn')?.addEventListener('click', function () {
    htmx.ajax('GET', '/ants/nuptial-flight-table/rows/?print=1&' + getFilterParams(), {
        target: '#print-area',
        swap: 'innerHTML',
    }).then(function () {
        window.print();
    });
});

// Reset button
document.getElementById('reset-btn')?.addEventListener('click', function () {
    const nameInput = document.getElementById('name-filter');
    const monthSelect = document.getElementById('month-select');
    const countrySelect = document.getElementById('country-select');
    const stateWrapper = document.getElementById('state-wrapper');
    if (nameInput) nameInput.value = '';
    if (monthSelect) monthSelect.value = 'all';
    if (countrySelect) countrySelect.value = 'all';
    if (stateWrapper) stateWrapper.innerHTML = '';
    if (quickCurrentBtn) quickCurrentBtn.classList.remove('active');
    htmx.trigger(document.getElementById('filter-form'), 'change');
});

// After printing, clear print area
window.addEventListener('afterprint', function () {
    const printArea = document.getElementById('print-area');
    if (printArea) printArea.innerHTML = '';
});
