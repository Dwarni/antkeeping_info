(function () {
    var map = null;
    var markers = [];
    var flights = [];
    var filteredFlights = [];
    var markerIcon = null
    var searchInput = null;
    var clusterGroup = L.markerClusterGroup();
    var markers = []

    function initMap() {
        map = L.map('map').setView([51.505, -0.09], 13);
        // create the tile layer with correct attribution
        const osmUrl='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
        const osmAttrib='Map data © <a href="https://openstreetmap.org">OpenStreetMap</a> contributors';
        // create the tile layer with correct attribution
	    var osm = new L.TileLayer(osmUrl, {minZoom: 2, maxZoom: 17, attribution: osmAttrib});	

        // start the map in South-East England
        map.setView(new L.LatLng(22, 0),2);
        map.addLayer(osm);
        map.addLayer(clusterGroup);
        clusterGroup.on('click', a => {
            openFlightInfo(a.layer)
        });
        updateMap();
    }

    function openFlightInfo(marker) {
        const markerIndex = markers.indexOf(marker);
        $.get(filteredFlights[markerIndex].id + '/info-window', data => {
            $('#flightInfoModalContent').html(data);
            $('#flightInfoModal').modal('toggle');
        })

    }

    function removeMarkers() {
        clusterGroup.clearLayers();
        markers = []

    }

    function updateMap() {
        var yearSelect = document.getElementById('yearSelect');
        var year = yearSelect.options[yearSelect.selectedIndex].value;

        flights = [];
        $.getJSON("/flights/list?year=" + year, function (data) {
            flights = data;
            filterFlights();
            updateMarkers();
        })
    }

    function filterFlights() {
        var filterString = searchInput.value;
        var filterStringLower = filterString.toLowerCase();

        if (filterString) {
            filteredFlights = flights.filter(function (flight) {
                var antSpeciesLower = flight.ant.toLowerCase();
                return antSpeciesLower.indexOf(filterStringLower) >= 0;
            })
        } else {
            filteredFlights = flights;
        }
    }

    function updateMarkers() {
        removeMarkers()

        for (var flight of filteredFlights) {
            var plotll = new L.LatLng(flight.lat,flight.lng, true);
			var plotmark = new L.Marker(plotll);
            // plotmark.data=plotlist[i];
            markers.push(plotmark)
			clusterGroup.addLayer(plotmark)

            // newMarker.addListener('click', function () {
            //     var that = this;
            //     var markerIndex = markers.indexOf(this);
            //     $.get(filteredFlights[markerIndex].id + '/info-window', function (data) {
            //         $('#flightInfoModalContent').html(data);
            //         $('#flightInfoModal').modal('toggle');
            //     })
            // });
        }
    }

    window.onload = function () {
        var yearSelect = document.getElementById('yearSelect');
        searchInput = document.getElementById('antSearchInput');
        initMap();
        yearSelect.onchange = function () {
            updateMap();
        }
        searchInput.onkeyup = function () {
            filterFlights();
            updateMarkers();
        }
    }
}) ();