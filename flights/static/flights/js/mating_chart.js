const store = new Vuex.Store({
    state: {
        flightEntries: [],
        loading: false,
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
            state.loading = true
        },
        loadingOff(state) {
            state.loading = false
        },
        toggleFilter(state) {
            state.filterVisible = !state.filterVisible
        },
        updateNameFilter(state, name) {
            state.currentPage = 1
            state.nameFilter = name
        },
        updateCountryFilter(state, countryFilter) {
            state.countryFilter = countryFilter
            state.stateFilter = 'all'
        },
        updateStateFilter(state, stateFilter) {
            state.stateFilter = stateFilter
        },
        setFlightEntries(state, flightEntries) {
            state.flightEntries = flightEntries
        },
        setCountries(state, countries) {
            state.countries = countries
        },
        setStates(state, states) {
            state.states = states
        },
        updateFlyingNow(state, flyingNow) {
            state.currentPage = 1
            state.flyingNow = flyingNow
        },
        resetFilter(state) {
            state.currentPage = 1
            state.nameFilter = ''
            state.flyingNow = false
            state.countryFilter = 'all'
            state.stateFilter = 'all'
            state.states = []
        },
        updateCurrentPage(state, currentPage) {
            state.currentPage = currentPage
        },
        previousPage(state) {
            if(state.currentPage > 1) {
                state.currentPage--
            }
        },
        nextPage(state) {
            const maxPages = calculateMaxPages(state.flightEntries.length, state.entriesPerPage)
            if(state.currentPage < maxPages) {
                state.currentPage++
            }
        }
    },
    actions: {
        fetchFlightEntries({ commit, state }) {
            commit('loadingOn')
            state.currentPage = 1
            const baseURL = '/api/ants/nuptial-flight-months/'
            let url = baseURL
            let params = {}

            if(state.countryFilter != 'all') {
                params.region = state.countryFilter
            }

            if(state.stateFilter != 'all') {
                params.region = state.stateFilter
            }

            var esc = encodeURIComponent;
            var query = Object.keys(params)
                .map(k => esc(k) + '=' + esc(params[k]))
                .join('&');
            if(query.length > 0) {
                url += `?${query}`
            }

            fetch(url)
                .then(response => {
                    return response.json()
                })
                .then(json => {
                    commit('setFlightEntries', json)
                })
            commit('loadingOff')    
        },
        fetchCountries({ commit }) {
            commit('loadingOn')
            fetch('/api/regions/?with-flight-months=true&type=Country')
                .then(response => {
                    return response.json()
                })
                .then(json => {
                    commit('setCountries', json)
                })
            commit('loadingOff')
        },
        fetchStates({ commit, state }) {
            if(state.countryFilter !== 'all') {
                commit('loadingOn')
                fetch(`/api/regions/?with-flight-months=true&parent=${state.countryFilter}`)
                    .then(response => {
                        return response.json()
                    })
                    .then(json => {
                        commit('setStates', json)
                    })
                commit('loadingOff')
            } else {
                commit('setStates', [])
            }
        },
        resetFilter({ commit, dispatch}) {
            commit('resetFilter')
            dispatch('fetchFlightEntries')
        }
    },
    getters: {
        filteredFlightEntries: state => {
            let filteredFlightEntries = state.flightEntries
            const currentMonth = new Date().getMonth() + 1
            if(state.flyingNow === true) {
                filteredFlightEntries = filteredFlightEntries
                                            .filter(flightEntry => flightEntry.flight_months.includes(currentMonth))
            }
            const nameFilterLower = state.nameFilter.toLowerCase()
            if(nameFilterLower !== '' && nameFilterLower.length >= 3) {
                filteredFlightEntries = filteredFlightEntries
                    .filter(flightEntry => {
                        const nameLower = flightEntry.name.toLowerCase()
                        return nameLower.includes(nameFilterLower)
                    })
            }

            return filteredFlightEntries
        },
        flightEntriesCurrentPage: (state, getters) => {
            const start = (state.currentPage - 1) * state.entriesPerPage
            let end =  state.currentPage * state.entriesPerPage
            const flightEntriesLength = getters.filteredFlightEntries.length
            if(end > flightEntriesLength) {
                end = flightEntriesLength
            }
            return getters.filteredFlightEntries.slice(start, end)
        },
        maxPages: (state, getters) => {
            return calculateMaxPages(getters.filteredFlightEntries.length, state.entriesPerPage)
        }
    }
})

function calculateMaxPages(entriesCount, entriesPerPage) {
    return Math.ceil(entriesCount / entriesPerPage)    
}

Vue.component('mating-chart-row', {
    props: ['flightEntry'],
    template: `
        <tr>
            <mating-chart-name-column :speciesName="flightEntry.name" />
            <mating-chart-month-column 
                v-for="n in 12"
                v-bind:current-month="n"
                v-bind:flight-months="flightEntry.flight_months"
                v-bind:key="n"
                ></mating-chart-month-column>
            <td v-if="flightEntry.flight_hour_range" title="Hours of the day" class="pr-1"><i class="bi bi-clock-fill"></i> {{ flightEntry.flight_hour_range.lower }}-{{ flightEntry.flight_hour_range.upper - 1 }}</td>
            <td v-if="flightEntry.flight_climate">
                <i v-if="flightEntry.flight_climate === 'm'" title="Moderate climate" class="bi bi-thermometer-half"></i>
                <i v-else-if="flightEntry.flight_climate === 'w'" title="Warm climate" class="fas bi bi-thermometer-high"></i>
                <div v-else title="Sticky climate"><i class="fas bi bi-thermometer-high"></i><i  class="bi bi-lightning-fill"></i></div>
            </td>
        </tr>
    `
})

Vue.component('mating-chart-name-column', {
    props: { speciesName: String},
    template: `
        <td class="name-column"> <a class="fst-italic" :href="antsURL" target="_blank">{{ speciesName }}</a><a :href="antWikiURL" class="ms-1" title="Antwiki" target="_blank"><span class="badge rounded-pill bg-success">AW</span></a></td>       
    `,
    computed: {
        antsURL: function () {
            const baseURL = '/ants'
            return `${baseURL}/${this.speciesName.toLowerCase().replaceAll(' ', '-')}`
        },
        antWikiURL: function () {
            const baseURL = 'https://antwiki.org/wiki'
            return `${baseURL}/${this.speciesName.replaceAll(' ', '_')}`
        }
    }
})

Vue.component('mating-chart-month-column', {
    props: ['currentMonth', 'flightMonths'],
    data: function() {
        return {
            monthNames: [
                'Jan',
                'Feb',
                'Mar',
                'Apr',
                'May',
                'Jun',
                'Jul',
                'Aug',
                'Sep',
                'Oct',
                'Nov',
                'Dec'
            ]
        }
    },
    template: `
        <td class="month-column" v-bind:class="{'may-fly': mayFly, 'may-not-fly': !mayFly}">{{ monthName }}</td>
    `,
    computed: {
        mayFly: function() {
            return this.flightMonths.includes(this.currentMonth)
        },
        monthName: function() {
            return this.monthNames[this.currentMonth - 1]
        }
    }
})

Vue.component('mating-chart-table', {
    template: `
    <table>
        <tbody>
            <mating-chart-row 
                v-for="flightEntry in flightEntriesCurrentPage" 
                v-bind:flightEntry="flightEntry"
                v-bind:key="flightEntry.name"
                >
            </mating-chart-row>
        </tbody>
    </table>
    `,
    computed: {
        ...Vuex.mapState(['flightEntries']),
        ...Vuex.mapGetters(['flightEntriesCurrentPage'])
    }
})

Vue.component('mating-chart-pagination', {
    template: `
        <nav aria-label="..." v-if="maxPages > 1">
            <ul class="pagination justify-content-center">
                <li class="page-item" v-bind:class="{'disabled': currentPage===1}">
                    <a class="page-link" @click="previousPage" href="#">Previous</a>
                </li>
                <li 
                    v-for="n in maxPages"
                    v-bind:key="n"
                    class="page-item"
                    v-bind:class="{'active': currentPage===n}"
                    >
                    <a class="page-link" href="#" @click="updateCurrentPage(n)">{{ n }}</a>
                </li>
                <li class="page-item" v-bind:class="{'disabled': currentPage===maxPages}">
                    <a class="page-link" @click="nextPage" href="#">Next</a>
                </li>
            </ul>
        </nav>
    `,
    computed: {
        ...Vuex.mapState(['currentPage']),
        ...Vuex.mapGetters(['maxPages'])
    },
    methods: Vuex.mapMutations(['previousPage', 'nextPage', 'updateCurrentPage'])
})

Vue.component('mating-chart-filter', {
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
    created: function() {
        this.$store.dispatch('fetchCountries')
    },
    computed: Vuex.mapState(['countries', 'states', 'nameFilter', 'countryFilter', 'stateFilter', 'flyingNow']),
    methods: {
        ...Vuex.mapActions(['resetFilter']),
        updateNameFilter(e) {
            this.$store.commit('updateNameFilter', e.target.value)
        },
        updateCountryFilter(e) {
            this.$store.commit('updateCountryFilter', e.target.value)
            this.$store.dispatch('fetchStates')
            this.$store.dispatch('fetchFlightEntries')
        },
        updateStateFilter(e) {
            this.$store.commit('updateStateFilter', e.target.value)
            this.$store.dispatch('fetchFlightEntries')
        },
        updateFlyingNow(e) {
            this.$store.commit('updateFlyingNow', e.target.checked)
        }
    }
})

var app = new Vue({
    el: '#mating-chart',
    store,
    created: function() {
        this.$store.dispatch('fetchFlightEntries')
    },
    computed: {
        ...Vuex.mapState(['loading', 'filterVisible']),
        ...Vuex.mapGetters(['filteredFlightEntries'])
    },
    methods: Vuex.mapMutations([
        'toggleFilter'
    ])
})