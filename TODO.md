NEXT: Fix generate ORG bones so it can use collections

Do we even need templates for torso?

Twist bones generate ORG bones, but not DEF bones
We don't show in the dialog whether twist bone connections exist yet.
    Ideally:
    - Info: all twist bones present
    - Warning: some twist bones present, but some are missing.  This is usually an error condition.
    - Notice: twist bones will be created
Twist bones/tweak bones - another name?

Chain selection tools need refinement
    - Select hierachy doesn't work with branches
    - Select connected doesn't work in pose mode