var allSettings;
var activeEffect = "";
var currentDevice = "all_devices";

// Init and load all settings
$( document ).ready(function() {

    $.ajax({
        url: "/getSettings",
        type: "GET", //send it through get method
        data: { 
          settingsIdentifier: this.settingsIdentifier
        },
        success: function(response) {
          parseFromSettings(response);
        },
        error: function(xhr) {
          //Do Something to handle error
        }
      });
});


function setActiveEffect(newActiveEffect){

    var lastEffect = this.activeEffect;
    this.activeEffect = newActiveEffect;

    removeActiveStyle(lastEffect);
    
    if(this.currentDevice == "all_devices"){
        var device_configs = this.allSettings["device_configs"]
        Object.keys(device_configs).forEach(device => {
            this.allSettings["device_configs"][device]["effects"]["last_effect"] = this.activeEffect
        });
    }else{
        this.allSettings["device_configs"][this.currentDevice]["effects"]["last_effect"] = this.activeEffect
    }
    

    var data = {};
    data["settings"] = this.allSettings;
    data["device"] = this.currentDevice;
    data["activeEffect"] = this.activeEffect;

    $.ajax({
        url: "/setActiveEffect",
        type: "POST", //send it through get method
        data: JSON.stringify(data, null, '\t'),
        contentType: 'application/json;charset=UTF-8',
        success: function(response) {
            console.log("Set the effect sucessfull. Response: " + response.toString());
        },
        error: function(xhr) {
          //Do Something to handle error
          console.log("Set the effect got an error. Error: " + xhr.responseText);
        }
      });

    setActiveStyle(this.activeEffect);
}

function parseFromSettings(allSettings){
    this.allSettings = allSettings;

    this.BuildDeviceCombobox();
    this.AddEventListeners();
    this.UpdateCurrentDevice("all_devices");
}

/* Device Handling */

function BuildDeviceCombobox(){
    var device_configs = this.allSettings["device_configs"]

    Object.keys(device_configs).forEach(device => {
        $( ".dropdown-menu").append( "<a class=\"dropdown-item device_item\" id=\"" + device +"\">" + device_configs[device]["DEVICE_NAME"] + "</a>" );
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

function UpdateCurrentDevice(currentDevice){
    this.currentDevice = currentDevice;

    var text = "";
    var currentEffect = "";
    if(this.currentDevice == "all_devices"){
        text = "Current device: All Devices"
    }
    else
    {
        text = "Current device: " + this.allSettings["device_configs"][currentDevice]["DEVICE_NAME"]
        currentEffect = this.allSettings["device_configs"][currentDevice]["effects"]["last_effect"]
    }
    
    $("#selected_device_txt").text(text);
    if(this.activeEffect != ""){
        this.removeActiveStyle(this.activeEffect);
    }
    
    this.activeEffect = currentEffect;

    if(this.activeEffect != ""){
        this.setActiveStyle(this.activeEffect);
    }
}

function SwitchDevice(e){
    var newDeviceId = e.target.id;

    this.UpdateCurrentDevice(newDeviceId);
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
        setActiveEffect(newActiveEffect);
    }
}

