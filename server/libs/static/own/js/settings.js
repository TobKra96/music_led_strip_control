var allSettings;
var deviceSettings;
var currentSettings;
var settingsIdentifier;

// Init and load all settings
$( document ).ready(function() {
    this.settingsIdentifier = $("#settingsIdentifier").val();

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

function setSettings(){
  this.settingsIdentifier = $("#settingsIdentifier").val();
  // Refresh the settings variable.
  this.parseToSettings()
  
  var data = {};
  data["settings"] = this.allSettings;
  data["device"] = this.currentDevice;
  data["effect"] = this.settingsIdentifier;

  $.ajax({
    url: "/setSettings",
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
}


// Parse from the settings variable to the elements inside the html page.
// (get settings)
function parseFromSettings(allSettings){
  this.settingsIdentifier = $("#settingsIdentifier").val();
  this.allSettings = allSettings;

  this.BuildDeviceCombobox();
  this.AddEventListeners();

  buildComboboxes();
  this.UpdateCurrentDevice("all_devices");
 
}


// Parse from the HTML page (elements) to the settings variable.
// (set settings)
function parseToSettings(){
  this.settingsIdentifier = $("#settingsIdentifier").val();

    Object.keys(this.currentSettings).forEach(currentSettingKey =>{
      if($("#" + currentSettingKey).length){
        if($("#" + currentSettingKey).attr('type') == 'checkbox'){
          this.currentSettings[currentSettingKey] = $("#" + currentSettingKey).is(':checked')
        }else if($("#" + currentSettingKey).attr('type') == 'number'){
          this.currentSettings[currentSettingKey] = parseFloat($("#" + currentSettingKey).val());
        }
        else{
          this.currentSettings[currentSettingKey] = $("#" + currentSettingKey).val();
        }
      }
    })

    if(this.settingsIdentifier == 'audio_settings'){
      this.allSettings['audio_config'] = this.currentSettings
    }else
    {
      if(this.currentDevice == "all_devices"){
        var device_configs = this.allSettings["device_configs"]

        Object.keys(device_configs).forEach(device => {
          if(this.settingsIdentifier == 'device_settings'){
            var clone = JSON.parse(JSON.stringify(this.currentSettings));
            this.allSettings['device_configs'][device] = clone;
          }
          else
          {
            var clone = JSON.parse(JSON.stringify(this.currentSettings));
            this.allSettings['device_configs'][device]['effects'][this.settingsIdentifier] = clone;
          }
        });
        
      }
      else
      {
        if(this.settingsIdentifier == 'device_settings'){
          this.allSettings['device_configs'][this.currentDevice] = this.currentSettings
        }
        else
        {
          this.allSettings['device_configs'][this.currentDevice]['effects'][this.settingsIdentifier] = this.currentSettings
        }
      }
    }
    
    
}

// Build all Comboboxes, we need out of "allSettings".
function buildComboboxes(){
  var context = this;
  $('.colours').each(function(){
    var colours = context.allSettings['colours'];
    for(var currentKey in colours){
      var newOption = new Option(currentKey, currentKey);
      /// jquerify the DOM object 'o' so we can use the html method
      $(newOption).html(currentKey);
      $(this).append(newOption);
    }
  });

  $('.gradients').each(function(){
    var gradients = context.allSettings['gradients'];
    for(var currentKey in gradients){
      var newOption = new Option(currentKey, currentKey);
      /// jquerify the DOM object 'o' so we can use the html method
      $(newOption).html(currentKey);
      $(this).append(newOption);
    }
  });
}


function resetSettings(){

  var r = confirm("Do you really want to reset the settings?");
  if (r == false) {
    return;
  }

  var message = "resetSettings";
  $.ajax({
    url: "/reset_settings/reset",
    type: "POST", //send it through get method
    data: JSON.stringify(message, null, '\t'),
    contentType: 'application/json;charset=UTF-8',
    success: function(response) {
        console.log("Set settings were resetted successful. Response: " + response.toString());
    },
    error: function(xhr) {
      //Do Something to handle error
      console.log("Could not reset the settings. Error: " + xhr.responseText);
    }
  });

  location.reload();
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
  if(this.currentDevice == "all_devices"){
      text = "Current device: All Devices"
  }
  else
  {
      text = "Current device: " + this.allSettings["device_configs"][currentDevice]["DEVICE_NAME"]
  }
  
  $("#selected_device_txt").text(text);

  if(this.settingsIdentifier == 'audio_settings')
  {
    this.currentSettings = this.allSettings['audio_config']
  }
  else
  {
    if(this.currentDevice == "all_devices")
    {
      if(this.settingsIdentifier == 'device_settings')
      {
        this.currentSettings = this.allSettings['default_device']
      }
      else
      {
        this.currentSettings = this.allSettings['default_device']['effects'][this.settingsIdentifier]
      }
    }
    else
    {
      if(this.settingsIdentifier == 'device_settings')
      {
        this.currentSettings = this.allSettings['device_configs'][this.currentDevice]
      }
      else
      {
        this.currentSettings = this.allSettings['device_configs'][this.currentDevice]['effects'][this.settingsIdentifier]
      }
    }
  }

  

  if(this.currentSettings == null){
    // Coulr not find the settings
    return;
  }

  Object.keys(this.currentSettings).forEach(currentSettingKey =>{
    if($("#" + currentSettingKey).attr('type') == 'checkbox'){
      if(this.currentSettings[currentSettingKey]){
        $("#" + currentSettingKey).click();
      }
      
    }else{
      $("#" + currentSettingKey).val(this.currentSettings[currentSettingKey]);
    }
    
    $("#" + currentSettingKey).trigger('change');
  })
}

function SwitchDevice(e){
  var newDeviceId = e.target.id;

  this.UpdateCurrentDevice(newDeviceId);
}

document.getElementById("save_btn").addEventListener("click",function(e) {
  setSettings();
});


function Clone(source) {
  if (Object.prototype.toString.call(source) === '[object Array]') {
      var clone = [];
      for (var i=0; i<source.length; i++) {
          clone[i] = goclone(source[i]);
      }
      return clone;
  } else if (typeof(source)=="object") {
      var clone = {};
      for (var prop in source) {
          if (source.hasOwnProperty(prop)) {
              clone[prop] = goclone(source[prop]);
          }
      }
      return clone;
  } else {
      return source;
  }
}