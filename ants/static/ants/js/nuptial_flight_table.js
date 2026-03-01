/**
 * Nuptial Flight Table – minimal JS companion for HTMX-driven page.
 *
 * Responsibilities:
 *   - Export buttons: build URL from current filter form and trigger download
 *   - Print button: load all filtered entries into #print-area via HTMX, then window.print()
 *   - Reset button: clear filter form, remove state select, re-trigger table load
 *   - Enter key: prevent form submission on Enter in name filter (would cause full page reload)
 *   - URL sync: keep address bar in sync with active filters via history.replaceState
 *   - Title location: update page heading with active country/state filter names
 */

function getFilterParams() {
    const form = document.getElementById('filter-form');
    return new URLSearchParams(new FormData(form)).toString();
}

// Sync address bar with current filter form state (removes default/empty values)
function syncUrl() {
    const form = document.getElementById('filter-form');
    const params = new URLSearchParams(new FormData(form));
    if (!params.get('name')) params.delete('name');
    if (params.get('month') === 'all') params.delete('month');
    if (params.get('country') === 'all') params.delete('country');
    if (params.get('state') === 'all') params.delete('state');
    const search = params.toString();
    history.replaceState(null, '', window.location.pathname + (search ? '?' + search : ''));
}

// Prevent Enter from submitting the filter form (which would cause a full page reload)
document.getElementById('name-filter').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') e.preventDefault();
});

// Prevent the country change event from bubbling to the filter form.
// Without this, the form would fire a rows request with stale state data before
// the states endpoint clears state-wrapper and sends HX-Trigger: refreshTable.
// HTMX's own listener (for the states endpoint) runs first since htmx.min.js
// loads before this script, so the states request still fires correctly.
document.getElementById('country-select').addEventListener('change', function (event) {
    event.stopPropagation();
});

// Update page heading with active country/state filter labels (derived from select option text)
function updateTitleLocation() {
    const countrySelect = document.getElementById('country-select');
    const stateSelect = document.querySelector('#state-wrapper select');
    const parts = [];
    if (countrySelect.value !== 'all') {
        parts.push(countrySelect.options[countrySelect.selectedIndex].text);
    }
    if (stateSelect && stateSelect.value !== 'all') {
        parts.push(stateSelect.options[stateSelect.selectedIndex].text);
    }
    document.getElementById('nuptial-title-location').textContent =
        parts.length ? ' (' + parts.join(', ') + ')' : '';
}

// Sync URL and title whenever the table content is updated (covers filter changes, pagination, initial load)
document.getElementById('table-container').addEventListener('htmx:afterSettle', function () {
    syncUrl();
    updateTitleLocation();
});

// Export buttons – server handles CSV/JSON generation
document.getElementById('export-csv-btn').addEventListener('click', function () {
    window.location.href = '/ants/nuptial-flight-table/export/csv/?' + getFilterParams();
});

document.getElementById('export-json-btn').addEventListener('click', function () {
    window.location.href = '/ants/nuptial-flight-table/export/json/?' + getFilterParams();
});

// Print button: fill #print-area with all filtered entries, then print
document.getElementById('print-btn').addEventListener('click', function () {
    htmx.ajax('GET', '/ants/nuptial-flight-table/rows/?print=1&' + getFilterParams(), {
        target: '#print-area',
        swap: 'innerHTML',
    }).then(function () {
        window.print();
    });
});

// Reset button: clear all filters to their defaults, remove state select, reload table
document.getElementById('reset-btn').addEventListener('click', function () {
    document.getElementById('name-filter').value = '';
    document.getElementById('month-select').value = 'all';
    document.getElementById('country-select').value = 'all';
    document.getElementById('state-wrapper').innerHTML = '';
    htmx.trigger(document.getElementById('filter-form'), 'change');
    // syncUrl is called automatically after the table settles via htmx:afterSettle
});

// After printing, clear the print area to avoid stale data on next print
window.addEventListener('afterprint', function () {
    document.getElementById('print-area').innerHTML = '';
});
