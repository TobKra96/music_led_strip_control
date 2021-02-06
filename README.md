<h1 align="center">
  Music LED Strip Control (MLSC)
</h1>

<p align="center">
    <img src="https://user-images.githubusercontent.com/7833146/105612807-9c287a80-5dbe-11eb-8c25-2212d975a605.png" alt="Logo" />
</p>

<p align="center">
  <a style="text-decoration:none" href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Made%20with-Python-1f425f.svg" alt="made-with-python" />
  </a>
  <a style="text-decoration:none" href="https://discord.gg/jXd5Zxsu/">
    <img src="https://img.shields.io/discord/774182494277992478" alt="Discord" />
  </a>
  <a style="text-decoration:none" href="https://github.com/TobKra96/music_led_strip_control/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/TobKra96/music_led_strip_control" alt="GitHub" />
  </a>
</p>


## Feature List

- Audio visualization in real time.
- Fancy Web interface.
- 23 effects with many configuration options.
- Customizable colors and color schemes.
- Multicore optimized for large LED strips (900+ LEDs).
- Standalone and client compatible for audio processing.


## Demo

<p align="center">
  <a style="text-decoration:none" href="https://youtu.be/DankmP4riOo">
    <img src="https://user-images.githubusercontent.com/7833146/105639512-0e5d9580-5e79-11eb-93f2-2c13456863cd.jpg" alt="Version2_Github" />
  </a>
  <a style="text-decoration:none" href="https://youtu.be/eUSX9l89th0">
    <img src="https://user-images.githubusercontent.com/7833146/105635856-9639a480-5e65-11eb-8126-9e947638e0f2.jpg" alt="Roomtour_Github" />
  </a>
  <a style="text-decoration:none" href="https://youtu.be/jAL1DfeYQI8">
    <img src="https://user-images.githubusercontent.com/7833146/105635961-1bbd5480-5e66-11eb-8608-51aaa9505257.jpg" alt="Version1_Github" />
  </a>
  <a style="text-decoration:none" href="https://github.com/TobKra96/music_led_strip_control/blob/master/media/LEDStripTutorial_WiringDiagram.png">
    <img src="https://user-images.githubusercontent.com/7833146/105613963-22948a80-5dc6-11eb-8cd3-4430521993bf.png" alt="DesktopSmartphone" />
  </a>
</p>


## Installation

### Automated installation
Run the following command in your terminal:
```bash
curl -sSL https://raw.githubusercontent.com/TobKra96/music_led_strip_control/master/setup.sh | sh
```
After the installation completes, please check the [Installation Guide](https://github.com/TobKra96/music_led_strip_control/wiki/Installation-Guide#iv-configure-music-led-strip-control) to configure the initial settings.

### Manual installation
Please see the Installation Guide inside the Wiki: [Installation Guide](https://github.com/TobKra96/music_led_strip_control/wiki/Installation-Guide).

Also, check out the tutorial video I created for the manual installation:

<p align="center">
  <a style="text-decoration:none" href="https://youtu.be/ShpOVoOpqrQ">
    <img src="https://user-images.githubusercontent.com/7833146/106381265-d219c000-63b7-11eb-927d-43b96453d2d2.jpg" alt="Tutorial_Github" />
  </a>
</p>

<p align="center">
    Setup scheme
</p>
<p align="center">
  <a style="text-decoration:none" href="">
    <img src="https://user-images.githubusercontent.com/7833146/104821835-ee0d5580-583e-11eb-8ed7-fbfc4f15a1a1.png" alt="Scheme_02" />
  </a>
</p>


## Used Libraries
 - [Audio Reactive LED Strip by Scott Lawson](https://github.com/scottlawsonbc/audio-reactive-led-strip)
Thank you for the digital signal processing and some effects. You are the best.
- [rpi_ws281x by Jeremy Garff](https://github.com/jgarff/rpi_ws281x)
Awesome library for the led ouput signal. Easy to use.
- [gentelella by Colorlib](https://github.com/ColorlibHQ/gentelella)
Fancy looking bootstrap theme.
Scripts included: Bootstrap, Font Awesome, jQuery-Autocomplete, FullCalendar, Charts.js, Bootstrap Colorpicker, Cropper, dataTables, Date Range Picker for Bootstrap, Dropzone, easyPieChart, ECharts, bootstrap-wysiwyg, Flot, Javascript plotting library for jQuery, gauge.js, iCheck, jquery.inputmask plugin, Ion.RangeSlider, jQuery, jVectorMap, moment.js, Morris.js - pretty time-series line graphs, PNotify - Awesome JavaScript notifications, NProgress, Pace, Parsley, bootstrap-progressbar, select2, Sidebar Transitions - simple off-canvas navigations, Skycons - canvas based wather icons, jQuery Sparklines plugin, switchery - Turns HTML checkbox inputs into beautiful iOS style switches, jQuery Tags Input Plugin, Autosize - resizes text area to fit text, validator - HTML from validator using jQuery, jQuery Smart Wizard
