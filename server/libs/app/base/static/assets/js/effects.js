document.addEventListener("DOMContentLoaded", () => {

    // Set effect slider values
    function setSliderValue(sliderId, outputId) {
        let slider = document.getElementById(sliderId)
        let output = document.getElementById(outputId)

        if (slider && output) {
            output.innerHTML = slider.value;

            slider.oninput = function() {
                output.innerHTML = this.value;
            }
        }
    }

    const sliderIdList = [
        'speed', 'bubble_length', 'bubble_repeat', 'blur', 'star_ascending_speed',
        'star_rising_speed', 'star_descending_speed', 'stars_count', 'stars_length',
        'pendulum_length', 'rods_length', 'rods_distance', 'decay', 'high_speed',
        'mid_speed', 'low_speed', 'lows_multiplier', 'mids_multiplier', 'high_multiplier',
        'subbass_speed', 'bass_speed', 'lowmid_speed', 'mid_speed', 'uppermid_speed',
        'presence_speed', 'brilliance_speed', 'subbass_multiplier', 'bass_multiplier',
        'lowmid_multiplier', 'mid_multiplier', 'uppermid_multiplier', 'presence_multiplier',
        'brilliance_multiplier', 'r_multiplier', 'g_multiplier', 'b_multiplier', 'scale',
        'roll_speed', 'resolution', 's_count', 'star_length', 'wipe_len', 'wipe_speed',
        'slider_length', 'bar_speed', 'bar_length', 'spectrum_count', 'bars_in_same_direction'
    ]

    const outputIdList = [
        'speedNum', 'bubbleLengthNum', 'bubbleRepeatNum', 'blurNum', 'starAscendingSpeedNum',
        'starRisingSpeedNum', 'starDescendingSpeedNum', 'starsCountNum', 'starsLengthNum',
        'pendulumLengthNum', 'rodsLengthNum', 'rodsDistanceNum', 'decayNum', 'highSpeedNum',
        'midSpeedNum', 'lowSpeedNum', 'lowsMultiplierNum', 'midsMultiplierNum', 'highMultiplierNum',
        'subbassSpeedNum', 'bassSpeedNum', 'lowmidSpeedNum', 'midSpeedNum', 'uppermidSpeedNum',
        'presenceSpeedNum', 'brillianceSpeedNum', 'subbassMultiplierNum', 'bassMultiplierNum',
        'lowmidMultiplierNum', 'midMultiplierNum', 'uppermidMultiplierNum', 'presenceMultiplierNum',
        'brillianceMultiplierNum', 'rMultiplierNum', 'gMultiplierNum', 'bMultiplierNum', 'scaleNum',
        'rollSpeedNum', 'resolutionNum', 'sCountNum', 'starLengthNum', 'wipeLenNum', 'wipeSpeedNum',
        'sliderLengthNum', 'barSpeedNum', 'barLengthNum', 'spectrumCountNum', 'barsInSameDirectionNum'
    ]

    sliderIdList.forEach((sliderId, index) => {
        setSliderValue(sliderId, outputIdList[index])
    });

    // Parse color selection
    let parent = document.querySelector('#color_picker');
    let input = document.querySelector('#color_input');

    if (parent && input) {
        const pickr = Pickr.create({
            el: parent,
            theme: 'monolith',
            default: 'rgb(255,255,255)',
            position: 'left-middle',
            lockOpacity: false,
            comparison: false,
            useAsButton: true,

            swatches: [
                'rgb(244, 67, 54)',
                'rgb(233, 30, 99)',
                'rgb(156, 39, 176)',
                'rgb(103, 58, 183)',
                'rgb(63, 81, 181)',
                'rgb(33, 150, 243)',
                'rgb(3, 169, 244)',
                'rgb(0, 188, 212)',
                'rgb(0, 150, 136)',
                'rgb(76, 175, 80)',
                'rgb(139, 195, 74)',
                'rgb(205, 220, 57)',
                'rgb(255, 235, 59)',
                'rgb(255, 193, 7)'
            ],

            components: {
                hue: true
            }
        }).on('init', pickr => {
            let newColor = pickr.getSelectedColor().toRGBA().toString(0).replace(', 1)', ')').replace('rgba', 'rgb');
            parent.style.background = newColor;
            input.value = newColor;
        }).on('change', color => {
            let newColor = color.toRGBA().toString(0).replace(', 1)', ')').replace('rgba', 'rgb');
            parent.style.background = newColor;
            input.value = newColor;
        })

        input.addEventListener('input', () => {
            let rgb = input.value.replace(/[^\d,]/g, '').split(',');
            let red = parseInt(rgb[0]);
            let green = parseInt(rgb[1]);
            let blue = parseInt(rgb[2]);
            if (red > 255 || red < 0 || isNaN(red)) {
                red = 0
            };
            if (green > 255 || green < 0 || isNaN(green)) {
                green = 0
            };
            if (blue > 255 || blue < 0 || isNaN(blue)) {
                blue = 0
            };
            let newColor = 'rgb(' + [red,green,blue].join(',') + ')';
            parent.style.background = newColor
            pickr.setColor(newColor);
        });
    }

});