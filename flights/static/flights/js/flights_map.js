var map = null;
var markers = [];
var flights = [];
var mc = null; // Marker Clusterer
var oms = null;
var infoWindow = null;
var markerIcon = null
var mapSettings = {
    center: {lat: 25, lng: 0},
    zoom: 2
};

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
        oms.removeAllMarkers();
        for(var i = 0; i < data.length; i++) {
            var flight = data[i]
            flights.push(flight)
        // Create a marker for each place.
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
                $.get(flights[markerIndex].id + '/info-window', function(data) {
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

        map.setCenter(mapSettings.center);
        map.setZoom(mapSettings.zoom);
    })
}

window.onload = function() {
    var yearSelect = document.getElementById('yearSelect');
    yearSelect.onchange = function() {
        updateMap();
    }    
}