import sys, os
from PIL import Image
base='/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign'
out=base+'/tmp/jury-client'
for c in ['deep','blueprint','premium']:
    for kind,h in [('desktop',1100),('mobile',1400)]:
        im=Image.open(f'{base}/concepts/{c}/{kind}.png').convert('RGB')
        W,H=im.size
        i=0;y=0
        while y<H:
            crop=im.crop((0,y,W,min(H,y+h)))
            crop.save(f'{out}/{c}-{kind}-{i:02d}.png')
            i+=1;y+=h
        print(c,kind,i)
