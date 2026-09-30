import Toast from "./classes/Toast.js";

let groups = jinja_groups;
let currentGroup = groups.find(g => g.id === localStorage.getItem("lastGroup"));
currentGroup = currentGroup ? currentGroup : groups[0];

// Init and load all settings
$(document).ready(function () {
    if (groups.length === 0) {
        $("#groupFound").addClass('d-none');
        $("#noGroupFound").removeClass('d-none');
        return;
    }

    $("#groupFound").removeClass('d-none');
    $("#noGroupFound").addClass('d-none');
    $("#selected_group_label").removeClass('d-none');

    groups.forEach(group => {
        $(`a[data-group_id=${group.id}]`).on("click", () => {
            selectGroup(group);
        });
    });

    selectGroup(currentGroup);
});

function selectGroup(group) {
    currentGroup = group;
    localStorage.setItem('lastGroup', group.id);

    $("a[data-group_id]").removeClass("active");
    $(`a[data-group_id=${group.id}]`).addClass("active");
    $("#selected_group_txt").text(group.name);

    $("#group_name").val(group.name);
    $(".group_device_input").each(function () {
        $(this).prop('checked', group.devices.includes($(this).data("device_id")));
    });

    $.ajax({
        url: "/api/settings/group",
        data: { "group": group.id }
    }).done((data) => {
        Object.entries(data.settings).forEach(([setting_key, setting_value]) => {
            $(`#${setting_key}.group_setting_input`).val(setting_value);
            $(`span[for='${setting_key}']`).text(setting_value);
        });
    }).fail((data) => {
        new Toast(`Unable to load settings of group "${group.name}". Error: ${data.responseText}`).error();
    });
}

// Save Functions   -----------------------------------------------------------

function saveGroup() {
    const groupName = $("#group_name").val();
    const devices = $(".group_device_input:checked").map(function () { return $(this).data("device_id") }).toArray();
    const settings = {
        "led_brightness": parseInt($("#led_brightness").val()),
        "fps": parseInt($("#fps").val())
    };

    // Save members first, so the group settings are applied to newly added devices.
    $.ajax({
        url: "/api/system/groups",
        type: "PUT",
        data: JSON.stringify({ "group": currentGroup.id, "group_name": groupName, "devices": devices }),
        contentType: 'application/json;charset=UTF-8'
    }).then(() => {
        return $.ajax({
            url: "/api/settings/group",
            type: "POST",
            data: JSON.stringify({ "group": currentGroup.id, "settings": settings }),
            contentType: 'application/json;charset=UTF-8'
        });
    }).done(() => {
        currentGroup.name = groupName;
        currentGroup.devices = devices;
        $(`a[data-group_id=${currentGroup.id}]`).text(groupName);
        $("#selected_group_txt").text(groupName);
        new Toast(`Group "${groupName}" saved.`).success();
    }).fail((data) => {
        new Toast(`Error while saving group "${currentGroup.name}". Error: ${data.responseText}`).error();
    });
}

function createGroup() {
    $.ajax({
        url: "/api/system/groups",
        type: "POST",
        data: JSON.stringify({}),
        contentType: 'application/json;charset=UTF-8'
    }).done((data) => {
        localStorage.setItem('lastGroup', data.group);
        location.reload();
    }).fail((data) => {
        new Toast(`Error while creating group. Error: ${data.responseText}`).error();
    });
}

$("#save_btn").on("click", function () {
    saveGroup();
});

$("#create1_btn, #create2_btn").on("click", function () {
    createGroup();
});

$("#delete_btn").on("click", function () {
    $('#modal_group_name').text(currentGroup.name);
    $('#modal_delete_group').modal('show');
});

$("#delete_btn_modal").on("click", function () {
    $('#modal_delete_group').modal('hide');
    $.ajax({
        url: "/api/system/groups",
        type: "DELETE",
        data: JSON.stringify({ "group": currentGroup.id }),
        contentType: 'application/json;charset=UTF-8'
    }).done(() => {
        localStorage.removeItem('lastGroup');
        location.reload();
    }).fail((data) => {
        new Toast(`Error while deleting group "${currentGroup.name}". Error: ${data.responseText}`).error();
    });
});
