// classes/EffectManager.js
export default class EffectManager {
    constructor() {
        // todo: refactor server-side
        this.nonMusicEffects = $("#dashboard-list-none-music > div > div").map(function() { return this.id }).toArray();
        this.musicEffects = $("#dashboard-list-music > div > div").map(function() { return this.id }).toArray();
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

    get allEffects () {
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
        } while(randomEffect === activeEffect)
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
                    $("#effect_random_cycle > div").addClass("border border-secondary");
                }
            } else {
                timer.postMessage({
                    seconds: 0,
                    status: 'stop'
                });
                sessionStorage.clear();
                $("#effect_random_cycle > div > p").text("Random Cycle");
                $("#effect_random_cycle > div").removeClass("border border-secondary");
            }
            
            // pick random effect based on type
            if(effect == "effect_random_cycle" || effect == "effect_random_non_music" || effect == "effect_random_music") {
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
                $("#alerts").append(`
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>(`+ new Date().toLocaleTimeString() +`) Error: </strong> `+data.responseText+`
                <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                  <span aria-hidden="true">&times;</span>
                </button>
                </div>`);
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