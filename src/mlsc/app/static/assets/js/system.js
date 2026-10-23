import { api } from "./classes/Api.js";
import { events } from "./classes/Events.js";
import Toast from "./classes/Toast.js";

$(() => {
    // Do not collapse accordion when clicking on body.
    $(".collapse").on('click', e => {
        e.stopPropagation();
    });

    // Restore system status card positions on reload.
    const order = JSON.parse(localStorage.getItem('order'));
    if (order) {
        Object.entries(order).forEach(([column, cards]) => {
            cards.forEach((card) => {
                const $target = $(".connectedSortable").find('#' + card);
                $target.appendTo($('#' + column));
            });
        });
    }

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

    /**
     * Update the system status cards with the performance data.
     * @param {object} data
     */
    const showPerformance = (data) => {
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
    }

    /**
     * Update the system status cards with the temperature data.
     * @param {object} data
     */
    const showTemperature = (data) => {
        const cpuTempC = data.system.raspi.celsius;
        const cpuTempF = data.system.raspi.fahrenheit;
        if (cpuTempC === 0 && cpuTempF === 0) {
            $("#cpu_temperature").html("N/A");
        } else {
            $("#cpu_temperature").html(cpuTempC + "\u00b0C&nbsp;&nbsp;/&nbsp;&nbsp;" + cpuTempF + "\u00b0F");
            $("#cpu_temperature_progress").css("width", cpuTempC + "%");
        }
    }

    // The server pushes performance and temperature every few seconds while this page is open.
    events.on("system.stats", (stats) => {
        showPerformance(stats);
        showTemperature(stats);
    });

    // Show the current values at once, without waiting for the first push.
    api.get("/system/performance").then(showPerformance).catch(() => {
        new Toast("Unable to reach the server.").error();
    });
    api.get("/system/temperature").then(showTemperature).catch(() => {});

    /**
     * Call API once to get the status of the services.
     */
    const getServices = () => {
        api.get("/system/services").then((data) => {
            data.services.forEach((service, index, array) => {
                let status = "Stopped";
                let statusColor = "bg-danger";
                if (service.not_found) {
                    status = "Not Found";
                }
                if (service.running) {
                    status = "Running";
                    statusColor = "theme-bg";
                }
                let border;
                index === array.length - 1 ? border = "" : border = "border-bottom";
                const serviceCard = `
                    <div class="card-block ${border} py-4">
                        <div class="row align-items-center justify-content-center">
                            <div class="col">
                                <h3 class="m-0 f-w-300">${service.name}</h3>
                            </div>
                            <div class="col-auto">
                                <label id="${service.name}" class="badge badge-pill mt-2 px-3 py-2 ${statusColor} text-white f-14 f-w-400 float-right">
                                    <span>${status}</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `;
                $("#services").append(serviceCard);
            });
        }).catch(() => {});
    }
    getServices();

    /**
     * Show the online state of the devices. A card is created for each device that has none yet.
     * @param {{devices: Array.<{id: string, name: string, connected: boolean}>}} data
     */
    const showDeviceStatus = (data) => {
        data.devices.forEach((device, index, array) => {
            if (!document.getElementById(device.id)) {
                let border;
                index === array.length - 1 ? border = "" : border = "border-bottom";
                const deviceCard = `
                    <div class="card-block ${border} py-4">
                        <div class="row align-items-center justify-content-center">
                            <div class="col">
                                <h3 class="m-0 f-w-300"><a href="/settings/device_settings?id=${device.id}" class="device_link">${device.name}</a></h3>
                            </div>
                            <div class="col-auto">
                                <label id="${device.id}" class="badge badge-pill mt-2 px-3 py-2 theme-bg2 text-white f-14 f-w-400 float-right"></label>
                            </div>
                        </div>
                    </div>
                `;
                $("#devices").append(deviceCard);
            }

            const status = device.connected ? "Online" : "Offline";
            const statusColor = device.connected ? "theme-bg" : "bg-danger";
            $("#" + device.id).text(status).removeClass("theme-bg theme-bg2 bg-danger").addClass(statusColor);
        });
    }

    // The server pushes the device status whenever it changed while this page is open.
    events.on("device.status", showDeviceStatus);
    api.get("/system/device-status").then(showDeviceStatus).catch(() => {});

    /**
     * Call API once to get software version data and update version card.
     */
    const getVersion = () => {
        api.get("/system/version").then((data) => {
            data.versions.forEach((software, index, array) => {
                const statusColor = "theme-bg2";
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
    getVersion();

    /**
     * Convert bytes to gigabytes.
     * @param {number} bytes
     * @return {number}
     */
    const bytesToGigabytes = bytes => {
        return bytes / 1024 / 1024 / 1024;
    }

});
