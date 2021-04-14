// classes/EffectManager.js
export default class EffectManager {
    constructor() {
        // todo: refactor server-side
        this.nonMusicEffects = $("#dashboard-list-none-music > div > div").map(function () { return this.id }).toArray();
        this.musicEffects = $("#dashboard-list-music > div > div").map(function () { return this.id }).toArray();
        this.specialEffects = $("#dashboard-list-special > div > div").map(function () { return this.id }).toArray();
        this.currentDevice;

        // Listen for effect change on click
        this.allEffects.forEach(effect => {
            $("#" + effect).on('click', () => {
                this.switchEffect(effect);
            });
        });

        initTimerWorker();
    }

    get allEffects() {
        return this.nonMusicEffects.concat(this.musicEffects, this.specialEffects)
    }

    get allLightEffects() {
        return this.nonMusicEffects.concat(this.musicEffects)
    }

    getRandomEffect(type, activeEffect) {
        let pool, randomEffect;

        if (type == 'effect_random_non_music') {
            pool = this.nonMusicEffects;
        } else if (type == 'effect_random_music') {
            pool = this.musicEffects;
        } else {
            pool = this.allLightEffects;
        }

        do {
            randomEffect = pool[Math.floor(Math.random() * pool.length)];
        } while (randomEffect === activeEffect)
        return randomEffect;
    }

    switchEffect(effect) {
        if (effect.length > 0) {

            if (effect == 'effect_random_cycle') {
                const effectCycleActive = sessionStorage.getItem('effect_cycle_active');
                if (!effectCycleActive) {
                    timer.postMessage({
                        seconds: hardcodedSec,
                        status: 'start'
                    });
                    sessionStorage.setItem('effect_cycle_active', true);
                    $("#effect_random_cycle > div").css("box-shadow", "inset 0 0 0 3px #3f4d67")
                }
            } else {
                const effectCycleActive = sessionStorage.getItem('effect_cycle_active');
                if (effectCycleActive) {
                    timer.postMessage({
                        seconds: 0,
                        status: 'stop'
                    });
                    sessionStorage.clear();
                }
                $("#effect_random_cycle > div > p").text("Random Cycle");
                $("#effect_random_cycle > div").css("box-shadow", "none")
            }

            // pick random effect based on type
            if (effect == "effect_random_cycle" || effect == "effect_random_non_music" || effect == "effect_random_music") {
                effect = this.getRandomEffect(effect, this.currentDevice.activeEffect);
            }

            $.ajax({
                url: "/SetActiveEffect",
                type: "POST",
                data: JSON.stringify({ "device": this.currentDevice.id, "effect": effect }),
                contentType: 'application/json;charset=UTF-8'
            }).done((data) => {
                // UI and State Updates should be here
                // this could cause Problems later
            }).fail((data) => {
                $(".toast_block").append(`
                    <div class="toast" style="min-width: 250px;" role="alert" aria-live="assertive" aria-atomic="true">
                        <div class="toast-header">
                            <strong class="mr-auto text-danger"><i class="feather icon-alert-triangle"></i> Error</strong>
                            <small class="text-muted">`+ new Date().toLocaleTimeString('en-GB') + `</small>
                            <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
                                <span aria-hidden="true" class="feather icon-x"></span>
                            </button>
                        </div>
                        <div class="toast-body">
                            Unable to set effect.<br>Error: ` + data.responseText + `
                        </div>
                    </div>
                `);

                $('.toast').toast({
                    delay: 5000
                })
                $('.toast').toast('show')
                $('.toast').on('hidden.bs.toast', function () {
                    $(this).remove()
                })
            });
            // update UI without waiting for a response
            this.currentDevice.setActiveEffect(effect);
        }
    }

}

let timer;
const hardcodedSec = 10;

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
        $("#effect_random_cycle > div").css("box-shadow", "inset 0 0 0 3px #3f4d67")
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