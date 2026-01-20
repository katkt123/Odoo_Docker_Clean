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
            var markers = L.featureGroup();
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
                markers.addLayer(m);
            });
            markers.addTo(map);
            try {
                map.fitBounds(markers.getBounds(), {padding: [40, 40]});
            } catch (e) {
                // fallback
            }
        } catch (err) {
            console.error('Failed to load map data', err);
        }
    });
});
