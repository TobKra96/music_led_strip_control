import { Device } from "./classes/Device.js";

/* Effect Handling */

function getRandomEffect(effects, activeEffect) {
    do {
        var randomEffect = effects[Math.floor(Math.random() * effects.length)];
    } while(randomEffect === activeEffect)
    return randomEffect;
}
function switchEffect(e) {
    let newActiveEffect = "";
    let BreakException = {};

    // wat (pls refactor)
    try {
        var path = e.path || (e.composedPath && e.composedPath());
        path.forEach(element => {
            if (element.classList != null) {
                if (element.classList.contains("dashboard_effect")) {
                    newActiveEffect = element.id;
                    throw BreakException;
                }
            }
        });
    }
    catch (e) {
        if (e !== BreakException) throw e;
    }
    // wat (pls refactor)

    if (newActiveEffect.length > 0) {
        console.log(newActiveEffect + " was clicked.");

        if (newActiveEffect == 'effect_random_cycle') {
            const effectCycleActive = sessionStorage.getItem('effect_cycle_active');
            if (!effectCycleActive) {
                timer.postMessage({
                    seconds: hardcodedSec,
                    status: 'start'
                });
                sessionStorage.setItem('effect_cycle_active', true);
            }
            newActiveEffect = getRandomEffect(allEffects, currentDevice.activeEffect);
        } else {
            timer.postMessage({
                seconds: 0,
                status: 'stop'
            });
            sessionStorage.clear();
            $("#effect_random_cycle > div > p").text("Random Cycle");
        }

        if (newActiveEffect == 'effect_random_non_music') {
            newActiveEffect = getRandomEffect(allNonMusicEffects, currentDevice.activeEffect);
        }
        if (newActiveEffect == 'effect_random_music') {
            newActiveEffect = getRandomEffect(allMusicEffects, currentDevice.activeEffect);
        }
        $.ajax({
            url: "/SetActiveEffect",
            type: "POST",
            data: JSON.stringify({ "device": currentDevice.id, "effect": newActiveEffect }),
            contentType: 'application/json;charset=UTF-8'
        }).done((data) => {
            currentDevice.setActiveEffect(newActiveEffect);
            console.table("Effect set successfully. Response:\n\n" + JSON.stringify(data, null, '\t'));
        }).fail((data) => {
            console.log("Error while setting effect. Error: " + data.responseText);
        });
    }
}

// Listen for effect change on click
document.getElementById("dashboard-item-list").addEventListener("click", function (e) {
    switchEffect(e);
});

function initTimerWorker() {
    timer = new Worker('/static/assets/js/timer.js');

    // Get messages from timer worker
    timer.onmessage = (event) => {
        var sec = event.data;
        sessionStorage.setItem('seconds', sec);
        $("#effect_random_cycle > div > p").text("Random Cycle (" + sec + "s)");
        if (sec <= 0) {
            sessionStorage.clear();
            $("#effect_random_cycle")[0].click();
        }
    };
    
    // Restore timer if it was running while page reloaded
    var effectCycleActive = sessionStorage.getItem('effect_cycle_active');
    if (effectCycleActive) {
        var sec = sessionStorage.getItem('seconds');
        if (sec <= 0) {
            sec = hardcodedSec;
            sessionStorage.setItem('seconds', sec);
        }
        timer.postMessage({
            seconds: sec,
            status: 'start'
        });
    }
}

// Global Variables

// Start with Fake Device
const devices = [new Device("all_devices", "All Devices")];
let currentDevice = devices[0];
let timer;
const hardcodedSec = 10;
// todo: refactor server-side
const allNonMusicEffects = $("#dashboard-list-none-music > div > div").map(function() { return this.id }).toArray();
const allMusicEffects = $("#dashboard-list-music > div > div").map(function() { return this.id }).toArray();
const allEffects = allNonMusicEffects.concat(allMusicEffects);

// Init and load all settings
$(document).ready(function () {

    $.ajax({ url: "/GetDevices" }).done((data) => {

        // data = { device_0: "devicename1", device_1: "devicename2" }
        // todo: return anon Objects from Endpoint

        // parse response into device Objects
        Object.keys(data).forEach(device_key => {
            devices.push(new Device(device_key, data[device_key]));
        });

        // Subtract the fake Device
        $('#device_count').text(devices.length-1);

        // Restore last selected device on reload
        let lastDevice = devices.find(device => device.id === localStorage.getItem("lastDevice"));
        if(lastDevice instanceof Device) {
            currentDevice = lastDevice;
        } else {
            // Fallback to all_devices
            currentDevice = devices[0];
        }
        // Async function
        currentDevice.getActiveEffect();

        // Build Device Tab
        devices.forEach(device => {
            // todo: do it server side
            const active = currentDevice.id === device.id ? " active" : "";
            const link = document.createElement("a");
            link.classList = "nav-link" + active;
            link.innerHTML = device.name;
            link.href = "#pills-0";
            link.role = "tab";
            link.setAttribute("data-toggle", "pill")
            link.setAttribute("aria-controls", "pills-0")
            link.setAttribute("aria-selected", "false")
            link.addEventListener('click', () => {
                currentDevice = device;
                localStorage.setItem('lastDevice', device.id);
                // Async function
                device.getActiveEffect();
            });

            const li = document.createElement("li");
            li.className = "nav-item device_item";
            li.appendChild(link)

            document.getElementById("deviceTabID").appendChild(li);

        });
     });

    initTimerWorker();

});