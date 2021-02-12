var settingsIdentifier;
var effectIdentifier;
var localSettings = {};
var currentDevice;
var colors = {};
var gradients = {};

var devicesLoading = true;

// Init and load all settings
$( document ).ready(function() {
  $("#device_dropdown").hide();
  settingsIdentifier = $("#settingsIdentifier").val();

  GetLocalSettings();
});


function GetGeneralSetting(setting_key){
  $.ajax({
    url: "/GetGeneralSetting",
    type: "GET", //send it through get method
    data: {
      "setting_key": setting_key,
  },
    success: function(response) {
        ParseGetGeneralSetting(response);
    },
    error: function(xhr) {
      //Do Something to handle error
    }
  });
}

function ParseGetGeneralSetting(response){
  var setting_key = response["setting_key"];
  var setting_value = response["setting_value"];
  localSettings[setting_key] = setting_value;

  SetLocalInput(setting_key, setting_value)
}

function GetLocalSettings(){
  var all_setting_keys = GetAllSettingKeys();

  Object.keys(all_setting_keys).forEach(setting_id => {
    GetGeneralSetting(all_setting_keys[setting_id])
  })

}

function SetLocalInput(setting_key, setting_value){
  if($("#" + setting_key).attr('type') == 'checkbox'){
    if(setting_value){
      $("#" + setting_key).click();
    }

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


function SetGeneralSetting(settings){

    var data = {};
    data["settings"] = settings;

    $.ajax({
      url: "/SetGeneralSetting",
      type: "POST", //send it through get method
      data: JSON.stringify(data, null, '\t'),
      contentType: 'application/json;charset=UTF-8',
      success: function(response) {
          console.log("Set the general sucessfull. Response: " + response.toString());
      },
      error: function(xhr) {
        //Do Something to handle error
        console.log("Set the general setting. Got an error. Error: " + xhr.responseText);
      }
    });

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
      else{
        setting_value = $("#" + setting_key).val();
      }
    }

    settings[setting_key] = setting_value;

  })

  SetGeneralSetting(settings)

}

function ResetSettings(){

  var data = {};

  $.ajax({
      url: "/ResetSettings",
      type: "POST", //send it through get method
      data: JSON.stringify(data, null, '\t'),
      contentType: 'application/json;charset=UTF-8',
      success: function(response) {
          console.log("Reset settings sucessfull. Response: " + response.toString());
          location.reload();
      },
      error: function(xhr) {
        //Do Something to handle error
        console.log("Reset settings got an error. Error: " + xhr.responseText);
      }
    });
}

document.getElementById("save_btn").addEventListener("click",function(e) {
  SetLocalSettings();
});

document.getElementById("reset_btn").addEventListener("click",function(e) {
  if (confirm('Are you sure you want to reset the config? This will need a restart.')) {
    ResetSettings(currentDevice);
  }

});