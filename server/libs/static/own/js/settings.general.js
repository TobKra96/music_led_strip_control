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


function SetGeneralSetting(setting_key, setting_value){

    var data = {};
    data["setting_key"] = setting_key;
    data["setting_value"] = setting_value;

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

    SetGeneralSetting(setting_key, setting_value)
  })

}

document.getElementById("save_btn").addEventListener("click",function(e) {
  SetLocalSettings();
});