map=null;
plane=null;
centered=false;

function getIconForPlane(plane) {
    var r = 255, g = 255, b = 0;
    var maxalt = 40000; /* Max altitude in the average case */
    var invalt = maxalt-plane.altitude;

    if (invalt < 0) invalt = 0;
    b = parseInt(255/maxalt*invalt);
    return {
        strokeWeight: 2,
        path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
        scale: 5,
        fillColor: 'rgb('+r+','+g+','+b+')',
        fillOpacity: 0.9,
        rotation: plane.track
    };
}

function refreshInfo() {
    var i = document.getElementById('geninfo');

    if (plane === null || typeof plane.aircraft === "undefined") {
        i.innerHTML = offline_msg;
    }
    else {
        var html = '<h2>Aircraft</h2>';
        html += '<p>';
        html += 'ICAO type: ' + plane.aircraft.icao_type + '<br>';
        html += 'Registration: ' + plane.aircraft.registration + '<br>';
        html += 'Description: ' + plane.aircraft.description + '<br>';
        html += '</p>';
        html += '<h2>Tracking</h2>';
        html += '<p>';
        html += 'Altitude: ' + plane.altitude + ' feet<br>';
        html += 'Coordinates: ' + plane.latitude + ', ' + plane.longitude + '<br>';
        html += 'Track: ' + plane.track + '&deg;<br>';
        html += 'Ground speed: ' + plane.ground_speed + ' knots<br>';
        html += 'Air speed: ' + plane.air_speed + ' knots<br>';
        html += 'Vertical speed: ' + plane.vertical_speed + ' fpm<br>';
        html += '</p>';
        i.innerHTML = html;
    }
}

function fetchData() {
    $.getJSON('/live/', function(data) {
        if (typeof data.aircraft === "undefined") {
            if (plane !== null) {
                plane.marker.setMap(null);
                plane = null;
            }
            refreshInfo();
            return;
        }
        pos = new google.maps.LatLng(data.latitude, data.longitude);
        if (!centered) {
            map.setCenter(pos);
            map.setZoom(10);
            centered = true;
        }
        if (plane === null) {
            marker = new google.maps.Marker({
                position: pos,
                map: map,
                icon: getIconForPlane(data)
            });
            data.marker = marker;
            plane = data;
        }
        else {
            marker = plane.marker;
            var icon = marker.getIcon();
            var newpos = new google.maps.LatLng(data.latitude, data.longitude);
            marker.setPosition(newpos);
            marker.setIcon(getIconForPlane(plane));
            plane.altitude = data.altitude;
            plane.latitude = data.latitude;
            plane.longitude = data.longitude;
            plane.track = data.track;
            plane.air_speed = data.air_speed;
            plane.ground_speed = data.ground_speed;
            plane.vertical_speed = data.vertical_speed;
        }
        refreshInfo();
    });
}

function initialize() {
    map = new google.maps.Map(document.getElementById("map_canvas"), {
        zoom: 3,
        center: new google.maps.LatLng(0, 0),
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });
    fetchData();
    window.setInterval(fetchData, 3000);
}
