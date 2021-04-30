import Toast from "./classes/Toast.js";

$(document).ready(function () {
    // Do not collapse accordion when clicking on body
    $(".collapse").on('click', (e) => {
        e.stopPropagation();
    });

    // Restore system status card positions on reload
    const order = JSON.parse(localStorage.getItem('order'));
    if (order) {
        for (const key of Object.keys(order)) {
            $.each(order[key], function (i, item) {
                let $target = $(".connectedSortable").find('#' + item);
                $target.appendTo($('#' + key));
            });
        }
    }

    $(function () {
        $("#sortable-1, #sortable-2, #sortable-3").sortable({
            connectWith: ".connectedSortable",
            containment: ".sortableParent",
            placeholder: "highlight",
            forcePlaceholderSize: true,
            delay: 100,
            revert: 300,
            cursor: "move",
            tolerance: "pointer",
            update: function (event, ui) {
                const col1 = $("#sortable-1").sortable('toArray');
                const col2 = $("#sortable-2").sortable('toArray');
                const col3 = $("#sortable-3").sortable('toArray');
                const order = {
                    "sortable-1": col1,
                    "sortable-2": col2,
                    "sortable-3": col3,
                };
                localStorage.setItem('order', JSON.stringify(order));
            }
        }).disableSelection();
    });

    function getPerformance() {
        // Called every 10 seconds
        $.ajax("/api/system/performance").done((data) => {
            const cpuUsage = data["system"]["cpu_info"]["percent"];
            $("#cpu_usage_percent").text(cpuUsage + "%");
            $("#cpu_usage_progress").css("width", cpuUsage + "%");

            const cpuFreq = data["system"]["cpu_info"]["frequency"];
            $("#cpu_freq").text(cpuFreq / 1000 + " GHz");

            const memoryUsage = data["system"]["memory_info"]["percent"];
            $("#memory_usage_percent").text(memoryUsage + "%");
            $("#memory_usage_progress").css("width", memoryUsage + "%");

            const memoryUsed = data["system"]["memory_info"]["used"];
            $("#memory_used").text(bytesToGigabytes(memoryUsed).toFixed(1) + " GB");

            const memoryTotal = data["system"]["memory_info"]["total"];
            $("#memory_total").text(bytesToGigabytes(memoryTotal).toFixed(1) + " GB");

            const diskUsage = data["system"]["disk_info"]["percent"];
            $("#disk_usage_percent").text(diskUsage + "%");
            $("#disk_usage_progress").css("width", diskUsage + "%");

            const diskUsed = data["system"]["disk_info"]["used"];
            $("#disk_used").text(bytesToGigabytes(diskUsed).toFixed(1) + " GB");

            const diskTotal = data["system"]["disk_info"]["total"];
            $("#disk_total").text(bytesToGigabytes(diskTotal).toFixed(1) + " GB");

            const networkInterfaces = data["system"]["network_info"];
            if ($("#network_interfaces").children().length < networkInterfaces.length) {
                for (var i = 0, len = networkInterfaces.length; i < len; i++) {
                    const interfaceName = networkInterfaces[i]["name"];
                    const interfaceAddress = networkInterfaces[i]["address"];
                    const interfaceNetmask = networkInterfaces[i]["netmask"];
                    const interfaceGbRecv = bytesToGigabytes(networkInterfaces[i]["bytes_recv"]).toFixed(1);
                    const interfaceGbSent = bytesToGigabytes(networkInterfaces[i]["bytes_sent"]).toFixed(1);
                    let border = "border-bottom";
                    if (i === len - 1) {
                        border = "";
                    }
                    const interfaceCard = `
                        <div class="card-block ${border}">
                            <div class="row">
                                <div class="col-auto">
                                    <label class="badge badge-pill px-3 py-2 mr-2 theme-bg2 text-white f-14 f-w-400">
                                        <span>${interfaceName}</span>
                                    </label>
                                    <label class="badge badge-pill px-3 py-2 mr-2 theme-bg2 text-white f-14 f-w-400">
                                        <i class="feather icon-arrow-down text-c-green"></i>
                                        <span>${interfaceGbRecv} GB</span>
                                    </label>
                                    <label class="badge badge-pill px-3 py-2 theme-bg2 text-white f-14 f-w-400">
                                        <i class="feather icon-arrow-up text-c-yellow"></i>
                                        <span>${interfaceGbSent} GB</span>
                                    </label>
                                </div>
                            </div>
                            <h3 class="mt-3 f-w-300">${interfaceAddress}</h3>
                            <h6 class="text-muted mt-2 mb-0 text-uppercase">address</h6>
                            <h3 class="mt-3 f-w-300">${interfaceNetmask}</h3>
                            <h6 class="text-muted mt-2 mb-0 text-uppercase">netmask</h6>
                        </div>
                    `;
                    $("#network_interfaces").append(interfaceCard);
                }
            }
        }).catch((error) => {
            new Toast("Unable to reach the server.").error();
        });
        setTimeout(getPerformance, 10000);
    }
    getPerformance();

    function getTemperature() {
        // Called every 20 seconds
        $.ajax("/api/system/temperature").done((data) => {
            const cpuTempC = data["system"]["raspi"]["celsius"];
            const cpuTempF = data["system"]["raspi"]["fahrenheit"];
            $("#cpu_temperature").html(cpuTempC + "°C&nbsp;&nbsp;/&nbsp;&nbsp;" + cpuTempF + "°F");
            $("#cpu_temperature_progress").css("width", cpuTempC + "%");
        });
        setTimeout(getTemperature, 20000);
    }
    getTemperature()

    function getServices() {
        // Preload services
        $.ajax("/api/system/services").done((data) => {
            const services = data["services"];
            for (var i = 0, len = services.length; i < len; i++) {
                const serviceName = services[i];
                let status = "Checking";
                let statusColor = "theme-bg2";
                let border = "border-bottom";
                if (i === len - 1) {
                    border = "";
                }
                const service = `
                    <div class="card-block ${border} py-4">
                        <div class="row align-items-center justify-content-center">
                            <div class="col">
                                <h3 class="m-0 f-w-300">${serviceName}</h3>
                            </div>
                            <div class="col-auto">
                                <label id="${serviceName}" class="badge badge-pill mt-2 px-3 py-2 ${statusColor} text-white f-14 f-w-400 float-right">
                                    <span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span>
                                    <span>${status}</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `;
                $("#services").append(service);
            }
        });
    }
    getServices();

    function getServicesStatus() {
        // Called once on page load
        return new Promise((resolve, reject) => {
            $.ajax({
                url: "/api/system/services/status",
                type: 'GET',
                data: {},
                contentType: 'application/json;charset=UTF-8',
                success: function (data) {
                    resolve(data);
                },
                error: function (error) {
                    reject(error);
                }
            });
        });
    }

    getServicesStatus()
        // Update service status
        .then((data) => {
            const services = data["services"];
            for (var i = 0, len = services.length; i < len; i++) {
                const serviceName = services[i]["name"];
                const serviceStatus = services[i]["running"];
                let status = "Stopped";
                let statusColor = "bg-danger";
                if (serviceStatus) {
                    status = "Running";
                    statusColor = "theme-bg";
                }
                $("#" + serviceName).text(status).removeClass("theme-bg2").addClass(statusColor);
            }
        })
        .catch((error) => {
            console.log(error);
        })

    function getDevices() {
        // Preload devices
        $.ajax("/api/system/devices").done((devices) => {
            if ($("#devices").children("div").length < devices.length) {
                for (var i = 0, len = devices.length; i < len; i++) {
                    const deviceName = devices[i]["name"];
                    const deviceId = devices[i]["id"];
                    let status = "Checking";
                    let border = "border-bottom";
                    if (i === len - 1) {
                        border = "";
                    }
                    const device = `
                        <div class="card-block ${border} py-4">
                            <div class="row align-items-center justify-content-center">
                                <div class="col">
                                    <h3 class="m-0 f-w-300"><a href="/settings/device_settings?id=${deviceId}" class="device_link">${deviceName}<a></h3>
                                </div>
                                <div class="col-auto">
                                    <label id="${deviceId}" class="badge badge-pill mt-2 px-3 py-2 theme-bg2 text-white f-14 f-w-400 float-right">
                                        <span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span>
                                        <span>${status}</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    `;
                    $("#devices").append(device);
                }
            }
        });
    }
    getDevices();

    function getDevicesStatus() {
        // Called every 10 seconds
        return new Promise((resolve, reject) => {
            $.ajax({
                url: "/api/system/devices/status",
                type: 'GET',
                data: {},
                contentType: 'application/json;charset=UTF-8',
                success: function (data) {
                    resolve(data);
                },
                error: function (error) {
                    reject(error);
                }
            });
            setTimeout(getDevicesStatus, 10000);
        });
    }

    getDevicesStatus()
        // Update device status
        .then((data) => {
            const devices = data["devices"];
            for (var i = 0, len = devices.length; i < len; i++) {
                const deviceId = devices[i]["id"];
                let status = "Offline";
                let statusColor = "bg-danger";
                if (devices[i]["connected"]) {
                    status = "Online";
                    statusColor = "theme-bg";
                }
                $("#" + deviceId).text(status).removeClass("theme-bg2").addClass(statusColor);
            }
        })
        .catch((error) => {
            console.log(error);
        })

    function bytesToGigabytes(bytes) {
        return bytes / 1024 / 1024 / 1024;
    }

});