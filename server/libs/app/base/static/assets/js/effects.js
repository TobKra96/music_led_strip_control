$(document).ready(function() {

    // Set effect slider values
    $('input[type=range]').on('input', function() {
        $("span[for='" + $(this).attr('id') + "']").text(this.value)
    });

});