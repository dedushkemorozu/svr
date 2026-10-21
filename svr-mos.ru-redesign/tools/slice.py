import sys
from PIL import Image
D='/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign/concepts/blueprint/'
T='/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad/redesign/tmp/'
d=Image.open(D+'desktop.png'); W,H=d.size
step=1000; i=0
for y in range(0,H,step):
    d.crop((0,y,W,min(H,y+step))).save(T+f'd{i}.png'); i+=1
print('desktop slices',i)
m=Image.open(D+'mobile.png'); W,H=m.size
h=1400; cols=3; n=0; y=0
while y<H:
    sheet=Image.new('RGB',(W*cols+20*(cols-1),h),(60,60,60))
    for c in range(cols):
        if y>=H: break
        sheet.paste(m.crop((0,y,W,min(H,y+h))),(c*(W+20),0)); y+=h
    sheet.save(T+f'm{n}.png'); n+=1
print('mobile sheets',n)
