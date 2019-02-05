# run instruction: python run_arc.py

import pygame
import numpy
import sys
import os

import time
import numpy as np
import random
import datetime

import scipy
    
from threading import Thread

from aux import *

DEBUG = True
if DEBUG:
    import robot.dummy as robot # for debug/development
else:
    import robot.interface as robot # for real testing

import subprocess

PYTHON3 = (sys.version_info > (3, 0))
if PYTHON3: # this really is tested on Python 3 so please use that
    from tkinter import *
    from tkinter import messagebox as tkMessageBox
    from tkinter import filedialog
    import tkinter.simpledialog as tksd
    from tkinter import messagebox

else: # python2
    from Tkinter import * # use for python2
    import tkMessageBox
    from Tkinter import filedialog
    import tkSimpleDialog as tksd
    
import json
import pandas as pd



from mouse import *


# The little control window
CONTROL_WIDTH,CONTROL_HEIGHT= 500,550 #1000,800 #450,400 # control window dimensions
CONTROL_X,CONTROL_Y = 500,50 # controls where on the screen the control window appears


EXPERIMENT = "sensoryshift"



numpy.random.seed() # make sure we're really random

# This is a global dict that holds all the configuration options. 
# Using a single variable for them makes it easier to keep track.
global conf
conf = {}


conf['N_ROBOT_LOG'] = 13 # how many columns go in the robot log file


conf['n_center_capture']=100 # how many samples to collect when capturing the center
conf['center_capture_period']=.01 # how long to wait between capturing samples for establishing the center


conf['fullscreen']=False

# The background of the screen
conf["bgcolor"] = (0,0,0)

# The size of the window (for pygame)
conf["screensize"] = (1920,1080) # inmotion screen
conf["screenpos"] = (1600,0) # the offset (allows you to place the subject screen "on" the second monitor)



# Read the screen-to-robot calibration from file
conf['calibfile']='calib.json'
if not os.path.exists(conf['calibfile']):
    print("## ERROR: cannot find screen calibration. You may want to run screencalib.py and save the calibration as %s"%conf['calibfile'])
    sys.exit(-1)
_,conf["calib"] = json.load(open(conf['calibfile'],'r')) #, encoding='latin1') if PYTHON3 else pickle.load(open('calib.pickle27','rb'))




# The sizes of various objects
conf["cursor_radius"] = .0035 # in robot coordinates (m)

# this is the display size of the target, not the size of the target area used for determining whether subjects are long enough "within" the target.
conf["target_radius"] = .0075
conf["target_colour"]  = (0,0,255)

# the marker for the center
conf['center_marker_radius']=.0075
conf['center_marker_colour']=(100,100,100)

# The cursor colour
conf["active_cursor_colour"]  = (0,255,0)
conf["passive_cursor_colour"] = (255,0,0)


# The radius of the movement
conf['movement_radius']=.15 # meters

conf['target_overshoot_SD']=.01 # in meters, the SD of the overshoot/undershoot of the target in passive trials
conf['target_overshoot_ask_p']=.99 # percentage of passive trials where we will randomly ask whether the cursor overshot or not


conf['robot_center']= (0,-.05) # robot center position
conf['robot_center_x'],conf['robot_center_y']=conf["robot_center"]  # just because we often need these separately as well


# The extent of the arc being displayed on the screen when the
# subject selects the placement of the hand
# This is in angles, degrees, with 0 = straight ahead, and positive angles are counterclockwise
conf['arc_range']= (-45,45)

conf['arc_draw_segments'] = 100 # how many segments to draw the arc (higher=more precision but takes more resources)
conf['arc_thickness']     = .001 # how thick to draw the 'selector' arc
conf['arc_colour']        = (80,80,80) # colour of the arc selector


conf['selector_radius']=.005 # the radius of the selector ball that is controlled by the joystick
conf['selector_colour']=(100,100,255)


# How long to take for the return movement
conf['return_duration']=1.5 # seconds

# How long to take for the passive movements
conf['passive_duration']=1.5 # seconds

conf['stay_duration']=1 # how long to stay "out there" in between forward and backward movement



# Range of the joystick values
# anything outside this range is snapped to the edges
conf['use_joystick']=False
conf['max_joystick']= 1
conf['min_joystick']= 0



conf['use_mouse']=True
conf['mouse_device']='/dev/input/by-id/usb-Kensington_Kensington_USB_PS2_Orbit-mouse'
#conf['mouse_device']='/dev/input/by-id/usb-Microsoft_Microsoft_5-Button_Mouse_with_IntelliEye_TM_-mouse'
conf['mouse_selector_tick']=.0005 # how much to change the selector (range 0..1) for one mouse 'tick' (this determines the maximum precision)



# The controller that can be used for the fade duration
conf['fade_controller'] = 5
conf['fade_duration']=.5 # how long to fade when holding at the starting point
conf['fade_cue_colour']=(255,0,0) # the colour of the cursor while holding still (fading forces)

#conf['move_cue_colour']=(0,255,0) # the colour of the cursor when ready to move
conf['move_controller'] = 6


# Note that these phase numbers are not necessarily incremental...
conf['phases']=['init',
                'return',
                'forward',
                'backward',
                'completed',
                'move', 
                'endmove',
                'select',
                'fade',
                'stay',
                'hold',
                'ask'
]



# Data that is specific to this trial
trialdata = {}





def conv_ang(a):
    """ Angles in this experiment are generally given in degrees
    w.r.t. straight ahead, just because that's simpler.
    But then sin and cos like to have them in radians, relative
    to straight right. So here we do that translation."""
    return ((a+90)/180)*np.pi
    


    

def draw_arc_selector():
    """ Draw the arc on the screen along which the subjects can
    choose the felt position of the hand."""

    conf['screen'].fill(conf['bgcolor'])

    mna,mxa = conf['arc_range']
    minang,maxang = conv_ang(mna),conv_ang(mxa) # convert into usable angles
    angs = np.linspace(minang,maxang,conf['arc_draw_segments'])

    # Now make an inner and outer arc
    cx,cy = conf['robot_center']
    points = []
    for sgn in [-.5,.5]:
        rad = conf['movement_radius']-sgn*conf['arc_thickness']
        p = [ (cx+rad*np.cos(a),cy+rad*np.sin(a)) for a in angs ]
        if sgn<0: p.reverse()
        points += p


    # And then plot a polygon!
    poly = [ robot_to_screen(ry,rz,conf) for (ry,rz) in points ]
    pygame.draw.polygon( conf['screen'],conf['arc_colour'],poly)

    
    if 'selector_angle' in trialdata:
        #print(conf['selector_position'])
        pos = position_from_angle(conv_ang(trialdata['selector_angle']))
        draw_ball(conf['screen'],pos,conf['selector_radius'],conf['selector_colour'])
        

    



    
def draw_ball(surface,pos,radius,colour):
    """
    Draw one of the two target "balls" (at the edges of the arc)

    Arguments
    sgn is whether this is the left or right direction.
    colour is the draw colour
    """

    # Draw the two target balls
    #for sgn in [-1,1]:
    #tx,ty = conf["ARC_BASE_X"]+sgn*conf["ARC_RADIUS"],conf["ARC_BASE_Y"]
    tx,ty=pos
    x1,y1 = robot_to_screen(tx-radius,ty-radius, conf)
    x2,y2 = robot_to_screen(tx+radius,ty+radius, conf)
    minx=min(x1,x2)
    maxx=max(x1,x2)
    miny=min(y1,y2)
    maxy=max(y1,y2)
    pygame.draw.ellipse(surface,colour,#conf["ARC_COLOUR"],
                        [minx,miny,maxx-minx,maxy-miny])




    
def pinpoint():
    """ Select a position on the screen using the joystick."""
    # Start the main loop
    trialdata['redraw']=True
    launch_mainloop()





def hold_fade():
    """ Hold and fade the robot handle """
    robot.wshm('traj_count',          0) # ensure that we start recording at the beginning of the trajectory buffer
    robot.wshm('fvv_workspace_enter', 0) # initialise: signal that the subject has not yet entered the workspace
    robot.wshm('fvv_robot_center_x', conf['robot_center_x'])
    robot.wshm('fvv_robot_center_y', conf['robot_center_y'])
    robot.wshm('plg_p1x',            conf['robot_center_x']) # the position for the initial hold
    robot.wshm('plg_p2x',            conf['robot_center_y'])
    robot.wshm("fvv_force_fade",      1.0) # This starts at 1.0 but exponentially decays to infinitely small
    robot.wshm("plg_stiffness",       robot.stiffness)
    robot.wshm("plg_damping",         robot.damping)

    robot.controller(conf['fade_controller'])
    


    
    
def launch_mainloop():
    conf['thread']=Thread(target=mainloop)
    conf['thread'].start()
    
    



def get_selector_prop(pos):
    """ Map the joystick position to a position of a selector on the screen."""

    # Determine the joystick position on a range from 0 to 1
    joy = pos[0]
    joyrel = (joy-conf['min_joystick'])/(conf['max_joystick']-conf['min_joystick'])
    if joyrel<0: joyrel=0
    if joyrel>1: joyrel=1
    #print(joyrel)

    return joyrel
     



def update_selector(dpos):
    """ Given a mouse move event (change in x, change in y),
    update the selector value."""
    dchange = sum(dpos)*conf['mouse_selector_tick']
    p = trialdata['selector_prop']+dchange
    p = p%1
    trialdata['selector_prop']=p
    selector_to_angle()



def selector_to_angle():
    """ Map a value in the selector range (0..1) to an actual angle (in deg) """
    prop = trialdata.get('selector_prop',None)
    if prop:
        mn,mx = conf['arc_range']
        a = mn+(mx-mn)*prop
        trialdata['selector_angle']=a

        ## Add this to the history of selections
        hist = trialdata.get('selector_history',[])
        if len(hist)==0 or hist[-1]!=a:
            hist.append(a)
        trialdata['selector_history']=hist
    
    

    

def get_joystick():
    """ Get the current position of the joystick."""
    joystick = conf['joystick']
    pos = [ joystick.get_axis( i ) for i in range(2) ] # get the first two axes
    if 'joystick_history' in trialdata:
        if len(trialdata['joystick_history'])==0 or pos!=trialdata['joystick_history'][-1]:
            trialdata['joystick_history'].append(pos) # TODO: make sure we clear the joystick history also!
    trialdata['selector_prop']=get_selector_prop(pos) # update the selector position
    selector_to_angle()
    return pos
    




def current_schedule():
    # Return the item that is currently scheduled
    if 'current_schedule' not in trialdata or trialdata['current_schedule']==-1: return None
    return trialdata['schedule'][trialdata['current_schedule']]


def phase_is(p):
    # Return whether the current phase is p
    return trialdata.get('phase',None)==p

def phase_in(phases):
    # Return whether the current phase is p
    return trialdata.get('phase',None)in phases




def start_new_trial():
    """ Initiate a new trial. """
    if trialdata['current_schedule']==len(trialdata['schedule'])-1:
        # Done the experiment!
        print("## BLOCK COMPLETED ##")
        robot.move_to(conf['robot_center_x'],conf['robot_center_y'],conf['return_duration'])
        while not robot.move_is_done():
            time.sleep(.1)
        robot.stay() # just fix the handle wherever it is
        next_phase('completed')
        gui['keep_going'] = False # this will bail out of the main loop
        gui['running'] = False
        time.sleep(1) # wait until some last commands may have stopped
        close_logs()
        update_ui()
        # Now ask the experimenter for observations
        #obsv = tksd.askstring('Please record any observations', 'Experimenter, please write down any observations.\nAny irregularities?\nDid the subject seem concentrated or not?\nWere things unclear or clear?\nAnything else that is worth noting?')
        #with open(conf['obsvlog'],'w') as f:
        #    f.write(obsv)

        tkMessageBox.showinfo("Robot", "Block completed! Yay!")
        return


    # Okay, if that wasn't the case, we can safely start our new trial
    trialdata['current_schedule']+=1


    sched = current_schedule() # Retrieve the current schedule
    trialdata['trial']           =sched['trial'] # trial number
    trialdata['type']            =sched['type']
    trialdata['target.direction']=sched['target.direction']  # display angle of the target
    trialdata['mov.direction']   =sched['mov.direction']     # physical angle of movement
    trialdata['cursor.rotation'] =sched['cursor.rotation']   # rotation applied to cursor before display
    trialdata['position_history']=[] # start with a clean position history (we'll fill this up during active trials only)

    for v in ['vmax_x','vmax_y','final_x','final_y']:
        trialdata[v]=None

    print("\n\n\n### TRIAL %d %s ###"%(trialdata['trial'],trialdata['type']))
    print("    target: %.2f  movement: %.2f  rotation: %.2f deg\n"%(trialdata['target.direction'],trialdata['mov.direction'],trialdata['cursor.rotation']))
    robot.wshm('fvv_trial_no',     trialdata['trial'])

    ## Return the robot to the center
    sx,sy = conf['robot_center']
    robot.move_to(sx,sy,conf['return_duration'])
    next_phase('return') # return to the starting point to start the trial
    
    



def record_position(x,y):
    # trialdata['position_history'].append((x,y)) # let's not do this -- we can use the info captured from the robot itself
    pass



def position_from_angle(a,radius=None):
    """ Return the position based on the angle, relative to the starting point
    and assuming a movement of a standard radius."""
    if radius==None:
        radius = conf['movement_radius']        
    cx,cy = conf['robot_center']
    pos = (cx+radius*np.cos(a),cy+radius*np.sin(a))
    return pos



def start_move_controller():
    robot.wshm('fvv_move_done',0) # we'll set this to one once the movement is completed
    robot.wshm('fvv_max_vel',0)
    robot.wshm('fvv_vmax_x',0)
    robot.wshm('fvv_vmax_y',0)
    robot.wshm('fvv_vel_low_timer',0)
    robot.controller(conf['move_controller'])
    




def record_plot():
    """ Make a plot of the trajectory we recorded from the robot."""
    if not 'captured' in trialdata:
        print("Nothing captured")
        return
    
    traj = trialdata['captured']
    #trajx,trajy = zip(*traj) # unzip!
    plot = pygame.Surface(conf['screensize'])
    plot.fill(conf['bgcolor'])

    # Draw start position
    draw_ball(plot,conf['robot_center'],conf['center_marker_radius'],conf['center_marker_colour'])
    # Draw target
    if 'target_position' in trialdata and not trialdata['type']=='pinpoint': # We show a target always, only not if this is a pinpoint trial
        draw_ball(plot,trialdata['target_position'],conf['target_radius'],conf['target_colour'])
    
    points = [ robot_to_screen(x,y,conf) for x,y in traj ]
    pygame.draw.lines(plot,(255,255,255),False,points,3)
    fname = 'sneak_peek.bmp'
    pygame.image.save(plot,fname)
    subprocess.call(['convert',fname,
                     #'-crop','800x500+600+200',
                     #'-flip',
                     '-resize','400x250','screenshot.gif'])
    trialdata['saved']=True
    gui["photo"]=PhotoImage(file='screenshot.gif')
    gui["photolabel"].configure(image=gui["photo"])
    




    
    
def mainloop():

    gui['running']=True
    gui['keep_going']=True # be an optimist!
    trialdata['redraw']=True
    trialdata['first.t']=time.time()
    pygame.event.clear() # Make sure there is no previous events in the pipeline
    if conf['use_mouse']:
        conf['mouse'].purgeEvents()

    while gui['keep_going']:

        time.sleep(.001) # add a little breath
        trialdata["t.absolute"] = time.time()
        trialdata["t.current"] = trialdata["t.absolute"]-trialdata['first.t']
        schedule = current_schedule()


        ##
        ## INPUT PHASE
        ##
        
        # Read the current position
        trialdata['robot_x'],trialdata['robot_y'] = robot.rshm('x'),robot.rshm('y')
        if phase_in(['fade','move']):
            record_position(trialdata['robot_x'],trialdata['robot_y'])
        
        # Get any waiting events (joystick, but maybe other events as well)
        if conf['use_joystick']:
            evs = pygame.event.get()
            if phase_is('select'):
                for ev in evs:
                    if ev.type==pygame.JOYAXISMOTION:
                        trialdata['joystick.pos']=get_joystick() # update the joystick position
                        trialdata['redraw']=True
                    if ev.type==pygame.JOYBUTTONDOWN:
                        trialdata['selection_made']=True

        if conf['use_mouse']:
            ev = conf['mouse'].getEvent()
            if ev and phase_is('select'): # Update the selector position based on this movement
                x,y=ev[0],ev[1]
                update_selector((x,y))
                trialdata['redraw']=True

                for i in range(2,len(ev)-1):
                    if ev[i]: trialdata['selection_made']=True


                


        ##
        ## CONTROL FLOW
        ##
        if phase_is('init'):
            # Start a new trial
            start_new_trial()

        if phase_is('return'):
            if robot.move_is_done(): # if we are back at the starting point
                if schedule['type'] in ['passive','pinpoint','active']:

                    # Determine the angle of the display target
                    angle = conv_ang(schedule['target.direction'])
                    trialdata['target.display.angle']=angle
                    trialdata['target_position']=position_from_angle(angle)
                    
                    if schedule['type'] in ['passive','pinpoint']:

                        angle = conv_ang(schedule['mov.direction'])
                        trialdata['movement_angle']=angle
                        radius = conf['movement_radius']
                        if schedule['type']=='passive': # In passive trials, we add a little undershoot/overshoot
                            o = np.random.normal(0,conf['target_overshoot_SD'])
                            trialdata['movement_overshoot']=o
                            radius+=o
                        trialdata['movement_position']=position_from_angle(angle,radius)
                        tx,ty = trialdata['movement_position']
                        robot.move_to(tx,ty,conf['passive_duration'])
                        next_phase('forward')
                    
                    if schedule['type']=='active': # active movement
                        hold_fade()
                        robot.background_capture()
                        # the above line  will activate position capturing in the background,
                        # so that we can later pull the captured trajectory out
                        next_phase('fade')
                        trialdata['hold.until.t']=trialdata['t.absolute']+conf['fade_duration']

                        if DEBUG:
                            x,y=trialdata['target_position']
                            robot.preprogram_move_to(x,y,1.5)
                            robot.future.append({"fvv_move_done":1}) # this will happen in the future when the entire trajectory has finished
                        
                    trialdata['redraw']=True

        if phase_is('fade'):
            if trialdata['t.absolute']>trialdata.get('hold.until.t',0): # if the hold time is expired
                start_move_controller()
                next_phase('move')
                robot.wshm('fvv_trial_phase',5) # signal that we are moving
                trialdata['redraw']=True

        if phase_is('move'):
            if robot.rshm('fvv_move_done'): # this is the signal from the move controller that the subject has stopped moving
                robot.stay()
                trialdata['captured'] = robot.stop_background_capture() # stop capturing in the background and retrieve the trajectory
                next_phase('hold')
                trialdata['hold.until.t']=trialdata['t.absolute']+conf['stay_duration']
                # Plot the movement
                record_plot()

        if phase_is('hold'):
            if trialdata['t.absolute']>trialdata.get('hold.until.t',0):
                next_phase('completed')
                
                    
        if phase_is('forward'):
            if robot.move_is_done():
                if schedule['type'] in ['passive','pinpoint']:
                    robot.stay()
                    trialdata['stay.until.t']=trialdata['t.absolute']+conf['stay_duration']
                    next_phase('stay')

        if phase_is('stay'):
            if trialdata['t.absolute']>trialdata.get('stay.until.t',0):
                if schedule['type'] in ['passive','pinpoint']:
                    sx,sy = conf['robot_center']
                    robot.move_to(sx,sy,conf['passive_duration'])
                    next_phase('backward')
                    
        if phase_is('backward'):
            if robot.move_is_done():
                if schedule['type'] in ['passive']:
                    robot.stay()
                    next_phase('ask')

                if schedule['type']=='pinpoint':
                    robot.stay()

                    r = random.random()
                    trialdata['selector_prop']   =r
                    trialdata['selector_initial']=r # mark that this was the first angle, in case we need to report this later on
                    trialdata['selection_made']=False
                    next_phase('select')


        if phase_is('ask'):
            r = numpy.random.uniform()
            if r<conf['target_overshoot_ask_p']:
                answer = messagebox.askyesno("Question","Did the cursor overshoot (YES) or undershoot (NO) the center of the target?")
                trialdata['overshoot_answer']=answer
            next_phase('completed')
                    
                    
        if phase_is('select'):
            if trialdata['selection_made']:
                print("Selected angle %.2f deg (%.2f)"%(trialdata['selector_angle'],trialdata['selector_prop']))
                next_phase('completed') # this will automatically wrap up the trial


        if phase_is('completed'):
            # Read the position at peak velocity
            for vr in ['vmax_x','vmax_y','final_x','final_y']:
                trialdata[vr]=robot.rshm('fvv_%s'%vr)
            write_logs()

            start_new_trial()
            
        


                
        # Possibly update the display
        if trialdata['redraw']:

            conf['screen'].fill(conf['bgcolor'])

            # Draw start position
            draw_ball(conf['screen'],conf['robot_center'],conf['center_marker_radius'],conf['center_marker_colour'])

            if 'target_position' in trialdata and not trialdata['type']=='pinpoint': # We show a target always, only not if this is a pinpoint trial
                draw_ball(conf['screen'],trialdata['target_position'],conf['target_radius'],conf['target_colour'])
            
            if phase_is('select'): # If we are in the select phase
                if 'selector_prop' in trialdata: selector_to_angle()
                draw_arc_selector()

            # For debug only: show veridical robot position
            if DEBUG:
                draw_ball(conf['screen'],(trialdata['robot_x'],trialdata['robot_y']),conf['cursor_radius'],(100,100,100)) # only for debug: show the real robot position

            if phase_in(['forward','stay','fade','move']):

                # Show a cursor
                if trialdata['type'] in ['passive','active']:
                    if phase_is('fade'):
                        colour=conf['fade_cue_colour']
                    elif phase_is('move'):
                        colour = conf['active_cursor_colour']
                    else:
                        colour = conf['passive_cursor_colour']
                    trialdata['cursor_position']=rotate((trialdata['robot_x'],trialdata['robot_y']),deg2rad(trialdata['cursor.rotation']),conf['robot_center'])
                    draw_ball(conf['screen'],trialdata['cursor_position'],conf['cursor_radius'],colour)


                
            pygame.display.flip()

            
    print("Bailed out of main loop.")
    gui['running']=False
    


    


def next_phase(p):
    """ Set the current phase to a given value. """
    print(p)
    trialdata['phase']=p

    # Track the start of this phase
    k = trialdata.get('t.phase',{})
    k[p]=time.time()
    trialdata['t.phase']=k

    # Mark on the robot that this phase started too
    if p in conf['phases']:
        robot.wshm('fvv_trial_phase',conf['phases'].index(p))
    else:
        print("## WARNING, unknown phase %s"%p)







#
#
#  Stuff relating to logging
#
#



def init_logs():
    #logfile = open("data/exampledata.txt",'w')

    basedir = './data/%s'%conf['participant']
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    
    timestamp = datetime.datetime.now().strftime("%d_%m.%Hh%Mm%S")
    basename = '%s/%s_%s_%s'%(basedir,conf['participant'],EXPERIMENT,timestamp)
        
    trajlog = '%strajectory.bin'%basename
    robot.start_log(trajlog,conf['N_ROBOT_LOG'])
    gui["logging"]=True

    conf['captured'] = []
    capturelog = '%scaptured.pickle27'%basename
    ##trajlog.write('participant experiment trial x y dx dy t t.absolute\n')

    
    dumplog = '%sdump.pickle'%basename

    ## Also dump the configuration parameters, this will make it easier to debug in the future
    conflog = open('%sparameters.json'%basename,'w')
    params = {}
    for key in sorted(conf):
        if key not in ['joystick','screen','mouse','thread','triallog']: # don't dump that stuff: not serialisable
            params[key]=conf[key]
    params['schedule']=trialdata['schedule']
    #print(params)
    json.dump(params,conflog)
    conflog.close()

    conf['obsvlog']     = '%sobservations.txt'%basename # where we will write the experimenter observations

    triallog = '%strials.txt'%basename
    conf['triallog'] = open(triallog,'w')
    conf['triallog'].write(trial_header())

    conf['trajlog']     = trajlog
    conf['dumpf']       = dumplog
    conf['capturelog']  = capturelog





def write_logs():
    """ At the end of a trial, write into the log. """
    hist = {}
    for k in ['type','target.direction','mov.direction','cursor.rotation','target_position','cursor_position','t.phase','selector_angle','selector_prop','selector_history','selector_initial','captured','overshoot_answer','movement_overshoot']:
        v = trialdata.get(k,np.nan)
        if isinstance(v,np.ndarray):
            v = v.tolist()
        hist[k]=v
    conf['trialhistory'].append(hist)
    pickle.dump(conf['trialhistory'],open(conf['dumpf'],'wb')) # this will overwrite the previous file

    conf['triallog'].write(trial_log())
    conf['triallog'].flush()
    


LOG_COLUMNS = ['trial','type','mov.direction','cursor.rotation','selector_angle','selector_prop','vmax_x','vmax_y','final_x','final_y','movement_overshoot','overshoot_answer']
def trial_header():
    return " ".join(LOG_COLUMNS)+"\n"
    
def trial_log():
    return " ".join([str(trialdata.get(v,np.nan)) for v in LOG_COLUMNS])+"\n"



def close_logs():
    if gui["logging"]:
        conf['triallog'].close()
        robot.stop_log()
    gui["logging"]=False




    

def read_schedule_file():
    """ 
    Read a schedule file which tells us the parameters of each trial.
    """

    print("Reading trial schedule file %s"%conf['schedulefile'])

    s = pd.read_csv(conf['schedulefile'],sep=' ')
    for c in ['trial','type','target.direction','mov.direction','cursor.rotation']:
        if not c in s.columns:
            print("## ERROR: missing column %s in schedule."%c)

    # I don't trust pandas so I prefer a simple data structure, list of dicts            
    schedule = []
    for i,row in s.iterrows():
        schedule.append(dict(row))

    trialdata['schedule'] = schedule
    #experiment.ntrials = len([ tr for tr in trials if tr["type"]=="arctrace" ])
    print("Finished reading %i trials"%(len(trialdata['schedule'])))


    



def update_ui():
    global gui
    gui["runb"].configure(state=DISABLED)
    gui["capturecenter"].configure(state=DISABLED)

    if gui["loaded"]:
        gui["loadb"].configure(state=DISABLED)

        if not gui["running"]:
            gui["runb"].configure(state=NORMAL)
            gui["capturecenter"].configure(state=NORMAL)

    else: # not loaded
        gui["loadb"].configure(state=NORMAL)

    

        
def load_robot():
    """ Launches the robot process. """
    global gui
    tkMessageBox.showinfo("Robot", "We will now load the robot.\n\nLook at the terminal because you may have to enter your sudo password there.")

    robot.load() # launches the robot C++ script
    # Then do zero FT
    tkMessageBox.showinfo("Robot", "Now we will zero the force transducers.\nAsk the subject to let go of the handle." )
    robot.zeroft()
    bias = robot.bias_report()
    tkMessageBox.showinfo("Robot", "Robot FT bias calibration done.\nYou can tell the subject to hold the handle again.\n\nRobot bias settings:\n\n" +" ".join([ str(b) for b in bias ]))
    gui["loaded"]=True
    update_ui()






def stop_running():
    gui['keep_going'] = False # this will bail out of the main loop
    time.sleep(1) # wait until some last commands may have stopped
    close_logs()
    if gui['loaded']:
        robot.unload()
        gui["loaded"]=False
        

    
def end_program():
    """ When the user presses the quit button. """
    stop_running()
    ending()
    sys.exit(0)


    
    


def run():
    """ Do one run of the experiment. """
    if gui["running"]:
        return

    global conf

    participant=gui["subject.id"].get().strip()
    if participant=="":
        tkMessageBox.showinfo("Error", "You need to enter a participant ID.")
        return
    conf['participant'] = participant

    
    schedulefile=gui["schedulef"].get().strip()
    if schedulefile=="":
        tkMessageBox.showinfo("Error", "You need to enter a schedule file name.")
        return
    if not os.path.exists(schedulefile):
        tkMessageBox.showinfo("Error", "The schedule file name you entered does not exist.")
        return
    conf['schedulefile'] = schedulefile


    centerx=gui["centerv"].get().strip()
    try:
        centerx=float(centerx)
    except:
        tkMessageBox.showinfo("Error", "The center X location you entered is invalid: %s.\n\nIt has to be a floating number."%centerx)
        return
    conf['robot_center_x'] = centerx
    conf['robot_center']=(conf['robot_center_x'],conf['robot_center_y'])


    print("Running the experiment.")
    gui["running"]=True
    update_ui()
    

    
    read_schedule_file()

    conf['trialhistory']=[] # this is where we will keep info from all previous trials.

    trialdata['participant'] =conf['participant']
    trialdata['schedulefile']=conf['schedulefile']
    init_logs()

    trialdata['current_schedule']=-1 # start at the beginning
    trialdata['phase']='init'
    
    launch_mainloop()


    

def select_schedule():
    """ Show a dialog that lets the user select a file. """
    
    fn = filedialog.askopenfilename(filetypes = (("CSV files", "*.csv")
                                                 ,("All files", "*.*") ))
    if not fn or not len(fn):
        print("No file selected.")
    else:
        gui["schedulef"].set(fn)







def capture_center():
    """ Capture the center position from the robot."""
    xs = []
    for i in range(conf['n_center_capture']):
        xs.append(robot.rshm('x'))
        time.sleep(conf['center_capture_period'])
    #print(xs)
    mean_x = np.mean(xs)
    gui['centerv'].set("%.3f"%mean_x)
        


        

def init_tk():
    global gui
    gui = {}
    
    master = Tk()
    master.geometry('%dx%d+%d+%d' % (CONTROL_WIDTH, CONTROL_HEIGHT, CONTROL_X, CONTROL_Y))
    master.configure(background='black')

    f = Frame(master,background='black')
    loadb   = Button(f, text="Load robot",                background="green",foreground="black", command=load_robot)
    runb    = Button(f, text="Run",                       background="blue", foreground="white", command=run)
    quitb   = Button(f, text="Quit",                      background="red",foreground="black", command=end_program)
    
    gui["subject.id"] = StringVar()
    l      = Label(f, text="subject ID",             fg="white", bg="black")
    subjid = Entry(f, textvariable=gui["subject.id"],fg="white", bg="black",insertbackground='yellow')

    row  = 0
    f.grid         (row=row,padx=10,pady=10)
    row += 1
    loadb.grid     (row=row,column=0,sticky=W,padx=10,pady=10)

    row += 1
    l.grid         (row=row,column=0,sticky=W,pady=10)
    subjid.grid    (row=row,column=1,sticky=W,padx=10)

    row +=1
    gui["schedulef"]  = StringVar()
    gui["schedulef"].set("schedule.csv")
    l      = Label(f, text="schedule file",          fg="white", bg="black")
    e      = Entry(f, textvariable=gui["schedulef"], fg="white", bg="black",insertbackground='yellow')
    l.grid(row=row,column=0,sticky=W,pady=10)
    e.grid(row=row,column=1,sticky=W,padx=10)
    b   = Button(f, text="select",                background="gray",foreground="black", command=select_schedule)
    b.grid(row=row,column=2,sticky=W,padx=10)

    row +=1
    gui["centerv"]  = StringVar()
    gui["centerv"].set("0.0")
    l      = Label(f, text="center X",             fg="white", bg="black")
    e      = Entry(f, textvariable=gui["centerv"], fg="white", bg="black",insertbackground='yellow')
    l.grid(row=row,column=0,sticky=W,pady=10)
    e.grid(row=row,column=1,sticky=W,padx=10)
    b   = Button(f, text="capture",                background="gray",foreground="black", command=capture_center)
    b.grid(row=row,column=2,sticky=W,padx=10)
    gui['capturecenter']=b

    row += 1
    runb.grid      (row=row,column=0,sticky=W,padx=10)

    b   = Button(f, text="pinpoint",             background="purple",foreground="black", command=pinpoint)
    b.grid(row=row,column=1,sticky=W,padx=10)
    
    row += 1
    quitb.grid     (row=row,sticky=W,padx=10,pady=10)


    row += 1
    gui["photo"]=PhotoImage(file='screenshot_base.gif')
    l = Label(f,image=gui['photo'])
    l.grid(row=row,column=0,columnspan=5,sticky=W)
    gui["photolabel"]=l
    
    # Make some elements available for the future
    gui["loadb"]     =loadb
    gui["runb"]      =runb
    gui["quitb"]     =quitb
    gui["keep_going"]=False
    gui["loaded"]    =False
    gui["running"]   =False
    gui["logging"]   =False
    
    master.bind()

    return master
    






def init_mouse():
    if conf['use_mouse']:
        if not os.path.exists(conf['mouse_device']):
            print("## ERROR: mouse device %s does not exist"%conf['mouse_device'])
            sys.exit(-1)
        mouse = MouseInput(conf['mouse_device'])
        conf['mouse']=mouse




## Initialise everything
conf['screen'],conf['mainfont'] = init_interface(conf)
init_mouse()
pygame.display.flip()


master = init_tk()
update_ui()
master.mainloop()




