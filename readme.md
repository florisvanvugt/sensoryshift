

This is an experiment in which passive sensory movements are used to cause a proprioceptive displacement, and then we ask whether this affects adaptation.

This is built for the inmotion2 robot.


# Usage

Clone the robot repository (https://github.com/florisvanvugt/inmotionpy) and place its  subdirectory `robot` into the present repository.

Run `screencalib.py` to ensure the mapping between robot positions and the screen is accurate.

`make`


If you use the trackball as a selector, you will probably want to disable it in X (otherwise the subject hijacks your mouse cursor)



# Schedule file

Each block is controlled by a schedule file. This is a text file table where each row is one trial (see `schedule.csv` for an example).
The `type` column tells you the type of a trial:
   * `passive` trial: take the subject out to a direction (specified by the `mov.direction` column) and showing a visual cursor, rotated by a number of degrees specified in `visual.rotation`.
   * `pinpoint` trial: take the subject out to a direction specified by the `mov.direction` column, then back to the starting point, and then display an arc where the subjects can select where they feel their hand is.
   * `active` trial: the subject can freely move to a direction, and sees a cursor, rotated by an amount specified in `visual.rotation`.
   
   
Angles are specified in degrees relative to 0=straight ahead, and positive angles are counterclockwise.

In the schedule file, there are various columns:
   * `target.direction`: the physical angle at which the target is displayed (not affected by any rotation)
   * `mov.direction`: the physical angle at which the subject hand will be moved (again, not affected by rotation)
   * `cursor.rotation`: the angle by which the visual cursor is rotated (where 0 rotation means the cursor follows the physical hand position).



# Control flow within the experiment

Every block starts in `init`.

  * Passive trials `init -> return -> forward -> backward -> completed`
  * Pinpoint trials `init -> return -> forward -> backward -> select -> completed`
  * Active trials `init -> return -> fade -> move -> completed`






### Trackball Mouse input privileges
You need read privileges on the input devices.
This can be achieved either manually but needs to be redone every time you log in to your computer:

```
sudo chmod a+r /dev/input/mouse*
```

Or you can set it permanently by adding a file called something like `/etc/udev/rules.d/99-inputrules.rules` with the following contents, in order to allow this once and for all:

```
#
#       Documentation is your friend: http://reactivated.net/writing_udev_rules.html
#
# Source: http://puredata.info/docs/faq/how-can-i-set-permissions-so-hid-can-read-devices-in-gnu-linux
#       input devices
#
SUBSYSTEM=="input", MODE="666"
```

To get information about a particular device, use

```
udevadm info {device}
```

(where `{device}` is the device node).






# TODO
- [ ] Robot binary log
- [ ] Record handle forces
- [ ] Record trial # in robot log
- [x] Joystick positioning: random offset at every trial

- [x] Could "cache" the selector arc surface and then blit it -- not necessary I suppose
- [ ] Screen calibration -- covariance between X and Y?
- [x] Trial log: log the times, results, targets, etc.

- [ ] Active trials: show trajectory in preview window

- [ ] Could also control the robot with the joystick to move you passively across the workspace

- [x] Run button disabled when no subject is given
- [x] Disable pointer Kensington in X

- [x] Make a history of selector positions?
- [ ] Show target

- [ ] Use radial velocity for determining cutoff during move phase?


