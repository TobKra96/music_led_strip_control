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

});