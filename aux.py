
import pygame
import time
import sys

import numpy as np
import pickle



# The font used for displaying anything of interest
FONTFILE = "fonts/Aller_Rg.ttf"
mainFontSize = 24





def init_interface(conf):

    # Pygame configuration constants
    if conf['fullscreen']:
        displayFlags = pygame.FULLSCREEN # use for full-screen
    else:
        displayFlags = pygame.NOFRAME # for non-fullscreen (windowed mode), but without frame


    pygame.init()

    # Load the fonts
    #mainfont = pygame.font.Font(FONTFILE, mainFontSize)
    mainfont = None

    import os
    os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % conf["SCREENPOS"] # controls where the subject screen will appear
    
    # Initialise the display
    screen = pygame.display.set_mode(conf["SCREENSIZE"],displayFlags)
    screen.convert()
    pygame.display.set_caption('Curry')
    pygame.mouse.set_visible(False)
    screen.fill(conf["BGCOLOR"])

    pygame.display.flip()

    return (screen,mainfont)



def ending():
    # To stop the program
    pygame.quit()





def waitforkey( keys ):
    # Just wait until the user presses one of these keys,
    # then return the key that was pressed and the reaction
    # time.
    t0 = time.time()
    bailout = False 
    key = None
    t=0
    pygame.event.clear() # Make sure there is no previous keypresses in the pipeline

    while not bailout:

        time.sleep(.01) # wait for 10ms

        # Flush the time 
        t = time.time()

        # Wait for the next event
        evs = pygame.event.get()

        for ev in evs:

            if ev.type == pygame.KEYDOWN:
                if ev.key in keys:
                    key = keys.index(ev.key)+1
                    bailout=True
                if ev.key == pygame.K_ESCAPE:
                    sys.exit(0)

            if ev.type == pygame.QUIT:
                sys.exit(0)


    return (t,key)





def textScreen( surf, font, text,
                bgColor = None,
                fontcolor = (255,255,255),
                linespacing = 40 ):
    """ Display the given text on the screen surface """

    if bgColor==None:
        bgColor = conf["BGCOLOR"]
    surf.fill( bgColor )

    # First convert each line into a separate surface
    lines = text.split("\n")
    textboxes = []
    for line in lines:
        textboxes.append( font.render(line,True,fontcolor) )

    # Then blit the surfaces onto the screen
    starty = (surf.get_height()-(len(lines)*linespacing))/2
    i=0
    for i in range(len(textboxes)):
        # Put the image of the text on the screen at 250 x250
        surf.blit( textboxes[i] , ((surf.get_width()-textboxes[i].get_size()[0])/2,
                                   starty+(i*linespacing)) )


    return starty+(len(lines)*linespacing)
        









def message_screen(message):
    # Show a message on the screen and wait for the user to press the space bar."
    textScreen(conf['screen'],conf['mainfont'],message)
    pygame.display.flip()
    ret = waitforkey([pygame.K_SPACE])
    #while experiment.inputs.getEvent()!=None:
    #pass # purge the event cue for the mouse
    return






def isfloat(value):
    # Check if the given variable is a float
    # I know, it's ugly, but it works.
    try:
        float(value)
        return True
    except ValueError:
        return False





def fade(p,colora,colorb):
    ## Fade between two colours, as determined by a ratio p (from 0 to 1).
    ## IF p==0, use color a, if p==1, use color b
    lst = (1-p)*np.array(colora)+p*np.array(colorb)
    return tuple([ int(x) for x in lst ])




def find_closest_point( frompos, topos, mincare=np.nan ):
    # Find the distance vector from frompos (i,j) to the closest
    # point in the series topos (x,y) (each of x and y is a vector of points)
    # If you specify mincare, then we drop out of the loop
    # once we hit a distance that is below mincare.

    (i,j)   = frompos
    (xs,ys) = topos

    mindist = np.inf
    minp = np.nan,np.nan
    for (x,y) in zip(xs,ys):
        dx,dy = i-x,j-y
        dist = dx**2+dy**2
        if dist<mindist:
            minp = dx,dy
            mindist=dist
            if dist<mincare:
                return minp
    return minp







def writeln(contents):
    # A simplified version for writing a line of output to file
    cols = []
    for (f,c) in contents:
        #print(f,c)
        if f==None:
            cols.append('nan')
        else:
            cols.append(('%'+c)%f)
    # cols = [ 'NA' if f==None else  for (f,c) in contents ]
    return (" ".join(cols)+"\n")







def robot_to_screen(x,y,conf):
    """ Given robot coordinates, find the screen coordinates. """
    #global conf
    calib=conf["calib"]
    return (int(calib["interc.x"] + (x*calib["slope.x"])),
            int(calib["interc.y"] + (y*calib["slope.y"])))



def screen_to_robot(rx,ry,conf):
    """ Given coordinates on the screen (in pixels), convert to robot coordinates. """
    #global conf
    calib=conf["calib"]
    return ( (rx-calib["interc.x"])/calib["slope.x"],
             (ry-calib["interc.y"])/calib["slope.y"])
