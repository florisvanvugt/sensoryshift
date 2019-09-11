

This is an experiment in which passive sensory movements are used to cause a proprioceptive displacement, and then we ask whether this affects adaptation.

This is built for the inmotion2 robot.


# Usage

Clone the robot repository (https://github.com/florisvanvugt/inmotionpy) and place its subdirectory `robot` into the present repository.

Run `screencalib.py` to ensure the mapping between robot positions and the screen is accurate.

```
make
```

If you want to run using the dummy robot, use

```
make dummy
```

If you use the trackball as a selector, you will probably want to disable it in X (otherwise the subject hijacks your mouse cursor)



# Schedule file

Each block is controlled by a schedule file. This is a text file table where each row is one trial (see `schedule.csv` for an example).
The `type` column tells you the type of a trial:
   * `passive` trial: take the subject out to a direction (specified by the `mov.direction` column) and showing a visual cursor, rotated by a number of degrees specified in `visual.rotation`.
   * `pinpoint` trial: take the subject out to a direction specified by the `mov.direction` column, then back to the starting point, and then display an arc where the subjects can select where they feel their hand is. In a proportion of trials, we will ask the subjects whether the cursor overshot or undershot the target (this is just to ensure they pay attention to the cursor).
   * `active` trial: the subject can freely move to a direction, and sees a cursor, rotated by an amount specified in `visual.rotation`.
   
   
Angles are specified in degrees relative to 0=straight ahead, and positive angles are counterclockwise.

In the schedule file, there are various columns:
   * `target.direction`: the physical angle at which the target is displayed (not affected by any rotation)
   * `mov.direction`: the physical angle at which the subject hand will be moved (again, not affected by rotation)
   * `cursor.rotation`: the angle by which the visual cursor is rotated (where 0 rotation means the cursor follows the physical hand position). set this to `NA` if you want there to be no cursor.
   * `force.field`: only meaningful for active trials, the possible values are `none`=null field, `curl`=curl force field, `channel`=force channel trial.
   * `target.type`: has to be `arc` or `point`, and I guess what that does is fairly obvious

To do visual no-feedback trials, simply set the `cursor.rotation` field to NA.



# Control flow within the experiment

Every block starts in `init`.

  * Passive trials `init -> return -> pause -> forward -> backward -> (ask) -> completed`
  * Pinpoint trials `init -> return -> pause -> forward -> backward -> select -> completed`
  * Active trials `init -> return -> fade -> move -> hold -> completed`






# Trackball Mouse input privileges
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




# Recognition task

We also implement a recognition task, where the subject passively feels two directions (A and B) and then is asked which is most similar to their own movement (on a previous day).

For this, press the `Recognition` button, which will prompt you to open a recognition schedule CSV file.

This CSV should have the following columns:

* `trial` - the number of the trial
* `direction` - which direction (in degrees) we will move to
* `type` - just a label that we don't actually use, but hey, why not have extra columns that do nothing?
* `target_direction` - the direction in which to display the visual target (because it can be different from the actual physical movement direction)


The directions are given in degrees as in the rest of the case relative to straight ahead, counter-clockwise.




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


