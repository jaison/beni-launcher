import random, math
W,H=1600,900
import os
OUT=os.path.expanduser('~/.local/share/cozy-kids-launcher/themes/')
def svg(body, defs=''):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice"><defs>{defs}</defs>{body}</svg>'

def flake(x,y,r,op=.9,sw=None,color='#ffffff'):
    sw=sw or max(1.5,r/7); s=[]
    for k in range(6):
        a=math.radians(k*60); ex,ey=x+r*math.cos(a),y+r*math.sin(a)
        s.append(f'M{x:.1f},{y:.1f} L{ex:.1f},{ey:.1f}')
        for f in (.45,.7):
            bx,by=x+r*f*math.cos(a),y+r*f*math.sin(a)
            for d in (-1,1):
                b=a+d*math.radians(45); s.append(f'M{bx:.1f},{by:.1f} L{bx+r*.28*math.cos(b):.1f},{by+r*.28*math.sin(b):.1f}')
    return f'<path d="{" ".join(s)}" stroke="{color}" stroke-opacity="{op}" stroke-width="{sw:.1f}" stroke-linecap="round" fill="none"/>'

def sparkle(x,y,r,color='#fff',op=1):
    return f'<path d="M{x},{y-r} Q{x+r*.18},{y-r*.18} {x+r},{y} Q{x+r*.18},{y+r*.18} {x},{y+r} Q{x-r*.18},{y+r*.18} {x-r},{y} Q{x-r*.18},{y-r*.18} {x},{y-r}Z" fill="{color}" opacity="{op}"/>'

def heart(x,y,s,color,op=1,rot=0):
    return (f'<path transform="translate({x},{y}) rotate({rot}) scale({s})" d="M0,6 C-14,-6 -10,-20 0,-12 C10,-20 14,-6 0,6Z" fill="{color}" opacity="{op}"/>')

# ================= REINO DO GELO =================
random.seed(11)
d_g='''<linearGradient id="gs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b2a6b"/><stop offset=".45" stop-color="#4f5fb8"/><stop offset=".75" stop-color="#9fb8ff"/><stop offset="1" stop-color="#e3f2ff"/></linearGradient>
<linearGradient id="aur1" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5effd6" stop-opacity="0"/><stop offset=".3" stop-color="#5effd6" stop-opacity=".55"/><stop offset=".7" stop-color="#b388ff" stop-opacity=".5"/><stop offset="1" stop-color="#b388ff" stop-opacity="0"/></linearGradient>
<linearGradient id="ice" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".5" stop-color="#cfe8ff"/><stop offset="1" stop-color="#8fbaf0"/></linearGradient>
<linearGradient id="icecastle" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity=".95"/><stop offset=".6" stop-color="#bfe3ff" stop-opacity=".9"/><stop offset="1" stop-color="#7fb2ee" stop-opacity=".9"/></linearGradient>
<radialGradient id="glowg" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffffff" stop-opacity=".7"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>'''
b=[f'<rect width="{W}" height="{H}" fill="url(#gs)"/>']
b+= [f'<circle cx="{random.randint(0,W)}" cy="{random.randint(0,380)}" r="{random.choice([1,1.3,1.8])}" fill="#fff" opacity="{random.uniform(.4,.9):.2f}"/>' for _ in range(110)]
for k,(y0,amp) in enumerate([(150,60),(220,50),(110,40)]):
    pts=' '.join(f'{x},{y0+amp*math.sin(x/170+k)}' for x in range(0,W+50,50))
    b.append(f'<polyline points="{pts}" fill="none" stroke="url(#aur1)" stroke-width="{70-k*18}" stroke-linecap="round" opacity="{.8-k*.2}"/>')
# montanhas de gelo
def mount(base,peaks,color,hl):
    s=''
    for (x,h,w) in peaks:
        s+=f'<polygon points="{x-w},{base} {x},{base-h} {x+w},{base}" fill="{color}"/><polygon points="{x},{base-h} {x+w*.18},{base-h*.62} {x+w*.05},{base-h*.55} {x-w*.12},{base-h*.66}" fill="{hl}" opacity=".9"/>'
    return s
b.append(mount(720,[(120,330,260),(420,260,230),(1180,300,250),(1500,360,260),(800,200,220)],'#8fb3e8','#ffffff'))
b.append(mount(790,[(0,200,240),(300,180,210),(1350,220,240),(1600,180,200)],'#a9c8f2','#ffffff'))
# castelo de gelo (centro-direita, atrás dos cartões aparece em cima)
cx=800
cast=['<g fill="url(#icecastle)" stroke="#ffffff" stroke-width="3" stroke-linejoin="round">']
for (dx,w,h) in [(-210,60,300),(-120,70,380),(0,110,470),(120,70,380),(210,60,300)]:
    x=cx+dx; top=760-h
    cast.append(f'<rect x="{x-w/2}" y="{top}" width="{w}" height="{h}"/>')
    cast.append(f'<polygon points="{x-w/2-8},{top} {x},{top-w*1.6} {x+w/2+8},{top}"/>')
    cast.append(f'<rect x="{x-8}" y="{top+40}" width="16" height="30" rx="8" fill="#7fb2ee" stroke="none"/>')
cast.append(f'<path d="M{cx-60},760 L{cx-60},680 Q{cx},620 {cx+60},680 L{cx+60},760Z" fill="#7fb2ee"/>')
cast.append('</g>')
b.append(f'<circle cx="{cx}" cy="420" r="260" fill="url(#glowg)" opacity=".55"/>'+''.join(cast))
b.append(f'<path d="M0,800 Q400,760 800,800 T1600,790 L1600,900 L0,900Z" fill="#f4faff"/><path d="M0,840 Q500,810 900,845 T1600,835 L1600,900 L0,900Z" fill="#ffffff"/>')
for _ in range(38):
    b.append(flake(random.randint(0,W),random.randint(0,880),random.choice([8,10,14,18,24,30]),op=random.uniform(.5,.95)))
for _ in range(25): b.append(sparkle(random.randint(0,W),random.randint(0,700),random.choice([5,7,9]),'#ffffff',.85))
open(OUT+'gelo.svg','w').write(svg(''.join(b),d_g))

# ================= CASINHA MÁGICA =================
random.seed(5)
d_c='''<linearGradient id="cs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd1ec"/><stop offset="1" stop-color="#e9d5ff"/></linearGradient>
<pattern id="dotsP" width="34" height="34" patternUnits="userSpaceOnUse"><rect width="34" height="34" fill="#ffb3d9"/><circle cx="17" cy="17" r="5" fill="#ffffff" opacity=".7"/></pattern>
<pattern id="strP" width="40" height="40" patternUnits="userSpaceOnUse"><rect width="40" height="40" fill="#c7b3ff"/><rect width="20" height="40" fill="#d8c9ff"/></pattern>
<pattern id="mintP" width="30" height="30" patternUnits="userSpaceOnUse"><rect width="30" height="30" fill="#a8edd8"/><path d="M0,15 L15,0 L30,15 L15,30Z" fill="#c4f5e6"/></pattern>
<pattern id="yelP" width="36" height="36" patternUnits="userSpaceOnUse"><rect width="36" height="36" fill="#ffe9a3"/><circle cx="9" cy="9" r="3" fill="#ffc94d"/><circle cx="27" cy="27" r="3" fill="#ffc94d"/></pattern>'''
b=[f'<rect width="{W}" height="{H}" fill="url(#cs)"/>']
# nuvenzinhas
for (x,y,s) in [(180,110,1),(1350,90,1.2),(760,60,.8)]:
    b.append(f'<g transform="translate({x},{y}) scale({s})" fill="#ffffff" opacity=".85"><circle r="40"/><circle cx="45" cy="10" r="32"/><circle cx="-45" cy="12" r="30"/><rect x="-75" y="10" width="150" height="32" rx="16"/></g>')
# casa de bonecas: telhado + 3 andares x 3 cômodos
hx,hy,hw=260,170,1080
b.append(f'<polygon points="{hx-40},{hy+60} {hx+hw/2},{hy-110} {hx+hw+40},{hy+60}" fill="#ff6fae" stroke="#ffffff" stroke-width="10" stroke-linejoin="round"/>')
b.append(f'<circle cx="{hx+hw/2}" cy="{hy-10}" r="44" fill="#ffe9a3" stroke="#fff" stroke-width="8"/>'+heart(hx+hw/2,hy-8,2.2,'#ff6fae'))
b.append(f'<rect x="{hx}" y="{hy+60}" width="{hw}" height="660" rx="18" fill="#ffffff"/>')
pats=['url(#dotsP)','url(#strP)','url(#mintP)','url(#yelP)']
rw,rh=(hw-40)/3,(660-40)/3
for r in range(3):
    for c in range(3):
        x=hx+10+c*(rw+10); y=hy+70+r*(rh+10)
        b.append(f'<rect x="{x}" y="{y}" width="{rw}" height="{rh}" rx="12" fill="{pats[(r*3+c)%4]}"/>')
        b.append(f'<rect x="{x}" y="{y+rh-22}" width="{rw}" height="22" fill="#e0a37a"/>')
        b.append(f'<rect x="{x+rw/2-40}" y="{y+30}" width="80" height="70" rx="40" fill="#bfe9ff" stroke="#fff" stroke-width="6"/><line x1="{x+rw/2}" y1="{y+30}" x2="{x+rw/2}" y2="{y+100}" stroke="#fff" stroke-width="5"/>')
# chaminé, gatinho genérico no telhado (orelhinhas)
b.append(f'<g transform="translate({hx+hw-170},{hy-40})"><path d="M-36,40 Q-40,0 -24,-18 L-12,4 Q0,-2 12,4 L24,-18 Q40,0 36,40 Q0,58 -36,40Z" fill="#9b7bff"/><circle cx="-12" cy="18" r="5" fill="#2d1b4e"/><circle cx="12" cy="18" r="5" fill="#2d1b4e"/><path d="M-5,28 Q0,32 5,28" stroke="#2d1b4e" stroke-width="3" fill="none" stroke-linecap="round"/><path d="M36,34 Q70,20 60,-10" stroke="#9b7bff" stroke-width="12" fill="none" stroke-linecap="round"/></g>')
# confete e corações
cols=['#ff6fae','#9b7bff','#4dd4b0','#ffc94d','#5bb8ff']
for _ in range(70):
    x,y=random.randint(0,W),random.randint(0,H); c=random.choice(cols)
    if random.random()<.5: b.append(f'<rect x="{x}" y="{y}" width="16" height="6" rx="3" fill="{c}" transform="rotate({random.randint(0,180)},{x},{y})"/>')
    else: b.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{c}"/>')
for _ in range(14): b.append(heart(random.randint(0,W),random.randint(0,H),random.uniform(1,2),random.choice(cols),.85,random.randint(-25,25)))
for _ in range(18): b.append(sparkle(random.randint(0,W),random.randint(0,H),random.choice([8,11,14]),'#ffffff',.9))
open(OUT+'casinha.svg','w').write(svg(''.join(b),d_c))

# ================= CASTELO ENCANTADO =================
random.seed(3)
d_p='''<linearGradient id="ps" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffb3d1"/><stop offset=".5" stop-color="#ffd6e7"/><stop offset="1" stop-color="#fff0d6"/></linearGradient>
<linearGradient id="wall" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff4f9"/><stop offset="1" stop-color="#f5d6ea"/></linearGradient>
<linearGradient id="roof" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c77dff"/><stop offset="1" stop-color="#8e44d6"/></linearGradient>
<linearGradient id="goldp" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff3b0"/><stop offset=".5" stop-color="#f4c542"/><stop offset="1" stop-color="#d49b1a"/></linearGradient>'''
b=[f'<rect width="{W}" height="{H}" fill="url(#ps)"/>']
for i,c in enumerate(['#ff8fab','#ffc06e','#fff176','#8ee6a0','#7fc8ff','#c49bff']):
    r=900-i*28; b.append(f'<path d="M{800-r},{900} A{r},{r} 0 0 1 {800+r},{900}" fill="none" stroke="{c}" stroke-width="28" opacity=".35"/>')
for (x,y,s) in [(200,180,1.3),(1380,140,1.5),(700,90,.9),(1100,300,.8),(350,420,.9)]:
    b.append(f'<g transform="translate({x},{y}) scale({s})" fill="#ffffff" opacity=".9"><circle r="40"/><circle cx="45" cy="10" r="32"/><circle cx="-45" cy="12" r="30"/><rect x="-75" y="10" width="150" height="32" rx="16"/></g>')
cx=800; g=['<g stroke="#e8b4d4" stroke-width="3">']
towers=[(-330,90,330),(-200,100,430),(0,150,540),(200,100,430),(330,90,330)]
for dx,w,h in towers:
    x=cx+dx; top=830-h
    g.append(f'<rect x="{x-w/2}" y="{top}" width="{w}" height="{h}" fill="url(#wall)"/>')
    g.append(f'<polygon points="{x-w/2-14},{top} {x},{top-w*1.5} {x+w/2+14},{top}" fill="url(#roof)" stroke="#7a2fbf"/>')
    fy=top-w*1.5
    g.append(f'<line x1="{x}" y1="{fy}" x2="{x}" y2="{fy-46}" stroke="#d49b1a" stroke-width="4"/><path d="M{x},{fy-46} L{x+36},{fy-36} L{x},{fy-26}Z" fill="#ff6fae" stroke="none"/>')
    for wy in (top+50, top+130):
        if wy<790: g.append(f'<path d="M{x-14},{wy+40} L{x-14},{wy+12} Q{x},{wy-6} {x+14},{wy+12} L{x+14},{wy+40}Z" fill="#ffe08a" stroke="#d49b1a"/>')
g.append(f'<rect x="{cx-260}" y="640" width="520" height="190" fill="url(#wall)"/>')
for i in range(13): g.append(f'<rect x="{cx-260+i*40}" y="620" width="24" height="24" fill="url(#wall)"/>')
g.append(f'<path d="M{cx-70},830 L{cx-70},730 Q{cx},660 {cx+70},730 L{cx+70},830Z" fill="#c77dff" stroke="#7a2fbf"/>')
g.append(f'<circle cx="{cx}" cy="700" r="0"/></g>')
b+=g
b.append(f'<path d="M0,830 Q400,800 800,830 T1600,820 L1600,900 L0,900Z" fill="#a6e3a1"/><path d="M0,860 Q500,840 900,865 T1600,858 L1600,900 L0,900Z" fill="#8fd18a"/>')
for _ in range(40): b.append(sparkle(random.randint(0,W),random.randint(0,800),random.choice([6,9,12,16]),random.choice(['#ffffff','#fff3b0','#ffd1ec']),.95))
for _ in range(10): b.append(heart(random.randint(0,W),random.randint(0,820),random.uniform(1,1.8),'#ff6fae',.7,random.randint(-20,20)))
open(OUT+'castelo.svg','w').write(svg(''.join(b),d_p))
print('ok')
