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

document.getElementById("save_btn").addEventListener("click",function(e) {
  setSettings();
});


function setSettings(){
  this.settingsIdentifier = $("#settingsIdentifier").val();
  // Refresh the settings variable.
  this.parseToSettings()
  
  var data = {};
  data.settingsIdentifier = this.settingsIdentifier;
  data.settings = this.allSettings;

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

  buildComboboxes();

  if(this.settingsIdentifier == 'device_settings'){
    this.currentSettings = this.allSettings['device_config']
  }
  else if(this.settingsIdentifier == 'audio_settings'){
    this.currentSettings = this.allSettings['audio_config']
  }
  else{
    this.currentSettings = this.allSettings['effects'][this.settingsIdentifier]
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

