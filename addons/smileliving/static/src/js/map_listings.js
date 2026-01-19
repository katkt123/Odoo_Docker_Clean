/* global L */
odoo.define('smileliving.map_listings', function (require) {
    'use strict';
    var ajax = require('web.ajax');
    $(document).ready(function () {
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

        // fetch GeoJSON
        ajax.jsonRpc('/smileliving/map_data', 'call', {}).then(function (data) {
            if (!data || !data.features || !data.features.length) {
                return;
            }
            var markers = L.featureGroup();
            data.features.forEach(function (f) {
                var lon = f.geometry.coordinates[0];
                var lat = f.geometry.coordinates[1];
                var props = f.properties || {};
                var icon = L.icon({
                    iconUrl: '/web/static/src/img/marker.png',
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
                m.bindPopup(popup, {closeButton: false, offset: L.point(0, -10)});
                m.on('mouseover', function () { m.openPopup(); });
                m.on('mouseout', function () { m.closePopup(); });
                markers.addLayer(m);
            });
            markers.addTo(map);
            try {
                map.fitBounds(markers.getBounds(), {padding: [40, 40]});
            } catch (e) {
                // fallback
            }
        });
    });
});
