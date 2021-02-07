#!/bin/bash

# Setup script for MLSC
# https://github.com/TobKra96/music_led_strip_control


INST_DIR="/share" # Installation location
PROJ_DIR="music_led_strip_control" # Project location
PROJ_NAME="MLSC" # Project abbreviation
ASOUND_DIR="/etc/asound.conf" # Asound config location
ALSA_DIR="/usr/share/alsa/alsa.conf" # Alsa config location


# Confirm action before proceeding.
confirm() {
    while true; do
        read -p "$(prompt -w "$*? [y/N] ")" yn
        case $yn in
            [Yy]*) prompt -s "Proceeding..."; return 0;;
            [Nn]*) prompt -i "Skipped."; return 1;;
            [Qq]*) prompt -e "Setup exited."; exit 0;;
            '') prompt -i "Skipped."; return 1;;
        esac
    done
}


echo "Installing $PROJ_NAME..."

# Update packages:
sudo apt-get update
sudo apt-get -y upgrade

# Install Git:
sudo apt-get -y install git

# Install Audio Driver:
sudo apt-get -y install libatlas-base-dev portaudio19-dev

# Install Python and required packages for it:
sudo apt-get -y install python3 python3-pip python3-scipy  # Fallback scipy module if the Pip module fails to install.


# Install required Python modules:
sudo pip3 install --no-input --upgrade pip     # Upgrade Pip to the latest version.
sudo pip3 install --no-input -I numpy==1.17.0  # Offers a lot of mathematical functions and matrix manipulation. This version is required because 1.16 has a memory leak when using queues.
sudo pip3 install --no-input rpi_ws281x        # Raspberry Pi PWM library for WS281X LEDs.
sudo pip3 install --no-input flask             # The webserver component.
sudo pip3 install --no-input pyaudio           # Offer the audio input stream, which will be processed.
sudo pip3 install --no-input scipy==1.3.0      # Offers a Gaussian filter.


# Install MLSC:
if [ ! -d $INST_DIR ]; then
	sudo mkdir $INST_DIR
fi
cd $INST_DIR

if [ -d $PROJ_DIR ]; then
    confirm '${PROJ_NAME} is already installed. Do you want to reinstall it'
    if [[ $? -eq 0 ]]; then
	    sudo mv $PROJ_DIR "${PROJ_DIR}_bak" # Backup previous MLSC installation.
        sudo git clone https://github.com/TobKra96/music_led_strip_control.git
        sudo cp music_led_strip_control_bak/server/libs/config.json music_led_strip_control/server/libs/config.json  # Restore config after reinstalling.
else
    sudo git clone https://github.com/TobKra96/music_led_strip_control.git
fi


# Setup microphone:
if [ ! -f $ASOUND_DIR ]; then
    sudo touch $ASOUND_DIR
else
    sudo mv $ASOUND_DIR "$ASOUND_DIR.bak"
fi
sudo echo -e 'pcm.!default {\n    type hw\n    card 1\n}\nctl.!default {\n    type hw\n    card 1\n}' > $ASOUND_DIR

if [ ! -f $ALSA_DIR ]; then
    sudo touch $ALSA_DIR
else
    sudo cp $ALSA_DIR "$ALSA_DIR.bak"
fi
sudo sed -i '/defaults.ctl.card 0/c\defaults.ctl.card 1' $ALSA_DIR
sudo sed -i '/defaults.pcm.card 0/c\defaults.pcm.card 1' $ALSA_DIR

sudo sed -e '/pcm.front cards.pcm.front/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.rear cards.pcm.rear/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.center_lfe cards.pcm.center_lfe/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.side cards.pcm.side/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.surround21 cards.pcm.surround21/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.surround40 cards.pcm.surround40/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.surround41 cards.pcm.surround41/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.surround50 cards.pcm.surround50/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.surround51 cards.pcm.surround51/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.surround71 cards.pcm.surround71/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.iec958 cards.pcm.iec958/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.spdif iec958/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.hdmi cards.pcm.hdmi/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.dmix cards.pcm.dmix/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.dsnoop cards.pcm.dsnoop/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.modem cards.pcm.modem/ s/^#*/#/' -i $ALSA_DIR
sudo sed -e '/pcm.phoneline cards.pcm.phoneline/ s/^#*/#/' -i $ALSA_DIR


echo -e "\n${PROJ_NAME} installation is done. Please reboot your system (sudo reboot)."