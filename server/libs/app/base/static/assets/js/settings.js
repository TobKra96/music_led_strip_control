$(document).ready(function () {

    // Set LED strip brightness
    $('input[type=range]').on('input', function () {
        $("span[for='" + $(this).attr('id') + "']").text(this.value)
    });

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
            if (outputType.value == 'output_raspi') {
                $('#raspberrypi').removeClass('d-none');
                $('#udp').addClass('d-none');
            } else {
                $('#udp').removeClass('d-none');
                $('#raspberrypi').addClass('d-none');
            }
        };
        $(outputType).change(toggleOutput).change();
    }

    // Toggle PIN visibility on hover
    $("#toggle_pin_view").on("mouseover", function (event) {
        event.preventDefault();
        $('#DASHBOARD_PIN').attr('type', 'text');
        $('#toggle_pin_view').removeClass("icon-eye");
        $('#toggle_pin_view').addClass("icon-eye-off");
    });
    $("#toggle_pin_view").on("mouseleave", function (event) {
        event.preventDefault();
        $('#DASHBOARD_PIN').attr('type', 'password');
        $('#toggle_pin_view').addClass("icon-eye");
        $('#toggle_pin_view').removeClass("icon-eye-off");
    });

    // Tooltip descriptions for general settings
    $('#WEBSERVER_PORT_TOOLTIP').attr('data-original-title', 'The port used by the web server.<br>Changing this, the web interface will be available on another port. Example:<br>http://[raspberry_pi_ip]:8080<br><br>Default setting: 8080');
    $('#DASHBOARD_PIN_TOOLTIP').attr('data-original-title', 'The PIN code for locking the web interface from unwanted access.<br>Only 4 to 8 digits are allowed.<br>Enable or disable the PIN Lock feature using the checkbox below.');
    $('#DEVICE_ID_TOOLTIP').attr('data-original-title', 'The device ID of your microphone.<br>This audio device will be used for the music reactive effects.');
    $('#DEFAULT_SAMPLE_RATE_TOOLTIP').attr('data-original-title', 'The sample rate of your microphone.<br>You can find it inside the console output.<br><br>Common values are 44100 or 48000.');
    $('#MIN_FREQUENCY_TOOLTIP').attr('data-original-title', 'The minimum frequency supported by your microphone.<br>This will increase the quality of your effects.<br><br>Default setting: 50');
    $('#MAX_FREQUENCY_TOOLTIP').attr('data-original-title', 'The maximum frequency supported by your microphone.<br>This will increase the quality of your effects.<br><br>Default setting: 16000');
    $('#MIN_VOLUME_THRESHOLD_TOOLTIP').attr('data-original-title', 'The minimum volume level of your microphone that has to be reached before the program will recognize the audio signal.<br>It filters background noises and reduces the rate of false triggers.<br><br>Default setting: 0.001');
    $('#N_ROLLING_HISTORY_TOOLTIP').attr('data-original-title', 'The amount of audio snapshots that will be stored for the calculation of the rhythm.<br><br>Default setting: 4');
    $('#FRAMES_PER_BUFFER_TOOLTIP').attr('data-original-title', 'The buffer size of the audio signal.<br>More buffer frames cause lower frame rates, but higher effect quality.<br>Less buffer frames cause high frame rates, but lower effect quality.<br><br>Default setting: 512');
    $('#N_FFT_BINS_TOOLTIP').attr('data-original-title', 'The amount of slices that the audio spectrum will be divided into.<br><br>Default setting: 24');
    $('#LOG_LEVEL_CONSOLE_TOOLTIP').attr('data-original-title', 'The logging verbosity level in the console.<br><br>Default setting: INFO');
    $('#LOG_LEVEL_FILE_TOOLTIP').attr('data-original-title', 'The logging verbosity level in a log file.<br>Enable or disable file logging using the checkbox below.<br><br>Use this only for debugging.<br>File logging for extensive periods of time could cause SD card wear-out.<br><br>Default setting: INFO');

    // Tooltip descriptions for device settings
    $('#FPS_TOOLTIP').attr('data-original-title', 'The maximum FPS you want to output with current device.<br><br>Default setting: 60');
    $('#LED_Count_TOOLTIP').attr('data-original-title', 'The amount of LEDs you want to control with current device.');
    $('#LED_Mid_TOOLTIP').attr('data-original-title', 'The middle of the LED Strip.<br>If you have a corner setup, you can shift the middle.');
    $('#OUTPUT_TYPE_TOOLTIP').attr('data-original-title', 'The output type for current device.<br>Raspberry Pi can be used directly, ESP can be used as a client.');
    $('#LED_Pin_TOOLTIP').attr('data-original-title', 'The GPIO Pin used for the signal.<br>Not all pins are compatible.<br>Use GPIO 18 (pin 12) for PWM0 and GPIO 13 (pin 33) for PWM1.<br><br>Default setting: 18');
    $('#LED_Freq_Hz_TOOLTIP').attr('data-original-title', 'The signal frequency used to communicate with the LED Strip.<br><br>Default setting: 800000');
    $('#LED_Channel_TOOLTIP').attr('data-original-title', 'The channel you want to use. PWM0 - 0 and PWM1 - 1.<br><br>Default setting: 0');
    $('#LED_Dma_TOOLTIP').attr('data-original-title', 'The direct memory access channel. Select a channel between 0-14.<br><br>Default setting: 10');
    $('#LED_Strip_TOOLTIP').attr('data-original-title', 'The LED Strip type. Check if the RGB channels are mapped correctly.<br><br>Default setting: WS281x_RGB');
    $('#LED_Invert_TOOLTIP').attr('data-original-title', 'The parameter for inverting the LED signal. It can be useful if you want to use an inverted logic level shifter.<br><br>Default value: Off');
    $('#UDP_Client_IP_TOOLTIP').attr('data-original-title', 'The IP address of the client.');
    $('#UDP_Client_Port_TOOLTIP').attr('data-original-title', 'The port used for the communication between the server and client.<br><br>Default setting: 7777');
});