// Month names for display and CSV export
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_NAMES_CSV = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Trigger a file download in the browser.
 */
function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Escape a value for inclusion in a CSV field.
 */
function escapeCSV(field) {
    if (field === null || field === undefined) return '';
    const s = String(field);
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
}

/**
 * Build a descriptive export filename based on active filters.
 * e.g. "nuptial-flight-table-campo-germany-bavaria"
 */
function buildExportFilename(nameFilter, countryName, stateName) {
    const slugify = s => s.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    const parts = ['nuptial-flight-table'];
    if (nameFilter && nameFilter.length >= 3) parts.push(slugify(nameFilter));
    if (countryName) parts.push(slugify(countryName));
    if (stateName) parts.push(slugify(stateName));
    return parts.join('-');
}

function calculateMaxPages(entriesCount, entriesPerPage) {
    return Math.ceil(entriesCount / entriesPerPage);
}

const store = new Vuex.Store({
    state: {
        flightEntries: [],
        loading: false,
        isPrinting: false,
        // filter
        filterVisible: true,
        countries: [],
        states: [],
        nameFilter: '',
        countryFilter: 'all',
        stateFilter: 'all',
        flyingNow: false,
        currentPage: 1,
        entriesPerPage: 30,
    },
    mutations: {
        loadingOn(state) {
            state.loading = true;
        },
        loadingOff(state) {
            state.loading = false;
        },
        toggleFilter(state) {
            state.filterVisible = !state.filterVisible;
        },
        updateNameFilter(state, name) {
            state.currentPage = 1;
            state.nameFilter = name;
        },
        updateCountryFilter(state, countryFilter) {
            state.countryFilter = countryFilter;
            state.stateFilter = 'all';
        },
        updateStateFilter(state, stateFilter) {
            state.stateFilter = stateFilter;
        },
        setFlightEntries(state, flightEntries) {
            state.flightEntries = flightEntries;
        },
        setCountries(state, countries) {
            state.countries = countries;
        },
        setStates(state, states) {
            state.states = states;
        },
        updateFlyingNow(state, flyingNow) {
            state.currentPage = 1;
            state.flyingNow = flyingNow;
        },
        resetFilter(state) {
            state.currentPage = 1;
            state.nameFilter = '';
            state.flyingNow = false;
            state.countryFilter = 'all';
            state.stateFilter = 'all';
            state.states = [];
        },
        updateCurrentPage(state, currentPage) {
            state.currentPage = currentPage;
        },
        previousPage(state) {
            if (state.currentPage > 1) {
                state.currentPage--;
            }
        },
        nextPage(state) {
            const maxPages = calculateMaxPages(state.flightEntries.length, state.entriesPerPage);
            if (state.currentPage < maxPages) {
                state.currentPage++;
            }
        },
        setPrinting(state, value) {
            state.isPrinting = value;
        },
    },
    actions: {
        fetchFlightEntries({ commit, state }) {
            commit('loadingOn');
            state.currentPage = 1;
            const baseURL = '/api/ants/nuptial-flight-months/';
            let url = baseURL;
            const params = {};

            if (state.countryFilter !== 'all') {
                params.region = state.countryFilter;
            }
            if (state.stateFilter !== 'all') {
                params.region = state.stateFilter;
            }

            const query = Object.keys(params)
                .map(k => encodeURIComponent(k) + '=' + encodeURIComponent(params[k]))
                .join('&');
            if (query.length > 0) {
                url += '?' + query;
            }

            fetch(url)
                .then(response => response.json())
                .then(json => {
                    commit('setFlightEntries', json);
                    commit('loadingOff');
                });
        },
        fetchCountries({ commit }) {
            fetch('/api/regions/?with-flight-months=true&type=Country')
                .then(response => response.json())
                .then(json => {
                    commit('setCountries', json);
                });
        },
        fetchStates({ commit, state }) {
            if (state.countryFilter !== 'all') {
                fetch('/api/regions/?with-flight-months=true&parent=' + state.countryFilter)
                    .then(response => response.json())
                    .then(json => {
                        commit('setStates', json);
                    });
            } else {
                commit('setStates', []);
            }
        },
        resetFilter({ commit, dispatch }) {
            commit('resetFilter');
            dispatch('fetchFlightEntries');
        },
        exportCSV({ getters, state }) {
            const data = getters.filteredFlightEntries;
            const headers = ['Species', ...MONTH_NAMES_CSV, 'Flight time', 'Climate'];
            const rows = data.map(item => {
                let time = '';
                if (item.flight_hour_range) {
                    time = item.flight_hour_range.lower + '-' + (item.flight_hour_range.upper - 1);
                }
                let climate = '';
                if (item.flight_climate === 'm') climate = 'Moderate';
                else if (item.flight_climate === 'w') climate = 'Warm';
                else if (item.flight_climate === 's') climate = 'Muggy';

                const monthFlags = Array.from({ length: 12 }, (_, i) =>
                    item.flight_months.includes(i + 1) ? 'x' : ''
                );
                return [item.name, ...monthFlags, time, climate];
            });

            // Build CSV with BOM for Excel UTF-8 compatibility
            const BOM = '\uFEFF';
            const headerRow = headers.map(escapeCSV).join(',');
            const dataRows = rows.map(row => row.map(escapeCSV).join(',')).join('\n');
            const csv = BOM + headerRow + '\n' + dataRows;

            downloadFile(csv, buildExportFilename(state.nameFilter, getters.selectedCountryName, getters.selectedStateName) + '.csv', 'text/csv;charset=utf-8');
        },
        exportJSON({ getters, state }) {
            const data = getters.filteredFlightEntries;
            const json = JSON.stringify(data, null, 2);
            downloadFile(json, buildExportFilename(state.nameFilter, getters.selectedCountryName, getters.selectedStateName) + '.json', 'application/json');
        },
        async printTable({ commit }) {
            commit('setPrinting', true);
            // Wait for Vue to render the print area before opening the print dialog
            await Vue.nextTick();
            setTimeout(() => {
                window.print();
                window.addEventListener('afterprint', function onAfterPrint() {
                    commit('setPrinting', false);
                    window.removeEventListener('afterprint', onAfterPrint);
                }, { once: true });
            }, 100);
        },
    },
    getters: {
        filteredFlightEntries: state => {
            let entries = state.flightEntries;
            const currentMonth = new Date().getMonth() + 1;
            if (state.flyingNow) {
                entries = entries.filter(e => e.flight_months.includes(currentMonth));
            }
            const nameLower = state.nameFilter.toLowerCase();
            if (nameLower.length >= 3) {
                entries = entries.filter(e => e.name.toLowerCase().includes(nameLower));
            }
            return entries;
        },
        flightEntriesCurrentPage: (state, getters) => {
            const start = (state.currentPage - 1) * state.entriesPerPage;
            let end = state.currentPage * state.entriesPerPage;
            const total = getters.filteredFlightEntries.length;
            if (end > total) end = total;
            return getters.filteredFlightEntries.slice(start, end);
        },
        maxPages: (state, getters) => {
            return calculateMaxPages(getters.filteredFlightEntries.length, state.entriesPerPage);
        },
        selectedCountryName: state => {
            if (state.countryFilter === 'all') return null;
            const c = state.countries.find(c => String(c.id) === String(state.countryFilter));
            return c ? c.name : null;
        },
        selectedStateName: state => {
            if (state.stateFilter === 'all') return null;
            const s = state.states.find(s => String(s.id) === String(state.stateFilter));
            return s ? s.name : null;
        },
    },
});

// Shared row template used in both the paginated table and the full print table
Vue.component('nuptial-flight-row', {
    props: ['flightEntry'],
    template: `
        <tr>
            <nuptial-flight-name-column :speciesName="flightEntry.name" :forbiddenInEu="flightEntry.forbidden_in_eu" />
            <nuptial-flight-month-column
                v-for="n in 12"
                v-bind:current-month="n"
                v-bind:flight-months="flightEntry.flight_months"
                v-bind:key="n"
            ></nuptial-flight-month-column>
            <td class="time-column">
                <span v-if="flightEntry.flight_hour_range">
                    <i class="bi bi-clock-fill"></i>
                    {{ flightEntry.flight_hour_range.lower }}-{{ flightEntry.flight_hour_range.upper - 1 }}
                </span>
            </td>
            <td class="climate-column">
                <i v-if="flightEntry.flight_climate === 'm'" class="bi bi-thermometer-half" title="Moderate climate"></i>
                <i v-else-if="flightEntry.flight_climate === 'w'" class="bi bi-thermometer-high" title="Warm climate"></i>
                <span v-else-if="flightEntry.flight_climate === 's'" title="Muggy climate">
                    <i class="bi bi-thermometer-high"></i><i class="bi bi-lightning-fill"></i>
                </span>
            </td>
        </tr>
    `,
});

Vue.component('nuptial-flight-name-column', {
    props: {
        speciesName: String,
        forbiddenInEu: Boolean,
    },
    template: `
        <td class="name-column">
            <a class="fst-italic" :href="antsURL">{{ speciesName }}</a>
            <a :href="antWikiURL" class="ms-1" title="AntWiki" target="_blank">
                <span class="badge rounded-pill bg-success">AW</span>
            </a>
            <span v-if="forbiddenInEu" class="badge bg-danger ms-1" title="Forbidden in EU">
                <i class="bi bi-ban"></i> EU
            </span>
        </td>
    `,
    computed: {
        antsURL() {
            return '/ants/' + this.speciesName.toLowerCase().replaceAll(' ', '-');
        },
        antWikiURL() {
            return 'https://antwiki.org/wiki/' + this.speciesName.replaceAll(' ', '_');
        },
    },
});

Vue.component('nuptial-flight-month-column', {
    props: ['currentMonth', 'flightMonths'],
    template: `
        <td class="month-column" v-bind:class="{'may-fly': mayFly, 'may-not-fly': !mayFly}">
            {{ monthName }}
        </td>
    `,
    computed: {
        mayFly() {
            return this.flightMonths.includes(this.currentMonth);
        },
        monthName() {
            return MONTH_NAMES[this.currentMonth - 1];
        },
    },
});

Vue.component('nuptial-flight-table-component', {
    template: `
        <div class="table-responsive">
            <table class="table table-sm table-bordered nuptial-flight-table">
                <thead class="table-light">
                    <tr>
                        <th>Species</th>
                        <th v-for="m in monthHeaders" :key="m" class="month-column">{{ m }}</th>
                        <th class="time-column">Time</th>
                        <th class="climate-column">Climate</th>
                    </tr>
                </thead>
                <tbody>
                    <nuptial-flight-row
                        v-for="entry in flightEntriesCurrentPage"
                        v-bind:flightEntry="entry"
                        v-bind:key="entry.id"
                    ></nuptial-flight-row>
                </tbody>
            </table>
        </div>
    `,
    data() {
        return { monthHeaders: MONTH_NAMES };
    },
    computed: {
        ...Vuex.mapGetters(['flightEntriesCurrentPage']),
    },
});

// Full table rendered only when printing (no pagination, all filtered entries)
Vue.component('nuptial-flight-print-table', {
    template: `
        <div class="nuptial-print-area">
            <h3>Nuptial Flight Table<span v-if="locationLabel"> ({{ locationLabel }})</span></h3>
            <p class="filter-summary">{{ filterSummary }}</p>
            <table class="nuptial-flight-table">
                <thead>
                    <tr>
                        <th>Species</th>
                        <th v-for="m in monthHeaders" :key="m" class="month-column">{{ m }}</th>
                        <th>Time</th>
                        <th>Climate</th>
                    </tr>
                </thead>
                <tbody>
                    <nuptial-flight-row
                        v-for="entry in filteredFlightEntries"
                        v-bind:flightEntry="entry"
                        v-bind:key="entry.id"
                    ></nuptial-flight-row>
                </tbody>
            </table>
            <div class="print-legend">
                <strong>Legend:</strong>
                <span class="legend-item"><span class="legend-swatch may-fly"></span> Flight month</span>
                <span class="legend-item"><i class="bi bi-clock-fill"></i> Flight time (h)</span>
                <span class="legend-item"><i class="bi bi-thermometer-half"></i> Moderate climate</span>
                <span class="legend-item"><i class="bi bi-thermometer-high"></i> Warm climate</span>
                <span class="legend-item"><i class="bi bi-thermometer-high"></i><i class="bi bi-lightning-fill"></i> Muggy/humid climate</span>
                <span class="legend-item"><span class="badge bg-danger"><i class="bi bi-ban"></i> EU</span> Forbidden in EU</span>
            </div>
            <p class="print-footer">Source: antkeeping.info</p>
        </div>
    `,
    data() {
        return { monthHeaders: MONTH_NAMES };
    },
    computed: {
        ...Vuex.mapGetters(['filteredFlightEntries', 'selectedCountryName', 'selectedStateName']),
        ...Vuex.mapState(['nameFilter', 'flyingNow']),
        locationLabel() {
            const parts = [];
            if (this.selectedCountryName) parts.push(this.selectedCountryName);
            if (this.selectedStateName) parts.push(this.selectedStateName);
            return parts.join(', ');
        },
        filterSummary() {
            const parts = [];
            if (this.nameFilter) parts.push('Search: "' + this.nameFilter + '"');
            if (this.flyingNow) parts.push('Flying now');
            return parts.length ? 'Filter: ' + parts.join(' | ') : 'No filters applied';
        },
    },
});

Vue.component('nuptial-flight-pagination', {
    template: `
        <nav aria-label="Pagination" v-if="maxPages > 1">
            <ul class="pagination justify-content-center">
                <li class="page-item" v-bind:class="{'disabled': currentPage === 1}">
                    <a class="page-link" @click.prevent="previousPage" href="#">Previous</a>
                </li>
                <li
                    v-for="n in maxPages"
                    v-bind:key="n"
                    class="page-item"
                    v-bind:class="{'active': currentPage === n}"
                >
                    <a class="page-link" href="#" @click.prevent="updateCurrentPage(n)">{{ n }}</a>
                </li>
                <li class="page-item" v-bind:class="{'disabled': currentPage === maxPages}">
                    <a class="page-link" @click.prevent="nextPage" href="#">Next</a>
                </li>
            </ul>
        </nav>
    `,
    computed: {
        ...Vuex.mapState(['currentPage']),
        ...Vuex.mapGetters(['maxPages']),
    },
    methods: Vuex.mapMutations(['previousPage', 'nextPage', 'updateCurrentPage']),
});

Vue.component('nuptial-flight-filter', {
    template: `
        <div>
            <h4 class="text-muted mb-3">Filter</h4>
            <div class="mb-3">
                <label for="nameFilter">Name:</label>
                <input :value="nameFilter" @input="updateNameFilter" type="text" class="form-control" id="nameFilter" placeholder="e.g. lasius">
            </div>
            <div class="form-check mb-3">
                <input type="checkbox" class="form-check-input" id="flyingNow" :checked="flyingNow" @click="updateFlyingNow">
                <label class="form-check-label" for="flyingNow">Flying Now</label>
            </div>
            <div class="mb-3">
                <label for="country">Country:</label>
                <select :value="countryFilter" @change="updateCountryFilter" id="country" class="form-control">
                    <option value="all">All</option>
                    <option v-for="country in countries" v-bind:key="country.id" v-bind:value="country.id">
                        {{ country.name }}
                    </option>
                </select>
            </div>
            <div class="mb-3" v-if="states.length > 0">
                <label for="state">State:</label>
                <select :value="stateFilter" @change="updateStateFilter" id="state" class="form-control">
                    <option value="all">All</option>
                    <option v-for="state in states" v-bind:key="state.id" v-bind:value="state.id">
                        {{ state.name }}
                    </option>
                </select>
            </div>
            <div class="mb-3">
                <button type="button" class="btn btn-warning" @click="resetFilter">Reset</button>
            </div>
        </div>
    `,
    created() {
        this.$store.dispatch('fetchCountries');
    },
    computed: Vuex.mapState(['countries', 'states', 'nameFilter', 'countryFilter', 'stateFilter', 'flyingNow']),
    methods: {
        ...Vuex.mapActions(['resetFilter']),
        updateNameFilter(e) {
            this.$store.commit('updateNameFilter', e.target.value);
        },
        updateCountryFilter(e) {
            this.$store.commit('updateCountryFilter', e.target.value);
            this.$store.dispatch('fetchStates');
            this.$store.dispatch('fetchFlightEntries');
        },
        updateStateFilter(e) {
            this.$store.commit('updateStateFilter', e.target.value);
            this.$store.dispatch('fetchFlightEntries');
        },
        updateFlyingNow(e) {
            this.$store.commit('updateFlyingNow', e.target.checked);
        },
    },
});

var app = new Vue({
    el: '#nuptial-flight-table',
    store,
    delimiters: ['[[', ']]'],
    created() {
        this.$store.dispatch('fetchFlightEntries');
    },
    computed: {
        ...Vuex.mapState(['loading', 'filterVisible', 'isPrinting']),
        ...Vuex.mapGetters(['filteredFlightEntries', 'flightEntriesCurrentPage']),
    },
    methods: {
        ...Vuex.mapMutations(['toggleFilter']),
        exportCSV() {
            this.$store.dispatch('exportCSV');
        },
        exportJSON() {
            this.$store.dispatch('exportJSON');
        },
        printTable() {
            this.$store.dispatch('printTable');
        },
    },
});
