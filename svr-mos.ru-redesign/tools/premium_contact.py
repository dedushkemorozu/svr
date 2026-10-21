import json, sys
from PIL import Image, ImageDraw
S='/tmp/claude-0/-home-user-svr/91850086-9a8b-57da-a51c-3fbc107daed3/scratchpad'
media=json.load(open(S+'/media.json'))
def sheet(ids,out,cols=4,cw=370,ch=230,bg=(120,120,120)):
    rows=(len(ids)+cols-1)//cols
    im=Image.new('RGB',(cols*cw,rows*ch),bg)
    d=ImageDraw.Draw(im)
    for i,mid in enumerate(ids):
        m=[x for x in media if x['id']==mid][0]
        try:
            t=Image.open(m['local']).convert('RGBA')
        except Exception as e:
            continue
        t.thumbnail((cw-10,ch-26))
        x=(i%cols)*cw+5; y=(i//cols)*ch+20
        im.paste(t,(x,y),t)
        d.text((x,y-16),str(mid),fill=(255,255,0))
    im.save(out)
ids=[x['id'] for x in media if x['w']>0]
sheet([7,8,9,10,12,13,14,15,16,17],S+'/redesign/tmp/premium/sheetA.png')
sheet(list(range(18,34)),S+'/redesign/tmp/premium/sheetB.png')
sheet(list(range(34,49)),S+'/redesign/tmp/premium/sheetC.png')
