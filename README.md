

# Music LED Strip Control
Feature List

- Audio visualization in realtime
- Webinterface
- 15 effects with many configuration options
- Customizable colors and color schemes.
- Multicore optimized for large led strips (900+ leds)
- Standalone and client compatible for audio processing
## Preview

![Preview Video](https://raw.githubusercontent.com/ElGammler/music_led_strip_control/master/media/video.gif)
[Link to the video](https://www.youtube.com/watch?v=jAL1DfeYQI8)

![Webinterface Dashboard](https://raw.githubusercontent.com/ElGammler/music_led_strip_control/master/media/webinterface.png)

![Edit Scroll effect with responsive design](https://raw.githubusercontent.com/ElGammler/music_led_strip_control/master/media/webinterface_scroll_edit.png)

## Installation
Requirements:

 - Raspberry Pi 3 B+ with sd card and power supply
 - LED Strip with WS2812B leds
 - 5V power supply, with enough power for the leds. Each led requires 60 mA.
 - 470 Ω resistor
 - USB sound card for the microphone
 - Microphone

Tested with:
- Raspbian Buster Lite, version: July 2019
- Python 3.7.3

1. Setup hardware. 
- Plugin USB soundcard and microphone.
- Connect the ground and the data pin (Pin 21)

2. Update your libraries
`sudo apt-get update`
`sudo apt-get upgrade`

3. Install python
`sudo apt-get python3`

4. Clone the github repository.
Seach for place you want to install the programm. I will use the following location:
`/share`
Navigate to your location with `cd /share`
If you haven't git install it with `sudo apt-get install git`.
Clone the repository: `sudo git clone https://github.com/ElGammler/music_led_strip_control.git`
5. Install all python libraries. I use pip for the most packages: `sudo apt-get install python3-pip`
- `pip3 install --upgrade pip`
- `sudo apt-get install libatlas-base-dev`
- `sudo pip3 install -I numpy==1.17.0` 
We need this version, because 1.16 has a memory leak by using queues.
- `sudo pip3 install cython`
- `sudo pip3 install scipy==1.3.0`
- `sudo pip3 install flask`
- `sudo apt-get install portaudio19-dev`
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

## Used Libraries

 - [Audio Reactive LED Strip by Scott Lawson](https://github.com/scottlawsonbc/audio-reactive-led-strip)
Thank you for the digital signal processing and some effects. You are the best.
- [rpi_ws281x by Jeremy Garff](https://github.com/jgarff/rpi_ws281x)
Awesome library for the led ouput signal. Easy to use.
- [gentelella by Colorlib](https://github.com/ColorlibHQ/gentelella)
Fancy looking bootstrap theme.
Scripts included: Bootstrap, Font Awesome, jQuery-Autocomplete, FullCalendar, Charts.js, Bootstrap Colorpicker, Cropper, dataTables, Date Range Picker for Bootstrap, Dropzone, easyPieChart, ECharts, bootstrap-wysiwyg, Flot, Javascript plotting library for jQuery, gauge.js, iCheck, jquery.inputmask plugin, Ion.RangeSlider, jQuery, jVectorMap, moment.js, Morris.js - pretty time-series line graphs, PNotify - Awesome JavaScript notifications, NProgress, Pace, Parsley, bootstrap-progressbar, select2, Sidebar Transitions - simple off-canvas navigations, Skycons - canvas based wather icons, jQuery Sparklines plugin, switchery - Turns HTML checkbox inputs into beautiful iOS style switches, jQuery Tags Input Plugin, Autosize - resizes text area to fit text, validator - HTML from validator using jQuery, jQuery Smart Wizard

