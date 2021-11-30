import Toast from "./Toast.js";


// classes/EffectManager.js
export default class EffectManager {
    constructor(currentDevice) {
        this.currentDevice = currentDevice ? currentDevice : undefined;
        this.timer = new easytimer.Timer();
        this.intervalSec;

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

        // Hardcoded all_devices for now.
        // If you manually select a different device,
        // the timer will continue instead of stopping.
        Promise.all([
            $.ajax({
                url: "/api/settings/effect",
                data: {
                    "device": "all_devices",
                    "effect": "effect_random_cycle",
                }
            }).done((data) => {
                this.intervalSec = data.settings.interval;
                if (sessionStorage.getItem('interval') != this.intervalSec) {
                    // If interval changed while timer was running, restart timer with new interval
                    sessionStorage.setItem('seconds', this.intervalSec);
                }
                sessionStorage.setItem('interval', this.intervalSec);
                this.initEasyTimer();
            }),

        ]).then(response => {

        }).catch((response) => {
            new Toast(JSON.stringify(response, null, '\t')).error();
        });
    }

    switchEffect(effect) {
        if (effect.length > 0) {

            const effectCycleActive = sessionStorage.getItem('effect_cycle_active');
            if (effect == 'effect_random_cycle') {
                if (!effectCycleActive) {
                    this.timer.start({ countdown: true, startValues: { seconds: this.intervalSec + 1 } });
                    sessionStorage.setItem('effect_cycle_active', true);
                }
            } else {
                if (effectCycleActive) {
                    this.timer.stop();
                    sessionStorage.removeItem('effect_cycle_active');
                }
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
                console.log(JSON.stringify(data, null, '\t'));
                new Toast("Error while setting effect.").error();
            });
        }
    }

    initEasyTimer() {
        this.timer.on('started', () => {
            $("#effect_random_cycle").css("box-shadow", "inset 0 0 0 3px #3f4d67");
        });

        this.timer.on('secondsUpdated', () => {
            sessionStorage.setItem('seconds', this.timer.getTotalTimeValues().seconds);
            $("#effect_random_cycle > div > p").text(`Random Cycle (${this.timer.getTimeValues().toString(['minutes', 'seconds'])})`);
        });

        this.timer.on('targetAchieved', () => {
            this.switchEffect("effect_random_cycle");
            $("#effect_random_cycle > div > p").text(`Random Cycle (${this.timer.getTimeValues().toString(['minutes', 'seconds'])})`);
            this.timer.start({ countdown: true, startValues: { seconds: this.intervalSec + 1 } });
        });

        this.timer.on('stopped', () => {
            $("#effect_random_cycle > div > p").text("Random Cycle");
            $("#effect_random_cycle").css("box-shadow", "0 1px 20px 0 rgb(69 90 100 / 8%)");
        });

        // Restore timer if it was running while page reloaded
        const effectCycleActive = sessionStorage.getItem('effect_cycle_active');
        if (effectCycleActive) {
            let sec = parseInt(sessionStorage.getItem('seconds'));
            console.log(sessionStorage.getItem('seconds'), sessionStorage.getItem('interval'))
            if (!Number.isInteger(sec)) {
                sec = this.intervalSec;
                sessionStorage.setItem('seconds', sec);
            }
            this.timer.start({ countdown: true, startValues: { seconds: sec + 1 } });
        }
    }
}
