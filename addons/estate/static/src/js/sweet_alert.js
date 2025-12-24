odoo.define('estate.sweet_alert', function (require) {
    "use strict";

    var core = require('web.core');
    var rpc = require('web.rpc');

    // SweetAlert2 CDN - sẽ được tải khi cần
    var sweetAlertLoaded = false;

    function loadSweetAlert() {
        if (sweetAlertLoaded) return Promise.resolve();
        
        return new Promise(function(resolve, reject) {
            // Load CSS
            var css = document.createElement('link');
            css.rel = 'stylesheet';
            css.href = 'https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css';
            document.head.appendChild(css);
            
            // Load JS
            var script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/sweetalert2@11';
            script.onload = function() {
                sweetAlertLoaded = true;
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    function showSweetAlert(options) {
        loadSweetAlert().then(function() {
            if (window.Swal) {
                window.Swal.fire(options);
            }
        });
    }

    // Ghi đè phương thức display_notification
    var ActionManager = require('web.ActionManager');
    
    ActionManager.include({
        _executeNotificationAction: function (action) {
            if (action.type === 'ir.actions.client' && action.tag === 'display_notification') {
                var params = action.params || {};
                
                // Chuyển đổi thông báo Odoo thành SweetAlert
                var sweetAlertOptions = {
                    title: params.title || 'Thông báo',
                    text: params.message || '',
                    icon: 'info',
                    confirmButtonText: 'OK',
                    timer: params.sticky ? null : 3000,
                    timerProgressBar: true
                };
                
                // Xác định icon dựa trên type
                if (params.type === 'success') {
                    sweetAlertOptions.icon = 'success';
                } else if (params.type === 'warning' || params.type === 'danger') {
                    sweetAlertOptions.icon = 'warning';
                } else if (params.type === 'error') {
                    sweetAlertOptions.icon = 'error';
                }
                
                showSweetAlert(sweetAlertOptions);
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        }
    });

    return {
        showSweetAlert: showSweetAlert
    };
});
