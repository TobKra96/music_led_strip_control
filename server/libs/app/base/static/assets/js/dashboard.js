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

var devices;
var activeEffect = "";
var currentDevice = "all_devices";

// Init and load all settings
$( document ).ready(function() {
    GetDevices();
});

function GetDevices(){
    $.ajax({
        url: "/GetDevices",
        type: "GET", //send it through get method
        success: function(response) {
            ParseDevices(response);
        },
        error: function(xhr) {
          //Do Something to handle error
        }
      });
}

function ParseDevices(devices){
    this.currentDevice = "all_devices"
    this.devices = devices;

    this.BuildDeviceCombobox();
    this.AddEventListeners();
    this.UpdateCurrentDeviceText();
    this.UpdateActiveEffectTile();
}

function GetActiveEffect(device){

    $.ajax({
        url: "/GetActiveEffect",
        type: "GET", //send it through get method
        data: {"device": device},
        success: function(response) {
            ParseActiveEffect(response);
        },
        error: function(xhr) {
          //Do Something to handle error
        }
      });
}

function ParseActiveEffect(respond){
    this.activeEffect = respond["effect"];
    this.UpdateActiveEffectTile();
}

function SetActiveEffect(newActiveEffect){

    var lastEffect = this.activeEffect;
    this.activeEffect = newActiveEffect;

    removeActiveStyle(lastEffect);

    if(this.currentDevice == "all_devices"){
        var data = {};
        data["effect"] = this.activeEffect;

        $.ajax({
            url: "/SetActiveEffectForAll",
            type: "POST", //send it through get method
            data: JSON.stringify(data, null, '\t'),
            contentType: 'application/json;charset=UTF-8',
            success: function(response) {
                console.log("Set the effect successfully. Response: " + response.toString());
            },
            error: function(xhr) {
              //Do Something to handle error
              console.log("Set the effect got an error. Error: " + xhr.responseText);
            }
          });

    }else{
        var data = {};
        data["device"] = this.currentDevice;
        data["effect"] = this.activeEffect;

        $.ajax({
            url: "/SetActiveEffect",
            type: "POST", //send it through get method
            data: JSON.stringify(data, null, '\t'),
            contentType: 'application/json;charset=UTF-8',
            success: function(response) {
                console.log("Set the effect successfully. Response: " + response.toString());
            },
            error: function(xhr) {
              //Do Something to handle error
              console.log("Set the effect got an error. Error: " + xhr.responseText);
            }
          });
    }

    setActiveStyle(this.activeEffect);
}


/* Device Handling */

function BuildDeviceCombobox(){
    var devices = this.devices

    $( ".dropdown-menu").append("<a class=\"dropdown-item device_item\" id=\"all_devices\">All Devices</a>")

    Object.keys(devices).forEach(device_key => {
        $( ".dropdown-menu").append( "<a class=\"dropdown-item device_item\" id=\"" + device_key +"\">" + devices[device_key] + "</a>" );
    });

}

function AddEventListeners(){
    var elements = document.getElementsByClassName("device_item");

    for (var i = 0; i < elements.length; i++) {
        elements[i].addEventListener('click', function(e){
            SwitchDevice(e);
        });
    }
}

function UpdateCurrentDeviceText(){
    var text = "";

    if(this.currentDevice == "all_devices"){
        text = "Current device: All Devices"
    }
    else
    {
        text = "Current device: " + this.devices[this.currentDevice]
    }

    $("#selected_device_txt").text(text);
    if(this.activeEffect != ""){
        this.removeActiveStyle(this.activeEffect);
    }
}

function UpdateActiveEffectTile(){

    if(this.activeEffect != ""){
        this.setActiveStyle(this.activeEffect);
    }
}

function SwitchDevice(e){
    var newDeviceId = e.target.id;

    this.currentDevice = newDeviceId;

    if(newDeviceId == "all_devices"){
        this.removeActiveStyle(this.activeEffect);
        this.UpdateActiveEffectTile();
        this.UpdateCurrentDeviceText();
        return;
    }

    this.GetActiveEffect(newDeviceId);

    this.UpdateCurrentDeviceText();
}




/* Effect Handling */


function setActiveStyle(currentEffect){

    $("#" + currentEffect).addClass("active-dashboard-item");
}

function removeActiveStyle(currentEffect){
    $("#" + currentEffect).removeClass("active-dashboard-item");
}

// locate your element and add the Click Event Listener
document.getElementById("dashboard-list-special").addEventListener("click",function(e) {
    // e.target is our targetted element.
    // try doing console.log(e.target.nodeName), it will result LI

    switchEffect(e, "dashboard-list-special");
});

// locate your element and add the Click Event Listener
document.getElementById("dashboard-list-none-music").addEventListener("click",function(e) {
    // e.target is our targetted element.
    // try doing console.log(e.target.nodeName), it will result LI

    switchEffect(e, "dashboard-list-none-music");
});

// locate your element and add the Click Event Listener
document.getElementById("dashboard-list-music").addEventListener("click",function(e) {
    // e.target is our targetted element.
    // try doing console.log(e.target.nodeName), it will result LI

    switchEffect(e, "dashboard-list-music");
});

function switchEffect(e, listName){
    var newActiveEffect = "";

    // Click on the li element direct
    if(e.target && e.target.nodeName == "LI") {
        if(e.target.parentElement && e.target.parentElement.id == listName){
            newActiveEffect = e.target.id;
        }

    // Click on some of the span elements inside the li element.
    }else if((e.target && e.target.nodeName == "SPAN")||(e.target && e.target.nodeName == "I")){
        if(e.target.parentElement && e.target.parentElement.nodeName == "LI"){
            if(e.target.parentElement.parentElement && e.target.parentElement.parentElement.id == listName){
                newActiveEffect = e.target.parentElement.id;
            }
        }
    }

    if(newActiveEffect.length > 0){
        console.log(newActiveEffect + " was clicked");
        SetActiveEffect(newActiveEffect);
    }
}