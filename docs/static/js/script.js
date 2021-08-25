document.addEventListener("DOMContentLoaded", function () {
    const buttons = document.querySelector('#hero_buttons');
    const scrollspy = VanillaScrollspy(buttons, 1000, 'easeInOutSine');
    scrollspy.init();

    let copyrightText = document.getElementById('copyright');
    copyrightText.innerHTML = "Copyright © " + new Date().getFullYear() + " MLSC.";

    let dismissed = localStorage.getItem("dismissed");
    let alertDiv = document.getElementById("update_alert");
    let dismissButton = document.getElementById("cancel_alert");
    if (!dismissed) {
        alertDiv.classList.remove("hidden");
    }

    dismissButton.addEventListener("click", function () {
        alertDiv.classList.add("hidden");
        localStorage.setItem("dismissed", true);
    });
});
