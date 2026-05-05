from random import randint
from secrets import choice


def genotp():
    otp=""
    up=[chr(i) for i in range(ord('A'),ord('Z')+1)]
    lo=[chr(i) for i in range(ord('a'),ord('z')+1)]
    for i in range(2):
        otp+=choice(up)+str(randint(0,9))+choice(lo)
    return otp 

