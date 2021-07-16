import Toast from "./Toast.js";

let intervalSec;

// classes/EffectManager.js
export default class EffectManager {
    constructor(currentDevice) {
        this.currentDevice = currentDevice ? currentDevice : undefined;

        $.ajax({
            url: "/api/resources/effects",
            data: {}
        }).done((data) => {
            this.allEffects = Object.keys(data.special).concat(Object.keys(data.music), Object.keys(data.non_music))
            // Listen for effect change on click
            this.allEffects.forEach(effect => {
                $("#" + effect).on('click', () => {
                    this.switchEffect(effect);
                });
            });
        })

        // Hardcoded all_devices for now. Timer.js is unstable with multiple devices.
        // This is still buggy because if you manually select a different device,
        // the timer will continue instead of stopping.
        Promise.all([
            $.ajax({
                url: "/api/settings/effect",
                data: {
                    "device": "all_devices",
                    "effect": "effect_random_cycle",
                }
            }).done((data) => {
                intervalSec = data.settings.interval;
                this.timer = this.initTimerWorker();
            }),

        ]).then(response => {

        }).catch((response) => {
            new Toast(JSON.stringify(response, null, '\t')).error();
        });
    }

    switchEffect(effect) {
        if (effect.length > 0) {

            if (effect == 'effect_random_cycle') {
                const effectCycleActive = sessionStorage.getItem('effect_cycle_active');
                if (!effectCycleActive) {
                    this.timer.postMessage({
                        seconds: intervalSec,
                        status: 'start'
                    });
                    sessionStorage.setItem('effect_cycle_active', true);
                    $("#effect_random_cycle").css("box-shadow", "inset 0 0 0 3px #3f4d67")
                }
            } else {
                const effectCycleActive = sessionStorage.getItem('effect_cycle_active');
                if (effectCycleActive) {
                    this.timer.postMessage({
                        seconds: 0,
                        status: 'stop'
                    });
                    sessionStorage.clear();
                }
                $("#effect_random_cycle > div > p").text("Random Cycle");
                $("#effect_random_cycle").css("box-shadow", "none")
            }

            $.ajax({
                url: "/api/effect/active",
                type: "POST",
                data: JSON.stringify({ "device": this.currentDevice.id, "effect": effect }),
                contentType: 'application/json;charset=UTF-8'
            }).done((data) => {
                // UI and State Updates should be here
                // this could cause Problems later
                this.currentDevice.setActiveEffect(data.effect);
            }).fail((data) => {
                new Toast('Unable to set effect. Error: ' + JSON.stringify(data, null, '\t')).error();
            });
        }
    }

    initTimerWorker() {
        let timer = new Worker('/static/assets/js/timer.js');

        // Get messages from timer worker
        timer.onmessage = (event) => {
            var sec = event.data;
            sessionStorage.setItem('seconds', sec);
            $("#effect_random_cycle > div > p").text(`Random Cycle (${formatTimer(sec)})`);
            if (sec <= 0) {
                sessionStorage.clear();
                $("#effect_random_cycle")[0].click();
            }
        };

        // Restore timer if it was running while page reloaded
        var effectCycleActive = sessionStorage.getItem('effect_cycle_active');
        if (effectCycleActive) {
            $("#effect_random_cycle").css("box-shadow", "inset 0 0 0 3px #3f4d67")
            var sec = sessionStorage.getItem('seconds');
            if (sec <= 0 || sec == null) {
                sec = intervalSec;
                sessionStorage.setItem('seconds', sec);
            }
            timer.postMessage({
                seconds: sec,
                status: 'start'
            });
        }
        return timer;
    }

}

function formatTimer(time) {
    let hrs = ~~(time / 3600);
    let mins = ~~((time % 3600) / 60);
    let secs = ~~time % 60;

    let result = "";
    if (hrs > 0) {
        result += `${hrs}:${(mins < 10 ? "0" : "")}`
    }
    result += `${mins}:${(secs < 10 ? "0" : "")}`
    result += secs;
    return result;
}
