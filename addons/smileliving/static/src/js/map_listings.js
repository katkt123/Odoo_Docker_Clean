/* global L */
odoo.define('smileliving.map_listings', [], function (require) {
    'use strict';
    // Không phụ thuộc vào module `web.ajax` (tránh lỗi asset bundle)
    // Dùng `fetch` native để gọi endpoint trả về GeoJSON

    function loadScript(src){
        return new Promise(function(resolve, reject){
            if (document.querySelector('script[src="' + src + '"]')){
                // already present, wait a tick
                return resolve();
            }
            var s = document.createElement('script');
            s.src = src;
            s.async = false;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    function loadCSS(href){
        if (document.querySelector('link[href="' + href + '"]')){
            return;
        }
        var l = document.createElement('link');
        l.rel = 'stylesheet';
        l.href = href;
        document.head.appendChild(l);
    }

    async function ensureLeaflet(){
        if (window.L) {
            return;
        }
        try{
            loadCSS('https://unpkg.com/leaflet@1.9.3/dist/leaflet.css');
            await loadScript('https://unpkg.com/leaflet@1.9.3/dist/leaflet.js');
            // load Turf for polygon point-in-polygon checks
            await loadScript('https://cdn.jsdelivr.net/npm/@turf/turf@6.5.0/turf.min.js');
        } catch (e){
            console.error('Failed to load Leaflet from CDN', e);
        }
    }

    $(document).ready(async function () {
        await ensureLeaflet();
        if (!window.L) {
            console.error('Leaflet is not available');
            return;
        }
        var $map = $('#smile_map');
        if (!$map.length) {
            return;
        }
        // Init map
        var map = L.map('smile_map').setView([10.776889, 106.700806], 11);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        // Search control will be added after map data is loaded so it uses
        // the final `doSearch` and marker helpers (defined later)

        // Prepare marker groups and helper functions early so the control is always visible
        var allMarkersGroup = L.featureGroup();
        var visibleLayer = L.layerGroup().addTo(map);
        var markerList = [];
        var currentRect = null; // rectangle overlay for last search
        var currentPolygonLayer = null; // for non-rectangular district polygon

        // doSearch: try local marker search first, fallback to Nominatim geocode
        function doSearch(q){
            q = (q || '').trim();
            if (!q) { showAllMarkers(); return; }
            var ql = q.toLowerCase();
            // find markers whose attached props match query
            var matches = markerList.filter(function(m){
                try {
                    var p = m._props || {};
                    var fields = [p.title, p.address, p.district, p.city, p.street];
                    return fields.some(function(f){ return f && String(f).toLowerCase().indexOf(ql) !== -1; });
                } catch (e) { return false; }
            });
            if (matches && matches.length) {
                visibleLayer.clearLayers();
                matches.forEach(function(m){ visibleLayer.addLayer(m); });
                try {
                    var bounds = L.latLngBounds(matches.map(function(m){ return m.getLatLng(); }));
                    // ensure minimum visible area
                    var latDiff = Math.abs(bounds.getNorth() - bounds.getSouth());
                    var lonDiff = Math.abs(bounds.getEast() - bounds.getWest());
                    var minDelta = 0.005;
                    if (latDiff < 1e-6 || lonDiff < 1e-6) {
                        var c = bounds.getCenter();
                        bounds = L.latLngBounds([ [c.lat - minDelta, c.lng - minDelta], [c.lat + minDelta, c.lng + minDelta] ]);
                    }
                    try { map.fitBounds(bounds, { padding: [40, 40] }); } catch (e) {}
                    if (currentRect) { try { map.removeLayer(currentRect); } catch (e) {} currentRect = null; }
                    try { currentRect = L.rectangle(bounds, {color: '#ff7800', weight: 3, fill: true, fillOpacity: 0.12, interactive: false}).addTo(map); } catch(e){}
                } catch (e) { console.warn('Fit bounds for matches failed', e); }
                return;
            }
            // fallback to geocode — request polygon (if available) from Nominatim
            var url = 'https://nominatim.openstreetmap.org/search?format=json&limit=1&polygon_geojson=1&q=' + encodeURIComponent(q);
            fetch(url, { headers: { 'Accept': 'application/json' } }).then(function (r){ return r.json(); }).then(function(res){
                if (!res || !res.length){ alert('Không tìm thấy vị trí'); return; }
                var place = res[0];
                // clear previous polygon/rect
                if (currentPolygonLayer) { try{ map.removeLayer(currentPolygonLayer); } catch(e){} currentPolygonLayer = null; }
                if (currentRect) { try{ map.removeLayer(currentRect); } catch(e){} currentRect = null; }
                // if geojson polygon available, draw it and filter markers by polygon
                if (place.geojson || place.polygon_geojson || place.geojson) {
                    var poly = place.geojson || place.polygon_geojson || place.geojson;
                    try {
                        currentPolygonLayer = L.geoJSON(poly, { style: { color: '#3388ff', weight: 2, fillOpacity: 0.08 } }).addTo(map);
                        try { map.fitBounds(currentPolygonLayer.getBounds(), { padding: [40,40] }); } catch(e){}
                        // filter markers using turf if available
                        if (window.turf) {
                            visibleLayer.clearLayers();
                            markerList.forEach(function(m){
                                try {
                                    var pt = turf.point([m.getLatLng().lng, m.getLatLng().lat]);
                                    if (turf.booleanPointInPolygon(pt, poly)) {
                                        visibleLayer.addLayer(m);
                                    }
                                } catch (e) {}
                            });
                        } else {
                            // fallback: include markers whose latlng is inside polygon bounds
                            var b = currentPolygonLayer.getBounds();
                            filterMarkersByBounds(b);
                        }
                        return;
                    } catch (e) {
                        console.warn('Failed to render polygon', e);
                    }
                }
                // if no polygon, fallback to bbox rectangle
                if (!place.boundingbox){ alert('Không có bounding box cho vị trí này'); return; }
                var south = parseFloat(place.boundingbox[0]);
                var north = parseFloat(place.boundingbox[1]);
                var west = parseFloat(place.boundingbox[2]);
                var east = parseFloat(place.boundingbox[3]);
                var bounds = L.latLngBounds([ [south, west], [north, east] ]);
                var latDiff = Math.abs(bounds.getNorth() - bounds.getSouth());
                var lonDiff = Math.abs(bounds.getEast() - bounds.getWest());
                var minDelta = 0.01;
                if (latDiff < 1e-6 || lonDiff < 1e-6) {
                    var c = bounds.getCenter();
                    bounds = L.latLngBounds([ [c.lat - minDelta, c.lng - minDelta], [c.lat + minDelta, c.lng + minDelta] ]);
                }
                filterMarkersByBounds(bounds);
                try { map.fitBounds(bounds, { padding: [40, 40] }); } catch (e) {}
                if (currentRect) { try { map.removeLayer(currentRect); } catch (e) {} currentRect = null; }
                try { currentRect = L.rectangle(bounds, {color: '#ff7800', weight: 3, fill: true, fillOpacity: 0.12, interactive: false}).addTo(map); } catch(e){}
            }).catch(function(err){ console.error('Geocode error', err); alert('Lỗi khi tìm vị trí'); });
        }

        function showAllMarkers(){
            visibleLayer.clearLayers();
            markerList.forEach(function(m){ visibleLayer.addLayer(m); });
            if (currentRect) { try { map.removeLayer(currentRect); } catch(e){} currentRect = null; }
        }

        function filterMarkersByBounds(bounds){
            visibleLayer.clearLayers();
            markerList.forEach(function(m){ try{ if (bounds.contains(m.getLatLng())){ visibleLayer.addLayer(m); } }catch(e){} });
        }

        // Add simple search control (uses Nominatim) to zoom into a city/district
        var SearchControl = L.Control.extend({
            options: { position: 'topright' },
            onAdd: function () {
                var container = L.DomUtil.create('div', 'smile-search-control');
                container.style.background = 'white';
                container.style.padding = '6px';
                container.style.borderRadius = '6px';
                container.style.boxShadow = '0 1px 4px rgba(0,0,0,0.2)';

                var input = L.DomUtil.create('input', '', container);
                input.type = 'search';
                input.placeholder = 'Tìm: Quận 7, TP Hồ Chí Minh...';
                input.style.width = '180px';
                input.style.marginRight = '6px';

                var btn = L.DomUtil.create('button', '', container);
                btn.innerText = 'Tìm';
                btn.style.cursor = 'pointer';

                var reset = L.DomUtil.create('button', '', container);
                reset.innerText = 'Tất cả';
                reset.style.marginLeft = '6px';
                reset.style.cursor = 'pointer';

                L.DomEvent.disableClickPropagation(container);

                btn.addEventListener('click', function () { doSearch(input.value); });
                input.addEventListener('keyup', function (ev) { if (ev.key === 'Enter') { doSearch(input.value); } });
                reset.addEventListener('click', function () { showAllMarkers(); try { map.fitBounds(allMarkersGroup.getBounds(), {padding:[40,40]}); } catch(e){} });

                return container;
            }
        });
        map.addControl(new SearchControl());
        // fetch GeoJSON (API trả về JSON)
        try {
            var resp = await fetch('/smileliving/map_data', { credentials: 'same-origin', headers: {'Accept': 'application/json'} });
            if (!resp.ok) {
                console.error('Failed to load map data, status:', resp.status);
                return;
            }
            var data = await resp.json();
            if (!data || !data.features || !data.features.length) {
                return;
            }
            // Groups to manage markers and visibility (reuse outer variables)
            allMarkersGroup = L.featureGroup();
            visibleLayer = L.layerGroup().addTo(map);
            markerList = [];

            // Initially show all markers
            markerList.forEach(function(m){ visibleLayer.addLayer(m); });
            try { map.fitBounds(visibleLayer.getBounds(), {padding: [40,40]}); } catch (e) {}

            
            data.features.forEach(function (f) {
                var lon = f.geometry.coordinates[0];
                var lat = f.geometry.coordinates[1];
                var props = f.properties || {};
                var icon = L.icon({
                    // Use module static path (file is at addons/smileliving/static/img/marker.png)
                    iconUrl: '/smileliving/static/img/marker.png',
                    iconSize: [30, 30],
                    iconAnchor: [15, 30],
                });
                var m = L.marker([lat, lon], {icon: icon});
                // attach original properties to marker for local search
                m._props = props || {};
                var popup = '<div style="display:flex;gap:8px;align-items:center;min-width:220px">';
                if (props.thumb) {
                    popup += '<img src="' + props.thumb + '" style="width:80px;height:60px;object-fit:cover;border-radius:4px"/>';
                }
                popup += '<div><strong>' + (props.title || '') + '</strong><div style="color:#666;margin-top:6px">';
                if (props.price) {
                    popup += '<span>' + props.price.toLocaleString() + '</span>';
                }
                popup += '</div><div style="margin-top:6px"><a href="' + (props.url || '#') + '">Xem chi tiết</a></div></div></div>';
                // Keep popup interactive so user can move mouse from marker -> popup
                // and still click buttons inside popup. Disable autoClose/closeOnClick
                // and implement a small close delay when mouse leaves both marker and popup.
                m.bindPopup(popup, {closeButton: false, offset: L.point(0, -10), autoClose: false, closeOnClick: false});
                // store close timeout handle on marker
                m._closeTimeout = null;

                function clearCloseTimeout() {
                    if (m._closeTimeout) {
                        clearTimeout(m._closeTimeout);
                        m._closeTimeout = null;
                    }
                }

                function scheduleClose(delay) {
                    clearCloseTimeout();
                    m._closeTimeout = setTimeout(function () {
                        try { m.closePopup(); } catch (e) {}
                        m._closeTimeout = null;
                    }, delay || 250);
                }

                m.on('mouseover', function () { clearCloseTimeout(); m.openPopup(); });
                m.on('mouseout', function () { scheduleClose(250); });

                // When popup opens, attach listeners on popup DOM to keep it open
                map.on('popupopen', function (ev) {
                    if (ev.popup && ev.popup._source === m) {
                        var popupEl = ev.popup.getElement();
                        if (popupEl) {
                            popupEl.addEventListener('mouseover', function () { clearCloseTimeout(); });
                            popupEl.addEventListener('mouseout', function () { scheduleClose(250); });
                            // Allow clicking inside popup without it being closed by map click
                            popupEl.addEventListener('click', function (e) { e.stopPropagation(); });
                        }
                    }
                });
                allMarkersGroup.addLayer(m);
                markerList.push(m);
            });
            // Initially show all markers
            markerList.forEach(function(m){ visibleLayer.addLayer(m); });
            try { map.fitBounds(visibleLayer.getBounds(), {padding: [40,40]}); } catch (e) {}

        } catch (err) {
            console.error('Failed to load map data', err);
        }
    });
});
