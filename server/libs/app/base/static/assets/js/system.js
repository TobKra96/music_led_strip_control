import Toast from "./classes/Toast.js";

$(document).ready(function () {
    // Do not collapse accordion when clicking on body
    $(".collapse").on('click', (e) => {
        e.stopPropagation();
    });

    // Restore system status card positions on reload
    const order = JSON.parse(localStorage.getItem('order'));
    if (order) {
        Object.entries(order).forEach(([column, cards]) => {
            cards.forEach((card) => {
                let $target = $(".connectedSortable").find('#' + card);
                $target.appendTo($('#' + column));
            });
        });
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

    /**
     * Call API to get performance data and update system status cards.
     */
    function getPerformance() {
        // Called every 10 seconds
        $.ajax("/api/system/performance").done((data) => {
            const cpuUsage = data.system.cpu_info.percent;
            $("#cpu_usage_percent").text(cpuUsage + "%");
            $("#cpu_usage_progress").css("width", cpuUsage + "%");

            const cpuFreq = data.system.cpu_info.frequency;
            $("#cpu_freq").text(cpuFreq / 1000 + " GHz");

            const memoryUsage = data.system.memory_info.percent;
            $("#memory_usage_percent").text(memoryUsage + "%");
            $("#memory_usage_progress").css("width", memoryUsage + "%");

            const memoryUsed = data.system.memory_info.used;
            $("#memory_used").text(bytesToGigabytes(memoryUsed).toFixed(1) + " GB");

            const memoryTotal = data.system.memory_info.total;
            $("#memory_total").text(bytesToGigabytes(memoryTotal).toFixed(1) + " GB");

            const diskUsage = data.system.disk_info.percent;
            $("#disk_usage_percent").text(diskUsage + "%");
            $("#disk_usage_progress").css("width", diskUsage + "%");

            const diskUsed = data.system.disk_info.used;
            $("#disk_used").text(bytesToGigabytes(diskUsed).toFixed(1) + " GB");

            const diskTotal = data.system.disk_info.total;
            $("#disk_total").text(bytesToGigabytes(diskTotal).toFixed(1) + " GB");

            const networkInterfaces = data.system.network_info;
            if ($("#network_interfaces").children().length < networkInterfaces.length) {
                networkInterfaces.forEach((netInterface, index, array) => {
                    let border;
                    index === array.length - 1 ? border = "" : border = "border-bottom";
                    const interfaceCard = `
                        <div class="card-block ${border}">
                            <div class="row">
                                <div class="col-auto">
                                    <label class="badge badge-pill px-3 py-2 mr-2 theme-bg2 text-white f-14 f-w-400">
                                        <span>${netInterface.name}</span>
                                    </label>
                                    <label class="badge badge-pill px-3 py-2 mr-2 theme-bg2 text-white f-14 f-w-400">
                                        <i class="feather icon-arrow-down text-c-green"></i>
                                        <span>${bytesToGigabytes(netInterface.bytes_recv).toFixed(1)} GB</span>
                                    </label>
                                    <label class="badge badge-pill px-3 py-2 theme-bg2 text-white f-14 f-w-400">
                                        <i class="feather icon-arrow-up text-c-yellow"></i>
                                        <span>${bytesToGigabytes(netInterface.bytes_sent).toFixed(1)} GB</span>
                                    </label>
                                </div>
                            </div>
                            <h3 class="mt-3 f-w-300">${netInterface.address}</h3>
                            <h6 class="text-muted mt-2 mb-0 text-uppercase">address</h6>
                            <h3 class="mt-3 f-w-300">${netInterface.netmask}</h3>
                            <h6 class="text-muted mt-2 mb-0 text-uppercase">netmask</h6>
                        </div>
                    `;
                    $("#network_interfaces").append(interfaceCard);
                });
            }
        }).catch((error) => {
            new Toast("Unable to reach the server.").error();
        });
        setTimeout(getPerformance, 10000);
    }
    getPerformance();

    /**
     * Call API to get temperature data and update system status cards.
     */
    function getTemperature() {
        // Called every 20 seconds
        $.ajax("/api/system/temperature").done((data) => {
            const cpuTempC = data.system.raspi.celsius;
            const cpuTempF = data.system.raspi.fahrenheit;
            $("#cpu_temperature").html(cpuTempC + "°C&nbsp;&nbsp;/&nbsp;&nbsp;" + cpuTempF + "°F");
            $("#cpu_temperature_progress").css("width", cpuTempC + "%");
        });
        setTimeout(getTemperature, 20000);
    }
    getTemperature();

    /**
     * Call API to get services data and update service status card as `Checking`.
     */
    function getServices() {
        // Preload services
        $.ajax("/api/system/services").done((data) => {
            data.services.forEach((service, index, array) => {
                let status = "Checking";
                let statusColor = "theme-bg2";
                let border;
                index === array.length - 1 ? border = "" : border = "border-bottom";
                const serviceCard = `
                    <div class="card-block ${border} py-4">
                        <div class="row align-items-center justify-content-center">
                            <div class="col">
                                <h3 class="m-0 f-w-300">${service}</h3>
                            </div>
                            <div class="col-auto">
                                <label id="${service}" class="badge badge-pill mt-2 px-3 py-2 ${statusColor} text-white f-14 f-w-400 float-right">
                                    <span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span>
                                    <span>${status}</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `;
                $("#services").append(serviceCard);
            });

            getServicesStatus();
        });
    }
    getServices();

    /**
     * Call API to get status of services.
     */
    function getServicesStatus() {
        // Called once on page load
        $.ajax("/api/system/services/status").done((data) => {
            data.services.forEach(service => {
                let status = "Stopped";
                if (service.not_found) {
                    status = "Not Found";
                }
                let statusColor = "bg-danger";
                if (service.running) {
                    status = "Running";
                    statusColor = "theme-bg";
                }
                $("#" + service.name).text(status).removeClass("theme-bg2").addClass(statusColor);
            });
        }).catch((xhr) => {
            console.log(xhr.responseText);
        })
    }

    /**
     * Call API to get devices data and update device card as `Checking`.
     */
    function getDevices() {
        // Preload devices
        $.ajax("/api/system/devices").done((devices) => {
            if ($("#devices").children("div").length < devices.length) {
                devices.forEach((device, index, array) => {
                    let status = "Checking";
                    let border;
                    index === array.length - 1 ? border = "" : border = "border-bottom";
                    const deviceCard = `
                        <div class="card-block ${border} py-4">
                            <div class="row align-items-center justify-content-center">
                                <div class="col">
                                    <h3 class="m-0 f-w-300"><a href="/settings/device_settings?id=${device.id}" class="device_link">${device.name}<a></h3>
                                </div>
                                <div class="col-auto">
                                    <label id="${device.id}" class="badge badge-pill mt-2 px-3 py-2 theme-bg2 text-white f-14 f-w-400 float-right">
                                        <span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span>
                                        <span>${status}</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    `;
                    $("#devices").append(deviceCard);
                });
            }

            getDevicesStatus();
        });
    }
    getDevices();

    /**
     * Call API to get status of devices.
     */
    function getDevicesStatus() {
        // Called every 10 seconds
        $.ajax("/api/system/devices/status").done((data) => {
            data.devices.forEach(device => {
                let status = "Offline";
                let statusColor = "bg-danger";
                if (device.connected) {
                    status = "Online";
                    statusColor = "theme-bg";
                }
                $("#" + device.id).text(status).removeClass("theme-bg theme-bg2").addClass(statusColor);
            });
        }).catch((xhr) => {
            console.log(xhr.responseText);
        });
        setTimeout(getDevicesStatus, 10000);
    }

    /**
     * Call API to get software version data and update version card.
     */
    function getVersion() {
        $.ajax("/api/system/version").done((data) => {
            data.versions.forEach((software, index, array) => {
                let statusColor = "theme-bg2";
                let border;
                index === array.length - 1 ? border = "" : border = "border-bottom";
                const versionCard = `
                    <div class="card-block ${border} py-4">
                        <div class="row align-items-center justify-content-center">
                            <div class="col">
                                <h3 class="m-0 f-w-300">${software.name}</h3>
                            </div>
                            <div class="col-auto">
                                <label id="${software.name}" class="badge badge-pill mt-2 px-3 py-2 ${statusColor} text-white f-14 f-w-400 float-right">
                                    <span>${software.version}</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `;
                $("#version").append(versionCard);
            });
        });
    }
    getVersion()

    /**
     * Convert bytes to gigabytes.
     * @param {number} bytes
     * @return {number}
     */
    function bytesToGigabytes(bytes) {
        return bytes / 1024 / 1024 / 1024;
    }

});
