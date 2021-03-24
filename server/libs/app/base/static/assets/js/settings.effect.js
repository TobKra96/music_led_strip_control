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
    BuildDeviceCombobox();
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

  BuildDeviceCombobox();
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

 // Set initial slider values
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
  }else if($("#" + setting_key).hasClass('colorpicker_input')){
    var hexcolor = rgbToHex(setting_value[0], setting_value[1], setting_value[2]);
    $("#" + setting_key).val("rgb(" + setting_value[0] + "," + setting_value[1] + "," +setting_value[2] + ")");
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
      else if($("#" + setting_key).hasClass('colorpicker_input')){
        rgb_color =  hexToRgb($("#" + setting_key).val());
        setting_value = rgb_color;
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

function BuildDeviceCombobox(){
  var devices = this.devices

  $('#deviceDropDownMenuID').append("<a class=\"dropdown-item device_item\" id=\"all_devices\">All Devices</a>")

  Object.keys(devices).forEach(device_key => {
      $('#deviceDropDownMenuID').append( "<a class=\"dropdown-item device_item\" id=\"" + device_key +"\">" + devices[device_key] + "</a>" );
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

}

function SwitchDevice(e){
  this.currentDevice = e.target.id;
  GetLocalSettings();
  UpdateCurrentDeviceText();
}

document.getElementById("save_btn").addEventListener("click",function(e) {
  SetLocalSettings();
});


$(function() {
  if($('#colorpickerDiv').length) {
    $('#colorpickerDiv').colorpicker({
        color: '#000000',
        format: 'rgb'
    });
  }
});



function componentToHex(c) {
  var hex = c.toString(16);
  return hex.length == 1 ? "0" + hex : hex;
}

function rgbToHex(r, g, b) {
  return "#" + componentToHex(r) + componentToHex(g) + componentToHex(b);
}

function hexToRgb(str) {
  var match = str.match(/rgb?\((\d{1,3}), ?(\d{1,3}), ?(\d{1,3})\)?(?:, ?(\d(?:\.\d?))\))?/);
  return match ? [match[1], match[2], match[3]] : [0,0,0];
}

