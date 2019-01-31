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
robot = None

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
conf['arc_thickness']     = .005 # how thick to draw the 'selector' arc
conf['arc_colour']        = (127,127,127)


conf['selector_radius']=.005 # the radius of the selector ball that is controlled by the joystick
conf['selector_colour']=(0,0,255)


# Range of the joystick values
# anything outside this range is snapped to the edges
conf['max_joystick']= 1
conf['min_joystick']= 0






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

    
    if 'selector_position' in conf:
        #print(conf['selector_position'])
        draw_ball(conf['screen'],conf['selector_position'],conf['selector_radius'],conf['selector_colour'])
        

    



    
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

    conf['redraw']=True
    
    # Start the main loop
    conf['thread']=Thread(target=mainloop)
    conf['thread'].start()





def get_selector_position(pos):
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

    cx,cy = conf['robot_center']
    pos = (cx+conf['movement_radius']*np.cos(a),cy+conf['movement_radius']*np.sin(a))
    
    return pos
     

    

def get_joystick():
    """ Get the current position of the joystick."""
    joystick = conf['joystick']
    pos = [ joystick.get_axis( i ) for i in range(2) ] # get the first two axes
    if len(conf['joystick_history'])==0 or pos!=conf['joystick_history'][-1]:
        conf['joystick_history'].append(pos) # TODO: make sure we clear the joystick history also!
    conf['selector_position']=get_selector_position(pos) # update the selector position
    return pos
    


def mainloop():

    conf['keep_going']=True # be an optimist!
    pygame.event.clear() # Make sure there is no previous events in the pipeline

    while conf['keep_going']:

        time.sleep(.001) # wait a little bit

        # Flush the time
        t = time.time()

        # Wait for the next event
        evs = pygame.event.get()

        for ev in evs:

            if ev.type==pygame.JOYAXISMOTION:
                conf['joystick.pos']=get_joystick() # update the joystick position
                conf['redraw']=True

        if conf['redraw']:
            draw_arc_selector()
            draw_ball(conf['screen'],conf['robot_center'],.01,(255,0,0))
            pygame.display.flip()

    print("Bailed out of main loop.")
    










#
#
#  Stuff relating to logging
#
#



def init_logs(conf):
    #logfile = open("data/exampledata.txt",'w')
    timestamp = datetime.datetime.now().strftime("%d_%m.%Hh%Mm%S")
    basename = './data/%s_%s_%s_'%(conf['participant'],EXPERIMENT,timestamp)
    trajlog = '%strajectory.bin'%basename
    robot.start_log(trajlog,N_ROBOT_LOG)
    gui["logging"]=True

    conf['captured'] = []
    capturelog = '%scaptured.pickle27'%basename
    ##trajlog.write('participant experiment trial x y dx dy t t.absolute\n')

                
    triallog = open('%strials.txt'%basename,'w')
    triallog.write('participant experiment trial rotation target.x target.y t.go t.movestart t.target.enter t.trial.end timing timing.numeric duration\n')


    conflog = open('%sparameters.json'%basename,'w')
    #conflog.write('parameter;value\n')
    params = {}
    for key,value in [ ('participant',  conf['participant']),
                       ('schedulefile', conf['schedulefile']),
                       ('calib',        conf['calib']),
                       ('fullscreen',   conf['fullscreen']),
    ]:
        params[key]=value #.append((str(key),str(value)))
    for key in sorted(conf):
        params[key]=conf[key]
    json.dump(params,conflog)
    conflog.close()



    conf['trajlog']     = trajlog
    conf['triallog']    = triallog
    conf['capturelog']  =capturelog







def trajlog(trialdata,position):
    # Write the trajectory to file. Actually here we log all mouse events, even those that
    # do not cause a change in cursor position (such as those occurring during "null" trial
    # time).

    (x,y) = trialdata["cursor.position"]
    t          = trialdata["t.current"]

    if not np.isnan(x) and not np.isnan(y):
        if trialdata["phase"]=="active":
            trialdata["position.history"].append((x,y,t))

    



def triallog(trialdata):
    (tx,ty) = trialdata["target.position"]

    conf['triallog'].write( writeln( [
        (conf['participant'],            's'),
        (trialdata["experiment"],           's'),
        (trialdata["trial.number"],         'i'),
        (tx,'f'),(ty,'f'),
        (trialdata["t.go"],                 'f'),
        (trialdata["t.movestart"],          'f'),
        (trialdata["t.target.enter"],       'f'),
        (trialdata["t.trial.end"],          'f'),
        (trialdata["timing"],               's'),
        (timing_number[trialdata["timing"]],'i'),
        (trialdata["duration"],             'f'),
        ]))

    conf['triallog'].flush()


def close_logs():
    if gui["logging"]:
        conf['triallog'].close()
        robot.stop_log()
    gui["logging"]=False



    

def read_schedule_file():
    """ Read a schedule file which tells us the parameters of each trial."""

    print("Reading trial schedule file %s"%conf['schedulefile'])

    schedule = pd.read_csv(conf['schedulefile'],sep=' ')

    for c in ['trial','type','mov.direction','visual.rotation']:
        if not c in schedule.columns:
            print("## ERROR: missing column %s in schedule."%c)
    
    conf['schedule'] = schedule
    #experiment.ntrials = len([ tr for tr in trials if tr["type"]=="arctrace" ])
    print("Finished reading %i trials"%(conf['schedule'].shape[0]))


    



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
    robot.load()

    # Then do zero FT
    tkMessageBox.showinfo("Robot", "Now we will zero the force transducers.\nAsk the subject to let go of the handle." )
    robot.zeroft()
    bias = robot.bias_report()
    tkMessageBox.showinfo("Robot", "Robot FT bias calibration done.\nYou can tell the subject to hold the handle again.\n\nRobot bias settings:\n\n" +" ".join([ str(b) for b in bias ]))
    gui["loaded"]=True
    update_ui()




    
def end_program():
    """ When the user presses the quit button. """

    conf['keep_going'] = False
    time.sleep(1) # wait until some last commands may have stopped

    close_logs()
    
    if gui['loaded']:
        robot.unload()
        gui["loaded"]=False
        
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
    experiment.participant = participant

    
    schedulefile=gui["schedulef"].get().strip()
    if schedulefile=="":
        tkMessageBox.showinfo("Error", "You need to enter a schedule file name.")
        return
    if not os.path.exists(schedulefile):
        tkMessageBox.showinfo("Error", "The schedule file name you entered does not exist.")
        return
    experiment.schedulefile = schedulefile

    experiment.visualfb = gui["visualfb"].get()!=0

    experiment.calib = conf["calib"]
    
    read_schedule_file(experiment)



    init_logs(experiment,conf)
    experiment.inputs = robot 



    trialdata = {"trial.number"    :0,
                 "experiment"      :EXPERIMENT,
                 "direction"       :"left",
                 "phase"           :"null",
                 "cursor.position" :(np.nan,np.nan),
                 "t.start"         :np.nan,
                 "t.trial.finish"  :-np.inf,
                 "target.position" :conf["RIGHT_ARC_ORIGIN"],
                 "start.position"  :conf["LEFT_ARC_ORIGIN"]}


    ##center_trackball(experiment)
    # This means we are still waiting for the first trigger
    conf['current_schedule'] = 0 # this is a pointer to where we are in the schedule. if zero, it means we haven't yet received the first trigger
    draw_positions(experiment,trialdata)
    pygame.display.flip()

    
    experiment.keep_going = True
    while experiment.keep_going:

        # Keep track of whether we will want to redraw
        redraw = False

        trialdata["t.absolute"] = time.time()

        # Get the current time (coded in seconds but with floating point precision)
        trialdata["t.current"] = trialdata["t.absolute"]-experiment.first_trigger_t()



        if trialdata["t.current"]>=trialdata["t.trial.finish"]: # this is where the trial should end

            # First of all, are we currently in the middle of a trial? Then we have to abort it.
            if trialdata["phase"]=="active":

                print("Forcing trial end.")
                
                print("Aborting trial because this takes too long.")
                redraw = True
                
                trialdata["t.target.enter"]       = np.nan
                trialdata["t.trial.end"]          = trialdata["t.current"]
                trialdata["duration"]             = np.nan
                trialdata["timing"]               = "incomplete.trial"

                trialdata["phase"]="feedback"
                trialdata["show.feedback.until.t"] = trialdata["t.current"]+conf["FINAL_POSITION_SHOW_TIME"]

                robot.stay() # stop the subject in their tracks
                finish_trial(experiment,trialdata)




        # Is it time to start holding the robot at the center?
        if trialdata['phase']=='return' and trialdata['t.current']>trialdata['t.stay']:
            trialdata['phase']='stay'
            x,y=trialdata['start.position']
            print("Staying fading at %f,%f"%(x,y))
            robot.stay_fade(x,y)

        elif trialdata['phase']=='stay' and trialdata['t.current']>trialdata['t.go']:
            print("Go!")
            trialdata['phase']='active' # go! start showing the cursor and let's move

            robot.wshm('fvv_trial_phase',4) # go signal is there, but subject has not necessarily started moving
            robot.move_phase_and_capture()
            #robot.start_capture()
            redraw = True # because if no visual fb, we should at least show the cursor
                    

        # If the feedback show time has completed...
        if trialdata["phase"]=="feedback" and trialdata["t.current"]>=trialdata.get("show.feedback.until.t",np.inf):
            # We have completed showing feedback
            print("Completed feedback show time.")
            trialdata["phase"]="null"
            redraw = True



        if trialdata['phase']=='null' and trialdata["t.current"]>=trialdata["t.trial.finish"]:
            # Start a new trial (or stop if there is nothing more to be done)
            trialdata = start_new_trial(experiment,trialdata)
            
            # Advance the schedule
            experiment.current_schedule += 1
                
            redraw = True





        # Get current position from the robot
        pos = robot.rshm('x'),robot.rshm('y')
        #print(pos)
        if True:
            # If we are in the "go" phase, start allowing cursor movement
            # If we are not, simply discard 
            if trialdata["phase"]=="active": #and trialdata["t.current"]>trialdata["t.start"]+trialdata["t.go"]:
                update_position(trialdata,pos,conf)
            trajlog(experiment,trialdata,pos)
            redraw = True





        if trialdata["phase"]=="active":
            # Decide whether we have reached the outside of the circle; if so, trial ends
            dfromcenter = np.sqrt(sum((np.array(trialdata["cursor.position"])-np.array(trialdata["cursor.start"]))**2))

            dtotarget = np.sqrt(sum((np.array(trialdata["cursor.position"])-np.array(trialdata["target.position"]))**2))
            # Determine whether we are inside the target area.
            # In the following, we set the in_target variable to TRUE if we are in the target area for this particular
            # experiment.

            # Determine the distance to the target; if they are close enough, flag that they have entered the target
            in_target = dtotarget<conf["TARGET_AREA"]


            if dfromcenter>conf["MOVE_START_RADIUS"]:
                # If we have moved far enough from the center to consider that the shooting movement has started.
                if trialdata["t.movestart"]==None:

                    # Movement has started
                    trialdata["t.movestart"] = trialdata["t.current"]
                    redraw = True

                    robot.wshm('fvv_trial_phase',5) # signal that we could start watching the velocity




                if experiment.visualfb:
                    if in_target:
                        if trialdata["t.target.enter"]==None:
                            trialdata["t.target.enter"]=trialdata["t.current"]
                        else:
                            if trialdata["t.current"]-trialdata["t.target.enter"] > conf["IN_TARGET_TIME"]:

                                ##### Trial ending
                                decide_timing(trialdata)

                                if True:
                                    trialdata["phase"]="feedback"
                                    trialdata["show.feedback.until.t"] = trialdata["t.current"]+conf["FINAL_POSITION_SHOW_TIME"]

                                    redraw = True


                                ### Wrap up the rest of the trial
                                robot.stay()
                                finish_trial(experiment,trialdata)


                    else:
                        # If we are outside of the target, we need to reset the target enter time
                        trialdata["t.target.enter"]=None


                else: # if we are not in visual feedback mode

                    # Here the logic is different, we wait for the robot to signal
                    # to us that the trial should end because the subject
                    # velocity is below a certain amount.

                    if robot.rshm('fvv_trial_phase')==6:

                        robot.stay()
                        robot.wshm('fvv_trial_phase',7) # mark that this trial is completed.
                        print("no-visual mode: trial end signaled.")

                        ##### Trial ending
                        decide_timing(trialdata)

                        trialdata["phase"]="feedback"
                        trialdata["show.feedback.until.t"] = trialdata["t.current"]+conf["FINAL_POSITION_SHOW_TIME"]
                        
                        redraw = True
                            
                        ### Wrap up the rest of the trial
                        finish_trial(experiment,trialdata)
                    
 

        if redraw:
            # Update the positions on the screen
            draw_positions(experiment,trialdata)
            pygame.display.flip()

            if trialdata['phase']=='feedback' and not trialdata['saved']:
                # Save to a file too
                if True:
                    print("Saving to file")
                    pygame.image.save(experiment.screen,'screenshot.bmp')
                    subprocess.call(['convert','screenshot.bmp',
                                     #'-crop','800x500+600+200',
                                     '-flip','-resize','400x250','screenshot.gif'])
                    trialdata['saved']=True

                    gui["photo"]=PhotoImage(file='screenshot.gif')
                    gui["photolabel"].configure(image=gui["photo"])


        master.update_idletasks()
        master.update()

    gui["running"]=False

    


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
    






## Initialise everything
conf['screen'],conf['mainfont'] = init_interface(conf)
pygame.display.flip()


master = init_tk()
update_ui()
master.mainloop()




