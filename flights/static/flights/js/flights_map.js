(function () {
    const BING_API_KEY = document.currentScript.getAttribute('bingApiKey')
    class AntMap {
        constructor(year, searchString) {
            this._bingApiKey = BING_API_KEY
            this._markers = []
            this._flights = []
            this._filteredFlights = []
            this._selectedYear = null
            this._filterString = null
            this._year = year
            this._searchString = searchString

            this.initMap()
        }

        get year() {
            return this._year
        }

        set year(value) {
            if(this._year !== value) {
                this._year = value
                this.updateMap()
            }
        }

        get searchString() {
            return this._searchString
        }

        set searchString(value) {
            if(this._searchString !== value) {
                this._searchString = value
                this.filterFlights()
                this.updateMarkers()
            }
        }

        initMap() {
            this._map = L.map('map')
                .setView([45, 10], 2);
            this.initBingLayer()
            this.initClusterGroup()
            //this.focusOnCurrentPosition(4)
            this.updateMap();    
        }

        initClusterGroup() {
            this._clusterGroup = L.markerClusterGroup()
            this._map.addLayer(this._clusterGroup);
            this._clusterGroup.on('click', a => {
                this.openFlightInfo(a.layer)
            });
        }

        initBingLayer() {
            const options = {
                bingMapsKey: this._bingApiKey,
                imagerySet: 'Road',
            }
            L.tileLayer.bing(options).addTo(this._map)
        }

        async getCurrentPosition() {
            return new Promise((resolve, reject) => {
                if ("geolocation" in navigator) {
                    navigator.geolocation.getCurrentPosition(position => {
                        const lat = position.coords.latitude
                        const lng = position.coords.longitude
                        resolve([lat, lng])
                    }, error => {
                        if (error.code == error.PERMISSION_DENIED) {
                            reject("Can't get current position since you denied access to your location")
                        }
                    });
                } else {
                    reject('geolocation is not supported by your browser')
                }
            })
        }

        focusOnCurrentPosition(zoom) {
            this.getCurrentPosition()
                .then(pos => {
                    this._map.setView(pos, zoom)
                })
                .catch(error => {
                    console.log(error)
                })
        }

        openFlightInfo(marker) {
            const markerIndex = this._markers.indexOf(marker);
            const flight = this._filteredFlights[markerIndex]
            fetch(flight.id + '/info-window')
                .then(response => response.text())
                .then(data => {
                    $( "#flightInfoModalContent" ).html(data);
                    $( "#flightInfoModal" ).modal('toggle');    
                })
                .catch(error => console.log(`Could not fetch info for flight with id ${flight.id}: ${error}`))
        }

        removeMarkers() {
            this._clusterGroup.clearLayers();
            this._markers = []
        }

        updateMap() {    
            this._flights = []
            this._filteredFlights = []
            fetch("/flights/list?year=" + this._year)
                .then(response => response.json())
                .then(data => {
                    this._flights = data
                    this.filterFlights()
                    this.updateMarkers()
                })
        }

        filterFlights() {
            var filterStringLower = this._searchString.toLowerCase();
    
            if (filterStringLower) {
                this._filteredFlights = this._flights.filter(function (flight) {
                    var antSpeciesLower = flight.ant.toLowerCase();
                    return antSpeciesLower.indexOf(filterStringLower) >= 0;
                })
            } else {
                this._filteredFlights = this._flights;
            }
        }

        updateMarkers() {
            this.removeMarkers()
    
            for (var flight of this._filteredFlights) {
                var plotll = new L.LatLng(flight.lat,flight.lng, true);
                var plotmark = new L.Marker(plotll);
                this._markers.push(plotmark)
                this._clusterGroup.addLayer(plotmark)
            }
        }
    }

    window.onload = () => {
        const yearSelect = document.getElementById( "yearSelect" )
        const map = new AntMap(yearSelect.value, '')
        
        yearSelect.onchange = e => {
            map.year = e.target.value
        }

        const antSearchInput = document.getElementById( "antSearchInput" )
        antSearchInput.onkeyup = e => {
            map.searchString = e.target.value
        }
    }
}) ();