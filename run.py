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

#import robot.interface as robot
import robot.dummy as robot
#robot = None

import subprocess

PYTHON3 = (sys.version_info > (3, 0))
if PYTHON3:
    from tkinter import *
    from tkinter import messagebox as tkMessageBox
    from tkinter import filedialog

else: # python2
    from Tkinter import * # use for python2
    import tkMessageBox
    from Tkinter import filedialog

import json
import pandas as pd



from mouse import *


# The little control window
CONTROL_WIDTH,CONTROL_HEIGHT= 500,550 #1000,800 #450,400 # control window dimensions
CONTROL_X,CONTROL_Y = 500,50 # controls where on the screen the control window appears


EXPERIMENT = "sensoryshift"



N_ROBOT_LOG = 13 # how many columns go in the robot log file


# This is a global dict that holds all the configuration options. 
# Using a single variable for them makes it easier to keep track.
global conf
conf = {}



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
conf["cursor_radius"] = .005 # in robot coordinates (m)

# this is the display size of the target, not the size of the target area used for determining whether subjects are long enough "within" the target.
conf["target_radius"] = .005

# The cursor colour
conf["cursor_colour"] = (255,255,255)


# The radius of the movement
conf['movement_radius']=.15 # meters

conf['robot_center']= (0,-.05) # robot center position


# The extent of the arc being displayed on the screen when the
# subject selects the placement of the hand
# This is in angles, degrees, with 0 = straight ahead, and positive angles are counterclockwise
conf['arc_range']= (45,0)

conf['arc_draw_segments'] = 100 # how many segments to draw the arc (higher=more precision but takes more resources)
conf['arc_thickness']     = .001 # how thick to draw the 'selector' arc
conf['arc_colour']        = (127,127,127)


conf['selector_radius']=.005 # the radius of the selector ball that is controlled by the joystick
conf['selector_colour']=(0,0,255)


# Range of the joystick values
# anything outside this range is snapped to the edges
conf['max_joystick']= 1
conf['min_joystick']= 0



# How long to take for the return movement
conf['return_duration']=1.5 # seconds

# How long to take for the passive movements
conf['passive_duration']=1.5 # seconds

conf['stay_duration']=1 # how long to stay "out there" in between forward and backward movement


conf['mouse_device']='/dev/input/by-id/usb-Kensington_Kensington_USB_PS2_Orbit-mouse'


# Data that is specific to this trial
trialdata = {}





def conv_ang(a):
    """ Angles in this experiment are generally given in degrees
    w.r.t. straight ahead, just because that's simpler.
    But then sin and cos like to have them in radians, relative
    to straight right. So here we do that translation."""
    return ((a+90)/180)*np.pi
    


def selector_position_from_angle(a):
    cx,cy = conf['robot_center']
    pos = (cx+conf['movement_radius']*np.cos(a),cy+conf['movement_radius']*np.sin(a))
    return pos

    

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
        pos = selector_position_from_angle(trialdata['selector_angle'])
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


    
def launch_mainloop():
    conf['thread']=Thread(target=mainloop)
    conf['thread'].start()
    
    



def get_selector_angle(pos):
    """ Map the joystick position to a position of a selector on the screen."""

    # Determine the joystick position on a range from 0 to 1
    joy = pos[0]
    joyrel = (joy-conf['min_joystick'])/(conf['max_joystick']-conf['min_joystick'])
    if joyrel<0: joyrel=0
    if joyrel>1: joyrel=1
    #print(joyrel)
    
    # Ok, lovely! Now we can turn that into an angle
    mn,mx = conf['arc_range']
    a = conv_ang(mn+joyrel*(mx-mn))
    return a
    
     

    

def get_joystick():
    """ Get the current position of the joystick."""
    joystick = conf['joystick']
    pos = [ joystick.get_axis( i ) for i in range(2) ] # get the first two axes
    if 'joystick_history' in trialdata:
        if len(trialdata['joystick_history'])==0 or pos!=trialdata['joystick_history'][-1]:
            trialdata['joystick_history'].append(pos) # TODO: make sure we clear the joystick history also!
    trialdata['selector_angle']=get_selector_angle(pos) # update the selector position
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
        robot.stay() # just fix the handle wherever it is
        print("Experiment schedule completed.")
        next_phase('completed')
        gui['keep_going'] = False # this will bail out of the main loop
        # Now ask the experimenter for observations
        obsv = tkSimpleDialog.askstring('Please record any observations', 'Experimenter, please write down any observations.\nAny irregularities?\nDid the subject seem concentrated or not?\nWere things unclear or clear?\nAnything else that is worth noting?')
        with open(conf['obsvlog'],'w') as f:
            f.write(obsv)

        tkMessageBox.showinfo("Robot", "Block completed! Yay!")
        time.sleep(1) # wait until some last commands may have stopped
        close_logs()
        update_ui()
        return


    # Okay, if that wasn't the case, we can safely start our new trial
    trialdata['current_schedule']+=1


    sched = current_schedule() # Retrieve the current schedule
    trialdata['trial']           =sched['trial'] # trial number
    trialdata['type']            =sched['type']
    trialdata['mov.direction']   =sched['mov.direction']
    trialdata['visual.rotation'] =sched['visual.rotation']

    print("\n\n\n### TRIAL %d %s ###"%(trialdata['trial'],trialdata['type']))
    print("    direction: %.2f  rotation: %.2f deg\n"%(trialdata['mov.direction'],trialdata['visual.rotation']))

    ## Return the robot to the center
    sx,sy = conf['robot_center']
    robot.move_to(sx,sy,conf['return_duration'])
    next_phase('return') # return to the starting point to start the trial
    
    
    


def mainloop():

    gui['running']=True
    gui['keep_going']=True # be an optimist!
    trialdata['redraw']=True
    trialdata['first.t']=time.time()
    pygame.event.clear() # Make sure there is no previous events in the pipeline
    conf['mouse'].purgeEvents()

    while gui['keep_going']:

        time.sleep(.0005) # add a little breath
        trialdata["t.absolute"] = time.time()
        trialdata["t.current"] = trialdata["t.absolute"]-trialdata['first.t']
        schedule = current_schedule()


        ##
        ## INPUT PHASE
        ##
        
        # Read the current position
        trialdata['robot_x'],trialdata['robot_y'] = robot.rshm('x'),robot.rshm('y')
        
        # Get any waiting events (joystick, but maybe other events as well)
        evs = pygame.event.get()
        for ev in evs:
            if ev.type==pygame.JOYAXISMOTION:
                trialdata['joystick.pos']=get_joystick() # update the joystick position
                trialdata['redraw']=True

        ev = conf['mouse'].getEvent()
        if ev:
            print(ev)# change position



        ##
        ## CONTROL FLOW
        ##
        if phase_is('init'):
            # Start a new trial
            start_new_trial()

        if phase_is('return'):
            if robot.move_is_done():
                if schedule['type'] in ['passive','pinpoint']:
                    angle = conv_ang(schedule['mov.direction'])
                    cx,cy=conf['robot_center']
                    r = conf['movement_radius']
                    trialdata['target.angle']=angle
                    trialdata['target_position']=(cx+r*np.cos(angle),cy+r*np.sin(angle))
                    tx,ty = trialdata['target_position']
                    robot.move_to(tx,ty,conf['passive_duration'])
                    next_phase('forward')

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
                    next_phase('completed')

                if schedule['type']=='pinpoint':
                    robot.stay()
                    next_phase('select')


                    
        if phase_is('select'):
            pass # determine when to stop (go to completed)


        if phase_is('completed'):
            write_logs()
            start_new_trial()
            
        


                
        # Possibly update the display
        if trialdata['redraw']:

            conf['screen'].fill(conf['bgcolor'])

            if phase_is('select'):
                draw_arc_selector()
                draw_ball(conf['screen'],conf['robot_center'],.01,(255,0,0))

            if phase_in(['forward','backward','stay','return']):

                # Show a cursor
                if trialdata['type'] in ['passive','active']:
                    trialdata['cursor_position']=rotate((trialdata['robot_x'],trialdata['robot_y']),trialdata['visual.rotation'],conf['robot_center'])
                    draw_ball(conf['screen'],trialdata['cursor_position'],conf['cursor_radius'],conf['cursor_colour'])

                draw_ball(conf['screen'],(trialdata['robot_x'],trialdata['robot_y']),conf['cursor_radius'],(100,100,100)) # only for debug: show the real robot position

                
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
    robot.start_log(trajlog,N_ROBOT_LOG)
    gui["logging"]=True

    conf['captured'] = []
    capturelog = '%scaptured.pickle27'%basename
    ##trajlog.write('participant experiment trial x y dx dy t t.absolute\n')

    triallogf = '%strials.json'%basename

    ## Also dump the configuration parameters, this will make it easier to debug in the future
    conflog = open('%sparameters.json'%basename,'w')
    params = {}
    for key in sorted(conf):
        if key not in ['joystick','screen','mouse']: # don't dump that stuff: not serialisable
            params[key]=conf[key]
    params['schedule']=trialdata['schedule']
    json.dump(params,conflog)
    conflog.close()

    conf['obsvlog']     = '%sobservations.txt'%basename # where we will write the experimenter observations

    conf['trajlog']     = trajlog
    conf['triallogf']   = triallogf
    conf['capturelog']  =capturelog





def write_logs():
    """ At the end of a trial, write into the log. """
    hist = {}
    for k in ['type','mov.direction','visual.rotation','target.angle','target_position','cursor_position','t.phase']:
        v = trialdata.get(k,None)
        if isinstance(v,np.ndarray):
            v = v.tolist()
        hist[k]=v
    conf['trialhistory'].append(hist)
    json.dump(conf['trialhistory'],open(conf['triallogf'],'w')) # this will overwrite the previous file
    



def close_logs():
    if gui["logging"]:
        robot.stop_log()
    gui["logging"]=False




    

def read_schedule_file():
    """ 
    Read a schedule file which tells us the parameters of each trial.
    """

    print("Reading trial schedule file %s"%conf['schedulefile'])

    s = pd.read_csv(conf['schedulefile'],sep=' ')
    for c in ['trial','type','mov.direction','visual.rotation']:
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

    if gui["loaded"]:
        gui["loadb"].configure(state=DISABLED)

        if not gui["running"]:
            gui["runb"].configure(state=NORMAL)

    else: # not loaded
        gui["loadb"].configure(state=NORMAL)
        gui["runb"].configure(state=DISABLED)

    

        
def load_robot():
    """ Launches the robot process. """
    global gui
    tkMessageBox.showinfo("Robot", "We will now load the robot.\n\nLook at the terminal because you may have to enter your sudo password there.")

    robot.launch() # launches the robot C++ script
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

    print("Running the experiment.")
    gui["running"]=True
    update_ui()
    
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
    mouse = MouseInput(conf['mouse_device'])
    conf['mouse']=mouse




## Initialise everything
conf['screen'],conf['mainfont'] = init_interface(conf)
init_mouse()
pygame.display.flip()


master = init_tk()
update_ui()
master.mainloop()




