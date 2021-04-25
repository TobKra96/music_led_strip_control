$(document).ready(function () {

    function getSystemInfoPerformance() {
        // Called every 10 seconds
        $.ajax("/GetSystemInfoPerformance").done((data) => {
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
            if ($("#network_interfaces").children().length - 1 < Object.keys(networkInterfaces).length) {
                for (var i = 0, len = Object.keys(networkInterfaces).length; i < len; i++) {
                    const interfaceName = Object.keys(networkInterfaces)[i];
                    const interfaceAddress = networkInterfaces[interfaceName]["address"];
                    const interfaceNetmask = networkInterfaces[interfaceName]["netmask"];
                    let border = "border-bottom";
                    if (i === len - 1) {
                        border = "";
                    }
                    const interfaceCard = `
                        <div id="${interfaceName}" class="card-block ${border}">
                            <div class="row">
                                <div class="col-auto">
                                    <label class="badge badge-pill px-3 py-2 theme-bg2 text-white f-14 f-w-400">${interfaceName}</label>
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
        });
        setTimeout(getSystemInfoPerformance, 10000);
    }
    getSystemInfoPerformance();

    function getSystemInfoTemperature() {
        // Called every 20 seconds
        $.ajax("/GetSystemInfoTemperature").done((data) => {
            const cpuTemp = data["system"]["raspi"]["celsius"];
            $("#cpu_temperature").text(cpuTemp + "°C");
            $("#cpu_temperature_progress").css("width", cpuTemp + "%");
        });
        setTimeout(getSystemInfoTemperature, 20000);
    }
    getSystemInfoTemperature()

    function getSystemInfoServices() {
        // Called once on page load
        $.ajax("/GetSystemInfoServices").done((data) => {
            const services = data["system"];
            for (var i = 0, len = Object.keys(services).length; i < len; i++) {
                const serviceName = Object.keys(services)[i];
                const serviceStatus = services[serviceName]["running"];
                let status = "Stopped";
                let statusColor = "bg-danger";
                if (serviceStatus) {
                    status = "Running";
                    statusColor = "theme-bg";
                }
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
                                <label class="badge badge-pill mt-2 px-3 py-2 ${statusColor} text-white f-14 f-w-400 float-right">${status}</label>
                            </div>
                        </div>
                    </div>
                `;
                $("#services").append(service);
            }
        });
    }
    getSystemInfoServices()

    function getDevices2() {
        $.ajax("/GetDevices2").done((devices) => {
            if ($("#devices").children().length - 1 < devices.length) {
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
                                    <h3 class="m-0 f-w-300">${deviceName}</h3>
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
    getDevices2();

    function getSystemInfoDeviceStatus() {
        // Called every 10 seconds
        return new Promise((resolve, reject) => {
            $.ajax({
                url: "/GetSystemInfoDeviceStatus",
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
            setTimeout(getSystemInfoDeviceStatus, 10000);
        });
    }

    getSystemInfoDeviceStatus()
        .then((devices) => {
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