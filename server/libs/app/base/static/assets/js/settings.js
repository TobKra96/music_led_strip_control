document.addEventListener("DOMContentLoaded", () => {

    // Set LED strip brightness
    let ledBrightnessSlider = document.getElementById("LED_Brightness");
    let ledBrightnessNumOutput = document.getElementById("ledBrightnessNum");

    if (ledBrightnessSlider && ledBrightnessNumOutput) {
        ledBrightnessNumOutput.innerHTML = ledBrightnessSlider.value;

        ledBrightnessSlider.oninput = function() {
            ledBrightnessNumOutput.innerHTML = this.value;
        }
    }

    // Insert filename of imported config
    let fileInput = document.querySelector('.custom-file-input');

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            let fileName = document.getElementById("configUpload").files[0].name;
            let nextSibling = e.target.nextElementSibling
            nextSibling.innerText = fileName
        })
    }

    // Hide unused output settings
    let outputType = document.getElementById("OUTPUT_TYPE");

    if (outputType) {
        function toggleOutput() {
            if (outputType.value == 'raspberrypi') {
                $('#raspberrypi').removeClass('d-none');
                $('#udp').addClass('d-none');
            } else {
                $('#udp').removeClass('d-none');
                $('#raspberrypi').addClass('d-none');
            }
        };
        toggleOutput();
        outputType.addEventListener("change", toggleOutput);
    }

});