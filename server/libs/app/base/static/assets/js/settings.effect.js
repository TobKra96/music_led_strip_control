var settingsIdentifier;
var effectIdentifier;
var localSettings = {};
var currentDevice;
var colors = {};
var gradients = {};
var devices = {};

var devicesLoading = true;
var coloresLoading = true;
var gradientsLoading = true;

var initialized = false;

// Init and load all settings
$( document ).ready(function() {

  if(initialized){
    return;
  }
  initialized = true;

  settingsIdentifier = $("#settingsIdentifier").val();
  effectIdentifier = $("#effectIdentifier").val();

  // Only allow all_devices for sync fade effect.
  if(effectIdentifier == "effect_sync_fade"){
    currentDevice = "all_devices"
    BuildDeviceTab();
    UpdateCurrentDeviceText();

    AddEventListeners();

    devicesLoading = false;
  }
  else{
    GetDevices();
  }

  GetColors();
  GetGradients();
});

//Check if all initial ajax requests are finished.
function CheckIfFinishedInitialLoading (){
  if(!devicesLoading && !coloresLoading && !gradientsLoading){
    GetLocalSettings();
  }
}

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
  currentDevice = "all_devices"
  this.devices = devices;

  BuildDeviceTab();
  UpdateCurrentDeviceText();

  AddEventListeners();

  devicesLoading = false;
  CheckIfFinishedInitialLoading();
}

function GetColors(){
  $.ajax({
    url: "/GetColors",
    type: "GET", //send it through get method
    data: {     },
    success: function(response) {
        ParseGetColors(response);
    },
    error: function(xhr) {
      //Do Something to handle error
    }
  });
}

function ParseGetColors(response){
  var context = this;
  this.colors = response;

  $('.colours').each(function(){
    var colours = context.colors;
    for(var currentKey in colours){
      var newOption = new Option(currentKey, currentKey);
      /// jquerify the DOM object 'o' so we can use the html method
      $(newOption).html(currentKey);
      $(this).append(newOption);
    }
  });

  coloresLoading = false;
  CheckIfFinishedInitialLoading();
}

function GetGradients(){
  $.ajax({
    url: "/GetGradients",
    type: "GET", //send it through get method
    data: {     },
    success: function(response) {
        ParseGetGradients(response);
    },
    error: function(xhr) {
      //Do Something to handle error
    }
  });
}

function ParseGetGradients(response){
  var context = this;
  this.gradients = response;

  $('.gradients').each(function(){
    var gradients = context.gradients;
    for(var currentKey in gradients){
      var newOption = new Option(currentKey, currentKey);
      /// jquerify the DOM object 'o' so we can use the html method
      $(newOption).html(currentKey);
      $(this).append(newOption);
    }
  });

  gradientsLoading = false;
  CheckIfFinishedInitialLoading();
}

function GetEffectSetting(device, effect, setting_key){
  $.ajax({
    url: "/GetEffectSetting",
    type: "GET", //send it through get method
    data: {
      "device": device,
      "effect": effect,
      "setting_key": setting_key,
  },
    success: function(response) {
        ParseGetEffectSetting(response);
    },
    error: function(xhr) {
      //Do Something to handle error
    }
  });
}

function ParseGetEffectSetting(response){
  var setting_key = response["setting_key"];
  var setting_value = response["setting_value"];
  localSettings[setting_key] = setting_value;

  SetLocalInput(setting_key, setting_value)

 // Set initial effect slider values
  $("span[for='" + setting_key + "']").text(setting_value)
}

function GetLocalSettings(){
  var all_setting_keys = GetAllSettingKeys();

  if(currentDevice == "all_devices"){
    if(Object.keys(devices).length > 0){
      var first_device_name = Object.keys(devices)[0];
      Object.keys(all_setting_keys).forEach(setting_id => {
        GetEffectSetting(first_device_name, effectIdentifier, all_setting_keys[setting_id])
      })
    }
  }else{
    Object.keys(all_setting_keys).forEach(setting_id => {
      GetEffectSetting(currentDevice, effectIdentifier, all_setting_keys[setting_id])
    })
  }


}

function SetLocalInput(setting_key, setting_value){
  if($("#" + setting_key).attr('type') == 'checkbox'){
    if(setting_value){
      $("#" + setting_key).click();
    }
  }else if($("#" + setting_key).attr('id') == 'color_input'){
    // Set RGB color and value from config
    $("#color_input").val(setting_value);
    pickr.setColor(setting_value);
  }else{
    $("#" + setting_key).val(setting_value);
  }

  $("#" + setting_key).trigger('change');
}



function GetAllSettingKeys(){
  var all_setting_keys = $(".setting_input").map(function() {
    return this.attributes["id"].value;
  }).get();

  return all_setting_keys;
}


function SetEffectSetting(device, effect, settings){

  if(this.currentDevice == "all_devices"){
      var data = {};
      data["effect"] = effect;
      data["settings"] = settings;

      $.ajax({
          url: "/SetEffectSettingForAll",
          type: "POST", //send it through get method
          data: JSON.stringify(data, null, '\t'),
          contentType: 'application/json;charset=UTF-8',
          success: function(response) {
              console.log("Set the effect successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
          },
          error: function(xhr) {
            //Do Something to handle error
            console.log("Set the effect got an error. Error: " + xhr.responseText);
          }
        });

  }else{
      var data = {};
      data["device"] = this.currentDevice;
      data["effect"] = effect;
      data["settings"] = settings;

      $.ajax({
          url: "/SetEffectSetting",
          type: "POST", //send it through get method
          data: JSON.stringify(data, null, '\t'),
          contentType: 'application/json;charset=UTF-8',
          success: function(response) {
            console.log("Set the effect successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
          },
          error: function(xhr) {
            //Do Something to handle error
            console.log("Set the effect got an error. Error: " + xhr.responseText);
          }
        });
  }

}

function SetLocalSettings(){
  var all_setting_keys = GetAllSettingKeys();

  settings = {};

  Object.keys(all_setting_keys).forEach(setting_id => {
    var setting_key = all_setting_keys[setting_id];
    var setting_value = "";

    if($("#" + setting_key).length){
      if($("#" + setting_key).attr('type') == 'checkbox'){
        setting_value = $("#" + setting_key).is(':checked')
      }else if($("#" + setting_key).attr('type') == 'number'){
        setting_value = parseFloat($("#" + setting_key).val());
      }
      else if($("#" + setting_key).attr('id') == 'color_input'){
        // Save RGB value to config
        setting_value = $("#color_input").val();
      }
      else{
        setting_value = $("#" + setting_key).val();
      }
    }

    settings[setting_key] = setting_value;

  })

  SetEffectSetting(currentDevice, effectIdentifier, settings)

}



/* Device Handling */

function BuildDeviceTab(){
  var devices = this.devices

  $('#deviceTabID').append("<li class='nav-item device_item'><a class='nav-link active' id='all_devices' data-toggle='pill' href='#pills-0' role='tab' aria-controls='pills-0' aria-selected='true'>All Devices</a></li>")

  Object.keys(devices).forEach(device_key => {
    $('#deviceTabID').append("<li class='nav-item device_item'><a class='nav-link' id=\"" + device_key + "\" data-toggle='pill' href='#pills-0' role='tab' aria-controls='pills-0' aria-selected='false'>" + devices[device_key] + "</a></li>")
  });

  $('#device_count').text(Object.keys(devices).length);

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
      text = "All Devices"
  }
  else
  {
      text = this.devices[this.currentDevice]
  }

  $("#selected_device_txt").text(text);
}

function SwitchDevice(e){
  this.currentDevice = e.target.id;
  GetLocalSettings();
  UpdateCurrentDeviceText();
}

document.getElementById("save_btn").addEventListener("click",function(e) {
  SetLocalSettings();
});

// Create color picker instance
let parent = document.querySelector('#color_picker');
let input = document.querySelector('#color_input');

if (parent && input) {
    var pickr = Pickr.create({
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

    // Parse color selection
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