document.addEventListener("DOMContentLoaded", () => {

    // Restore active effect button on reload
    let savedEffectId = localStorage.getItem("effectId");
    let savedEffectButton = document.getElementById(savedEffectId)

    if (savedEffectButton) {
        $(savedEffectButton).addClass('dashboard_effect_active');
    }

    // Set selected effect button as active
    let effectButton = $('.dashboard_effect')

    if (effectButton) {
        effectButton.click(function() {
            effectButton.removeClass('dashboard_effect_active');
            $(this).addClass('dashboard_effect_active');
            localStorage.setItem('effectId', $(this).attr('id'));
        });
    }

});