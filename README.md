

# Music LED Strip Control (MLSC)
Feature List

- Audio visualization in realtime
- Webinterface
- 15 effects with many configuration options
- Customizable colors and color schemes.
- Multicore optimized for large led strips (900+ leds)
- Standalone and client compatible for audio processing
## Preview

![Preview Video](https://raw.githubusercontent.com/TobKra96/music_led_strip_control/master/media/video.gif)

[Link to the video](https://www.youtube.com/watch?v=jAL1DfeYQI8)


![Webinterface Dashboard](https://raw.githubusercontent.com/TobKra96/music_led_strip_control/master/media/webinterface.png)

![Edit Scroll effect with responsive design](https://raw.githubusercontent.com/TobKra96/music_led_strip_control/master/media/webinterface_scroll_edit.png)

## Installation
Requirements:

 - Raspberry Pi 3 or 4 with sd card and power supply
 - LED Strip with WS2812B leds
 - 5V power supply, with enough power for the leds. Each led requires 60 mA.
 - 470 Ω resistor
 - USB sound card for the microphone
 - Microphone

Tested with:
- Raspberry 3 B+
- Raspberry 4 B with 4GB RAM. I think the 2 GB variant would work too.
- Raspbian Buster Lite, version: July 2019
- Raspbian Buster Lite, version: February 2020
- Python 3.7.3

1. Setup hardware. 
- Plugin USB soundcard and microphone.
- Connect the ground and the data pin (Pin 21)

2. Update your libraries
`sudo apt-get update`
`sudo apt-get upgrade`

3. Install python
`sudo apt-get install python3`

4. Clone the github repository.  
Seach for place you want to install the programm. I will use the following location:  
`/share`
You can create a new folder with `sudo mkdir share`
Navigate to your location with `cd /share`  
If you have not yet installed git you can do so with the following command: `sudo apt-get install git`.  
Clone the repository: `sudo git clone https://github.com/TobKra96/music_led_strip_control.git`  
5. Install all python libraries. I use pip for the most packages: `sudo apt-get install python3-pip`  
`pip3 install --upgrade pip`  
`sudo apt-get install libatlas-base-dev`  
`sudo pip3 install -I numpy==1.17.0` 
We need this version, because 1.16 has a memory leak by using queues.  
`sudo pip3 install cython`  
`sudo pip3 install scipy==1.3.0`  
`sudo pip3 install flask`  
`sudo apt-get install portaudio19-dev`  
`sudo pip3 install pyaudio`  
- Install ws281x library:  
`sudo apt-get install build-essential python3-dev git scons swig`  
`sudo git clone https://github.com/jgarff/rpi_ws281x.git`  
`cd rpi_ws281x`  
`sudo scons`  
`cd python`  
`sudo python3 setup.py install`  

6. Setup microphone
	Create/edit `/etc/asound.conf`  
	`sudo nano /etc/asound.conf`  
	Set the file to the following text
	```
	pcm.!default {
	    type hw
	    card 1
	}
	ctl.!default {
	    type hw
	    card 1
	}
	```
	Next, set the USB device to as the default device by editing  `/usr/share/alsa/alsa.conf`
	```
	sudo nano /usr/share/alsa/alsa.conf
	```

	Change

	```
	defaults.ctl.card 0
	defaults.pcm.card 0
	```
	To
	```
	defaults.ctl.card 1
	defaults.pcm.card 1
	```


## Configure MLSC
1. Try to start the programm. Go to the location you cloned the repository. In my installation it was:  
`/share/music_led_strip_control`
	Go to the server component:  
	`cd /share/music_led_strip_control/server`  
	
	To start the programm enter:  
	`sudo python3 main.py`  
2. Now you have to search for your microphone id. Inside the output you should find a list with all available audio sources. It should look like this:
```
Found the following audio sources:
2 - USB Audio Device: - (hw:1,0) - 44100.0
3 - sysdefault - 48000.0
7 - spdif - 44100.0
9 - default - 44100.0
```  
In my case I will use "sysdefault". It has the ID 3.

3. Open the webinterface of MLSC
Search inside your Browser for the hostname of the raspberry pi, or the ip.  
Navigate to "Edit General Settings/Audio Setting".  
There should be an input filed to enter the "Audio Source ID".  
Press "Save".  

4. Now we change the led stip size, to match it with your strip.  
Go to "Edit General Settings/Device Settings".  
Enter the count of LEDs you use inside "Numbers of LEDs".  
Change the mid of your led strip. This will affect the mirror option of many effects.  
You can use the half of your "Numbers of LEDs" or set a custom number, if you got a corner you want to start the mirror effect. You will get the best results with the half of "Numbers of LEDs".  
Press "Save".

5. Restart the programm and have fun with MLSC.

See the wiki for more configuration tutorials.

## Used Libraries

 - [Audio Reactive LED Strip by Scott Lawson](https://github.com/scottlawsonbc/audio-reactive-led-strip)
Thank you for the digital signal processing and some effects. You are the best.
- [rpi_ws281x by Jeremy Garff](https://github.com/jgarff/rpi_ws281x)
Awesome library for the led ouput signal. Easy to use.
- [gentelella by Colorlib](https://github.com/ColorlibHQ/gentelella)
Fancy looking bootstrap theme.
Scripts included: Bootstrap, Font Awesome, jQuery-Autocomplete, FullCalendar, Charts.js, Bootstrap Colorpicker, Cropper, dataTables, Date Range Picker for Bootstrap, Dropzone, easyPieChart, ECharts, bootstrap-wysiwyg, Flot, Javascript plotting library for jQuery, gauge.js, iCheck, jquery.inputmask plugin, Ion.RangeSlider, jQuery, jVectorMap, moment.js, Morris.js - pretty time-series line graphs, PNotify - Awesome JavaScript notifications, NProgress, Pace, Parsley, bootstrap-progressbar, select2, Sidebar Transitions - simple off-canvas navigations, Skycons - canvas based wather icons, jQuery Sparklines plugin, switchery - Turns HTML checkbox inputs into beautiful iOS style switches, jQuery Tags Input Plugin, Autosize - resizes text area to fit text, validator - HTML from validator using jQuery, jQuery Smart Wizard

