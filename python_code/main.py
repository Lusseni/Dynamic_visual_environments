#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 23 13:57:47 2025

@author: herttaleinonen

Handles Eyelink connection, calibration and EDF data and calls for a task script in the end 
"""

from __future__ import division, print_function
import pylink
import os
import platform
import time
import sys
import numpy as np
from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
from psychopy import visual, core, event, monitors, gui
from string import ascii_letters, digits

from dynamic_task import run_dynamic_trials  # <-- Dynamic task imported here
from static_task import run_static_trials  # <-- Static task imported here
from evading_target_static_task import run_evading_target_static_trials # <-- Static evading target task imported here
from visibility_task import run_visibility_trials # <-- Visibility task imported here

from flicker_static_task import run_flicker_static_trials  # <-- Static flicker task imported here
from flicker_dynamic_task import run_flicker_dynamic_trials  # <-- Dynamic flicker task imported here
from window_static_task import run_window_static_trials # <-- Static window task imported here
from window_dynamic_task import run_window_dynamic_trials # <-- Dynamic window task imported here
from following_target_dynamic_task import run_following_target_dynamic_trials # <-- Dynamic evading target task imported here

# --- Setup ---
dummy_mode = False
full_screen = True

# Prompt EDF file name
dlg_title = "Enter EDF Filename"
dlg_prompt = "Please enter a file name with 8 or fewer characters [letters, numbers, and underscore]."

# Loop until a valid file name is entered
while True:
    dlg = gui.Dlg(dlg_title)
    dlg.addText(dlg_prompt)
    dlg.addField("Filename", initial="Test", label="EDF Filename")
    # show dialog until OK or Cancel
    ok_data = dlg.show()
    if dlg.OK:
        tmp_str = ok_data["Filename"].rstrip().split(".")[0]
        if all(c in ascii_letters + digits + '_' for c in tmp_str) and len(tmp_str) <= 8:
            edf_fname = tmp_str
            break
        else:
            print("Invalid EDF filename")
    else:
        core.quit()
        sys.exit()

# Setup folder structure for EDF data
results_folder = 'results'
os.makedirs(results_folder, exist_ok=True)
time_str = time.strftime("_%Y_%m_%d_%H_%M", time.localtime()) # download EDf file from Host PC to local hard drive
session_identifier = edf_fname + time_str
session_folder = os.path.join(results_folder, session_identifier)
os.makedirs(session_folder, exist_ok=True)

# Step 1:
# Connect to EyeLink
if dummy_mode:
    el_tracker = pylink.EyeLink(None)
else:
    try:
        el_tracker = pylink.EyeLink("100.1.1.1")
    except RuntimeError as error:
        print('ERROR:', error)
        core.quit()
        sys.exit()

# Step 2:
# Open an EDF data file on the host PC 
edf_file = edf_fname + ".EDF"
el_tracker.openDataFile(edf_file)
# add a header to the EDF file
el_tracker.sendCommand(f"add_file_preamble_text 'RECORDED BY {os.path.basename(__file__)}'")

# Step 3:
# Configure the tracker
el_tracker.setOfflineMode()

# Get the software version
eyelink_ver = 5  # set version to 0, in case running in Dummy mode
if not dummy_mode:
    vstr = el_tracker.getTrackerVersionString()
    eyelink_ver = int(vstr.split()[-1].split('.')[0])
    # print out some version info in the shell
    print('Running experiment on %s, version %d' % (vstr, eyelink_ver))

# File and Link data control
# what eye events to save in the EDF file, include everything by default
file_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON,INPUT'
# what eye events to make available over the link, include everything by default
link_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON,FIXUPDATE,INPUT'
# what sample data to save in the EDF data file and to make available
# over the link, include the 'HTARGET' flag to save head target sticker
# data for supported eye trackers
if eyelink_ver > 3:
    file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,HTARGET,GAZERES,BUTTON,STATUS,INPUT'
    link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,HTARGET,STATUS,INPUT'
else:
    file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,GAZERES,BUTTON,STATUS,INPUT'
    link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS,INPUT'
el_tracker.sendCommand("file_event_filter = %s" % file_event_flags)
el_tracker.sendCommand("file_sample_data = %s" % file_sample_flags)
el_tracker.sendCommand("link_event_filter = %s" % link_event_flags)
el_tracker.sendCommand("link_sample_data = %s" % link_sample_flags)

# Tracker config
el_tracker.sendCommand("calibration_type = HV5")
el_tracker.sendCommand("button_function 5 'accept_target_fixation'")

# Step 4:
# Set up a graphics environment for calibration
# Setup a screen
'''
mon = monitors.Monitor('myMonitor', width=48.0, distance=70.0) # custom dimensions
win = visual.Window(fullscr=full_screen, monitor=mon, winType='pyglet', units='pix')
# get the native screen reso used by PsychoPy
scn_width, scn_height = win.size
'''

mon = monitors.Monitor('ViewPixx', 
                    width=48.0, 
                    distance=70.0) # custom dimensions
                        
mon.setSizePix((1920, 1080))

#mon.setActualFrameRate(120.0)

win = visual.Window(
                    fullscr=True,
                    monitor=mon,
                    units='pix',
                    winType='pyglet'
)
scn_width, scn_height = win.size

actual_fps = 30.0

# Pass the display pixel coordinates (left, top, right, bottom) to the tracker
el_coords = "screen_pixel_coords = 0 0 %d %d" % (scn_width - 1, scn_height - 1)
el_tracker.sendCommand(el_coords)

# Write a DISPLAY_COORDS message to the EDF file
dv_coords = "DISPLAY_COORDS  0 0 %d %d" % (scn_width - 1, scn_height - 1)
el_tracker.sendMessage(dv_coords)

# Calibration
# configure a graphics environment for calibration
genv = EyeLinkCoreGraphicsPsychoPy(el_tracker, win) 

# Set backgroud and foreground colours for the calibration target
genv.setCalibrationColors((-1, -1, -1), win.color)
# use a picture as the calibration target
genv.setTargetType('picture')
genv.setPictureTarget(os.path.join('images', 'fixTarget.bmp'))

# Request pylink to use the PsychoPy window opened above for calibration
pylink.openGraphicsEx(genv)


# Show calibration instructions on screen
def show_msg(text):
    msg = visual.TextStim(win, text, color=(-1, -1, -1), wrapWidth=scn_width / 2)
    win.flip()
    msg.draw()
    win.flip()
    event.waitKeys()
    win.flip()

msg = 'Press ENTER twice to start calibration.'
show_msg(msg)

# Do camera setup
if not dummy_mode:
    try:
        el_tracker.doTrackerSetup()
    except RuntimeError as err:
        print('ERROR:', err)
        el_tracker.exitCalibration()
        

# --- Step 6: Run dynamic trials ---
# Calls class from task file 
# Remember to comment out the ones you are not using
"""
run_dynamic_trials(
    win=win,
    el_tracker=el_tracker,
    screen_width=scn_width,
    screen_height=scn_height,
    participant_id=edf_fname,
    timestamp=session_identifier
)

run_static_trials(
    win=win,
    el_tracker=el_tracker,
    screen_width=scn_width,
    screen_height=scn_height,
    participant_id=edf_fname,
    timestamp=session_identifier
)

run_flicker_static_trials(
    win=win,
    el_tracker=el_tracker,
    screen_width=scn_width,
    screen_height=scn_height,
    participant_id=edf_fname,
    timestamp=session_identifier
)

run_flicker_dynamic_trials(
    win=win,
    el_tracker=el_tracker,
    screen_width=scn_width,
    screen_height=scn_height,
    participant_id=edf_fname,
    timestamp=session_identifier
)


run_window_static_trials(
    win=win,
    el_tracker=el_tracker,
    screen_width=scn_width,
    screen_height=scn_height,
    participant_id=edf_fname,
    timestamp=session_identifier
)


run_window_dynamic_trials(
    win=win,
    el_tracker=el_tracker,
    screen_width=scn_width,
    screen_height=scn_height,
    participant_id=edf_fname,
    timestamp=session_identifier
)


run_following_target_static_trials(
    win=win,
    el_tracker=el_tracker,
    screen_width=scn_width,
    screen_height=scn_height,
    participant_id=edf_fname,
    timestamp=session_identifier
)
"""
run_evading_target_static_trials(
    win=win,
    el_tracker=el_tracker,
    screen_width=scn_width,
    screen_height=scn_height,
    participant_id=edf_fname,
    timestamp=session_identifier
)
"""

# after calibration & EyeLink setup:
csv_file = run_visibility_trials(
    win, el_tracker, scn_width, scn_height,
    edf_fname, session_identifier
)
print("Visibility data saved:", csv_file)
run_visibility_trials( 
    win=win,
    el_tracker=el_tracker,
    screen_width=scn_width,
    screen_height=scn_height,
    participant_id=edf_fname,
    timestamp=session_identifier
)
"""
# --- Step 7: Download and close ---
def terminate_task():
    if el_tracker.isConnected():
        if el_tracker.isRecording():
            el_tracker.stopRecording()
        el_tracker.setOfflineMode()
        el_tracker.sendCommand('clear_screen 0') 
        pylink.msecDelay(500)
        el_tracker.closeDataFile()

        print('EDF data is transferring from EyeLink Host PC...')
        #show_msg(msg)
        # Download the EDF data file from the host PC to a local data folder
        local_edf = os.path.join(session_folder, session_identifier + '.EDF')
        try:
            el_tracker.receiveDataFile(edf_file, local_edf)
        except RuntimeError as error:
            print('ERROR:', error)
        # Close the link to the tracker
        el_tracker.close()
        
    thank_you_msg = visual.TextStim(
        win, 
        text = "The experiment is now over. Thank you for participating! Press ESC to close the window.", 
        color="white", 
        height = 30,
        wrapWidth=win.size[0] * 0.8
    )
    
    while True:
        thank_you_msg.draw()
        win.flip()
        if "escape" in event.getKeys():
            break
    # Close PsychoPy window and quit
    win.close()
    core.quit()
    sys.exit()
  

terminate_task()
