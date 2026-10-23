// Init and load all settings
$(() => {
    var settingsIdentifier = $("#settingsIdentifier").val();

    Promise.all([

        $.ajax("/api/settings/microphone/volume").done((response) => {
            $('#level').val(response["level"]);
            $('#output').val(response["output"]);
            // Set initial effect slider values
            $("span[for='level']").text(response["level"]);
        })

    ]).then(() => {
    }).catch((response) => {
        // all requests finished but one or more failed
        new Toast(JSON.stringify(response, null, '\t')).error();
    });
}
);

/**
 * Call API to set the microphone volume level.
 * @param {number} level
 */
function setMicrophoneLevel(level) {
    data = {};
    data["level"] = level
    $.ajax({
        url: "/api/settings/microphone/volume",
        type: "POST",
        data: JSON.stringify(data, null, '\t'),
        contentType: 'application/json;charset=UTF-8'
    }).done(response => {
        $('#output').val(response["output"]);
        // todo toasts
        console.log("Effect settings set successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
    }).fail(response => {
        // todo toasts
        console.log("Error while setting effect settings. Error: " + response.responseText);
    });
}

document.getElementById("save_btn").addEventListener("click", function () {
    level = $('#level').val();
    setMicrophoneLevel(level);

});

// Set effect slider values
$('input[type=range]').on('input', function () {
    $("span[for='" + $(this).attr('id') + "']").text(this.value);
});
