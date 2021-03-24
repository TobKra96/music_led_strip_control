var settingsIdentifier;
var localSettings = {};
var currentDevice;
var output_types = {};


var devicesLoading = true;
var outputTypesLoading = true;
var ledStripsLoading = true;

var reloadingCounter = 0;
var reloadingMax = 0;

// Init and load all settings
$( document ).ready(function() {
  settingsIdentifier = $("#settingsIdentifier").val();

  GetDevices();
  GetOutputTypes();
  GetLEDStrips();
});

//Check if all initial ajax requests are finished.
function CheckIfFinishedInitialLoading (){
  if(!devicesLoading && !outputTypesLoading && !ledStripsLoading){
    GetLocalSettings();
  }
}

// Get Devices    -----------------------------------------------------------

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
  this.devices = devices;

  if(Object.keys(devices).length > 0){
    currentDevice = Object.keys(devices)[0];
  }

  BuildDeviceCombobox();
  UpdateCurrentDeviceText();

  AddEventListeners();

  devicesLoading = false;
  CheckIfFinishedInitialLoading();
}


// Get Output Type    -----------------------------------------------------------

function GetOutputTypes(){
  $.ajax({
    url: "/GetOutputTypes",
    type: "GET", //send it through get method
    data: {     },
    success: function(response) {
        ParseGetOutputTypes(response);
    },
    error: function(xhr) {
      //Do Something to handle error
    }
  });
}

function ParseGetOutputTypes(response){
  var context = this;
  this.output_types = response;

  $('.output_type').each(function(){
    var output_types = context.output_types;

    Object.keys(output_types).forEach(output_type_key => {
      var newOption = new Option(output_types[output_type_key], output_type_key);
      /// jquerify the DOM object 'o' so we can use the html method
      $(this).append(newOption);
    });
  });

  outputTypesLoading = false;
  CheckIfFinishedInitialLoading();
}

// Get Device Settings   -----------------------------------------------------------

function GetDeviceSetting(device, setting_key){
  $.ajax({
    url: "/GetDeviceSetting",
    type: "GET", //send it through get method
    data: {
      "device": device,
      "setting_key": setting_key,
  },
    success: function(response) {
        ParseGetDeviceSetting(response);
    },
    error: function(xhr) {
      //Do Something to handle error
    }
  });
}

function ParseGetDeviceSetting(response){
  var setting_key = response["setting_key"];
  var setting_value = response["setting_value"];
  localSettings[setting_key] = setting_value;

  SetLocalDeviceInput(setting_key, setting_value)
}

// Get Output Type Device Settings   -----------------------------------------------------------

function GetOutputTypeDeviceSetting(device, output_type_key, setting_key){
  $.ajax({
    url: "/GetOutputTypeDeviceSetting",
    type: "GET", //send it through get method
    data: {
      "device": device,
      "output_type_key": output_type_key,
      "setting_key": setting_key,
  },
    success: function(response) {
        ParseGetOutputTypeDeviceSetting(response);
    },
    error: function(xhr) {
      //Do Something to handle error
    }
  });
}

function ParseGetOutputTypeDeviceSetting(response){
  var output_type_key = response["output_type_key"];
  var setting_key = response["setting_key"];
  var setting_value = response["setting_value"];
  localSettings[setting_key] = setting_value;

  SetLocalOutputTypeDeviceInput(output_type_key, setting_key, setting_value)

  // Set initial brightness slider value
  $("span[for='" + setting_key + "']").text(setting_value)
}

// Get LED Strips   -----------------------------------------------------------

function GetLEDStrips(){
  $.ajax({
    url: "/GetLEDStrips",
    type: "GET", //send it through get method
    data: {     },
    success: function(response) {
        ParseGetLEDStrips(response);
    },
    error: function(xhr) {
      //Do Something to handle error
    }
  });
}

function ParseGetLEDStrips(response){
  var context = this;
  this.led_strips = response;

  $('.led_strips').each(function(){
    var led_strips = context.led_strips;
    for(var currentKey in led_strips){
      var newOption = new Option(led_strips[currentKey], currentKey);
      $(newOption).html(led_strips[currentKey]);
      $(this).append(newOption);
    }
  });

  ledStripsLoading = false;
  CheckIfFinishedInitialLoading();
}



// Set Device Setting   -----------------------------------------------------------

function SetDeviceSetting(device, settings){

  var data = {};
  data["device"] = device;
  data["settings"] = settings;

  $.ajax({
      url: "/SetDeviceSetting",
      type: "POST", //send it through get method
      data: JSON.stringify(data, null, '\t'),
      contentType: 'application/json;charset=UTF-8',
      success: function(response) {
          console.log("Set the device settings successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
          reloadingCounter++;
          if(reloadingCounter >= reloadingMax){
            location.reload();
          }
      },
      error: function(xhr) {
        //Do Something to handle error
        console.log("Set the device settings got an error. Error: " + xhr.responseText);
        reloadingCounter++;
          if(reloadingCounter >= reloadingMax){
            location.reload();
          }
      }
    });
}

// Set Output Type Device Setting   -----------------------------------------------------------

function SetOutputTypeDeviceSetting(device, output_type_key, settings){

var data = {};
data["device"] = device;
data["output_type_key"] = output_type_key;
data["settings"] = settings;

$.ajax({
  url: "/SetOutputTypeDeviceSetting",
  type: "POST", //send it through get method
  data: JSON.stringify(data, null, '\t'),
  contentType: 'application/json;charset=UTF-8',
  success: function(response) {
      console.log("Set the device settings successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
      reloadingCounter++;
          if(reloadingCounter >= reloadingMax){
            location.reload();
          }

  },
  error: function(xhr) {
    //Do Something to handle error
    console.log("Set the device settings got an error. Error: " + xhr.responseText);
    reloadingCounter++;
          if(reloadingCounter >= reloadingMax){
            location.reload();
          }
  }
});
}


// Load Functions   -----------------------------------------------------------

function GetLocalSettings(){

  if(Object.keys(devices).length > 0){
    $("#deviceFound").removeClass('d-none');
    $("#noDeviceFound").addClass('d-none');
  }else{
    $("#deviceFound").addClass('d-none');
    $("#noDeviceFound").removeClass('d-none');

    return;
  }


  var all_device_setting_keys = GetDeviceSettingKeys();

    Object.keys(all_device_setting_keys).forEach(setting_id => {
      GetDeviceSetting(currentDevice, all_device_setting_keys[setting_id])
    })

    Object.keys(output_types).forEach(output_type_key => {
      var all_output_type_setting_keys = GetOutputTypeSettingKeys(output_type_key);

      Object.keys(all_output_type_setting_keys).forEach(setting_id => {
        GetOutputTypeDeviceSetting(currentDevice, output_type_key, all_output_type_setting_keys[setting_id])
      })

    });

}

function SetLocalDeviceInput(setting_key, setting_value){
  if($("#" + setting_key).attr('type') == 'checkbox'){
    if(setting_value){
      $("#" + setting_key).click();
    }

  }else{
    $("#" + setting_key).val(setting_value);
  }

  $("#" + setting_key).trigger('change');
}

function SetLocalOutputTypeDeviceInput(output_type_key, setting_key, setting_value){
  if($("#" + setting_key + "." + output_type_key).attr('type') == 'checkbox'){
    if(setting_value){
      $("#" + setting_key + "." + output_type_key).click();
    }

  }else{
    $("#" + setting_key + "." + output_type_key).val(setting_value);
  }

  $("#" + setting_key + "." + output_type_key).trigger('change');
}


function GetDeviceSettingKeys(){
  var all_setting_keys = $(".device_setting_input").map(function() {
    return this.attributes["id"].value;
  }).get();

  return all_setting_keys;
}

function GetOutputTypeSettingKeys(output_type){
  var all_setting_keys = $("." + output_type).map(function() {
    return this.attributes["id"].value;
  }).get();

  return all_setting_keys;
}



// Save Functions   -----------------------------------------------------------

function SetLocalSettings(){
  var all_device_setting_keys = GetDeviceSettingKeys();

  reloadingCounter = 0;
  reloadingMax = 1; //Device Settings
  reloadingMax += Object.keys(output_types).length; // All output types.

  settings_device = {};
  Object.keys(all_device_setting_keys).forEach(setting_id => {
    var setting_key = all_device_setting_keys[setting_id];
    var setting_value = "";

    var elementIdentifier = "#" + setting_key + ".device_setting_input";
    if($(elementIdentifier).length){
      if($(elementIdentifier).attr('type') == 'checkbox'){
        setting_value = $(elementIdentifier).is(':checked')
      }else if($(elementIdentifier).attr('type') == 'number'){
        setting_value = parseFloat($(elementIdentifier).val());
      }
      else{
        setting_value = $(elementIdentifier).val();
      }
    }

    settings_device[setting_key] = setting_value;

  })

  SetDeviceSetting(currentDevice, settings_device)


  Object.keys(output_types).forEach(output_type_key => {
    var all_output_type_setting_keys = GetOutputTypeSettingKeys(output_type_key);

    settings_output_type = {};

    Object.keys(all_output_type_setting_keys).forEach(setting_id => {
      var setting_key = all_output_type_setting_keys[setting_id];
      var setting_value = "";

      var elementIdentifier = "#" + setting_key + "." + output_type_key;
      if($(elementIdentifier).length){
        if($(elementIdentifier).attr('type') == 'checkbox'){
          setting_value = $(elementIdentifier).is(':checked')
        }else if($(elementIdentifier).attr('type') == 'number'){
          setting_value = parseFloat($(elementIdentifier).val());
        }
        else{
          setting_value = $(elementIdentifier).val();
        }
      }

      settings_output_type[setting_key] = setting_value;


    });

    SetOutputTypeDeviceSetting(currentDevice, output_type_key, settings_output_type)

  });
}


// General Functions   -----------------------------------------------------------

function CreateNewDevice(){

  var data = {};

  $.ajax({
      url: "/CreateNewDevice",
      type: "POST", //send it through get method
      data: JSON.stringify(data, null, '\t'),
      contentType: 'application/json;charset=UTF-8',
      success: function(response) {
          console.log("Create new device successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
          location.reload();
      },
      error: function(xhr) {
        //Do Something to handle error
        console.log("Create new device got an error. Error: " + xhr.responseText);
      }
    });
}

function DeleteDevice(device){

  var data = {};
  data["device"] = device;

  $.ajax({
      url: "/DeleteDevice",
      type: "POST", //send it through get method
      data: JSON.stringify(data, null, '\t'),
      contentType: 'application/json;charset=UTF-8',
      success: function(response) {
          console.log("Delete device successfully. Response:\n\n" + JSON.stringify(response, null, '\t'));
          location.reload();
      },
      error: function(xhr) {
        //Do Something to handle error
        console.log("Delete device got an error. Error: " + xhr.responseText);
      }
    });
}


/* Device Handling */

function BuildDeviceCombobox(){
  var devices = this.devices

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
  text = "Current device: " + this.devices[this.currentDevice]
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

document.getElementById("create1_btn").addEventListener("click",function(e) {
  CreateNewDevice();
});

document.getElementById("create2_btn").addEventListener("click",function(e) {
  CreateNewDevice();
});

document.getElementById("delete_btn").addEventListener("click",function(e) {
  if (confirm('Are you sure you want to delete the device?')) {
    DeleteDevice(currentDevice);
  }

});



