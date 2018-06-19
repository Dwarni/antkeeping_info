var map = null;
var markers = [];
var flights = [];
var filteredFlights = [];
var mc = null; // Marker Clusterer
var oms = null;
var infoWindow = null;
var markerIcon = null
var mapSettings = {
    center: {lat: 25, lng: 0},
    zoom: 2
};
var mcOptions = {gridSize: 35, maxZoom: 12, imagePath: '/static/flights/img/vendor/markerclusterer/'};
var searchInput = null;

function initMap() {
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: mapSettings.zoom,
        center: mapSettings.center,
        mapTypeId: 'terrain'
    });

    oms = new OverlappingMarkerSpiderfier(map, {
        markersWontMove: true,
        markersWontHide: true,
        basicFormatEvents: true,
        keepSpiderfied: true
    });

    markerIcon = {
        url: '/static/flights/img/marker.png',
        anchor: new google.maps.Point(8, 8)
    }

    searchInput = document.getElementById('antSearchInput');

    // get flights list
    updateMap();
}

function updateMap() {
    // get flights list
    var mcOptions = {gridSize: 35, maxZoom: 8, imagePath: '/static/flights/img/vendor/markerclusterer/'};
    var yearSelect = document.getElementById('yearSelect');
    var year = yearSelect.options[yearSelect.selectedIndex].value;
    
    // Clear out the old markers.
    markers.forEach(function(marker) {
        marker.setMap(null);
    });
    markers = [];
    flights = [];
    $.getJSON( "/flights/list?year=" + year, function(data) {
        flights = data;
        filterFlights();
        updateMarkers();
    })
}

function filterFlights() {
    var filterString = searchInput.value;
    var filterStringLower = filterString.toLowerCase();

    if(filterString) {
        filteredFlights = flights.filter(function(flight) {
            var antSpeciesLower = flight.ant.toLowerCase();
            return antSpeciesLower.indexOf(filterStringLower) >= 0;
        })
    } else {
        filteredFlights = flights;
    }
}

function updateMarkers() {
    // Clear out the old markers.
    markers.forEach(function(marker) {
        marker.setMap(null);
    });
    markers = [];
    oms.removeAllMarkers();

    for(var flight of filteredFlights) {
        var newMarker = new google.maps.Marker({
            map: map,
            icon: markerIcon,
            title: flight.ant,
            position: {lat: flight.lat, lng: flight.lng}
        });
  
        markers.push(newMarker);
        newMarker.addListener('click', function() {
            var that = this;
            var markerIndex = markers.indexOf(this);
            $.get(filteredFlights[markerIndex].id + '/info-window', function(data) {
                $('#flightInfoModalContent').html(data);
                $('#flightInfoModal').modal('toggle');
            })
        });
        
        oms.addMarker(newMarker);
    }

    if(mc) {
        mc.clearMarkers();
        mc.addMarkers(markers);
    } else {
        mc = new MarkerClusterer(map, markers, mcOptions);
    }   
}

window.onload = function() {
    var yearSelect = document.getElementById('yearSelect');
    yearSelect.onchange = function() {
        updateMap();
    }
    searchInput.onkeyup = function() {
        filterFlights();
        updateMarkers();
    }
}