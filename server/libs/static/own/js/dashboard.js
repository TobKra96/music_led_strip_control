
var activeEffect = "";

$( document ).ready(function() {

    $.ajax({
        url: "/getActiveEffect",
        type: "GET", //send it through get method
        data: { 
            active_effect: true
        },
        success: function(response) {
            activeEffect = response.active_effect;
            setActiveStyle();
        },
        error: function(xhr) {
          //Do Something to handle error
        }
      });
    
});

function setActiveEffect(newActiveEffect){

    removeActiveStyle();
    activeEffect = newActiveEffect;
        
    $.ajax({
        url: "/setActiveEffect",
        type: "POST", //send it through get method
        data: JSON.stringify(activeEffect, null, '\t'),
        contentType: 'application/json;charset=UTF-8',
        success: function(response) {
            console.log("Set the effect sucessfull. Response: " + response.toString());
        },
        error: function(xhr) {
          //Do Something to handle error
          console.log("Set the effect got an error. Error: " + xhr.responseText);
        }
      });

    setActiveStyle();
}

function setActiveStyle(){
    
    $("#" + activeEffect).addClass("active-dashboard-item");
}

function removeActiveStyle(){
    $("#" + activeEffect).removeClass("active-dashboard-item");
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
    }else if(e.target && e.target.nodeName == "SPAN"){
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