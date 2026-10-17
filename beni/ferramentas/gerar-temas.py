import random, math
random.seed(7)
W,H=1600,900
import os
OUT=os.path.expanduser('~/.local/share/cozy-kids-launcher/themes/')

def svg(body, defs=''):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice"><defs>{defs}</defs>{body}</svg>'

# ---------------- HERÓI (cidade à noite, quadrinhos, teias) ----------------
def web(cx,cy,r,a0,a1,spokes=7,rings=6,color='#ffffff',op=.55,sw=2.2):
    s=[]; angs=[a0+(a1-a0)*i/(spokes-1) for i in range(spokes)]
    for a in angs:
        s.append(f'<line x1="{cx}" y1="{cy}" x2="{cx+r*math.cos(a):.1f}" y2="{cy+r*math.sin(a):.1f}"/>')
    for k in range(1,rings+1):
        rr=r*k/rings; pts=[]
        for i in range(len(angs)-1):
            p1=(cx+rr*math.cos(angs[i]),cy+rr*math.sin(angs[i])); p2=(cx+rr*math.cos(angs[i+1]),cy+rr*math.sin(angs[i+1]))
            mid=(angs[i]+angs[i+1])/2; sag=rr*0.82
            c=(cx+sag*math.cos(mid),cy+sag*math.sin(mid))
            pts.append(f'M{p1[0]:.1f},{p1[1]:.1f} Q{c[0]:.1f},{c[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}')
        s.append(f'<path d="{" ".join(pts)}" fill="none"/>')
    return f'<g stroke="{color}" stroke-opacity="{op}" stroke-width="{sw}" stroke-linecap="round">{"".join(s)}</g>'

def skyline(base,hmin,hmax,wmin,wmax,color,win,winop,seed):
    random.seed(seed); x=-20; out=[]
    while x<W+20:
        w=random.randint(wmin,wmax); h=random.randint(hmin,hmax); y=base-h
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h+200}" fill="{color}"/>')
        if random.random()<.3: out.append(f'<rect x="{x+w*.4:.0f}" y="{y-40}" width="6" height="40" fill="{color}"/>')
        if win:
            for wy in range(y+18,base-10,26):
                for wx in range(x+10,x+w-14,20):
                    if random.random()<.38: out.append(f'<rect x="{wx}" y="{wy}" width="9" height="13" fill="{win}" opacity="{winop}"/>')
        x+=w+random.randint(0,8)
    return ''.join(out)

defs_h='''<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#061032"/><stop offset=".55" stop-color="#14205e"/><stop offset=".8" stop-color="#7a1030"/><stop offset="1" stop-color="#c8102e"/></linearGradient>
<pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="7" cy="7" r="2.1" fill="#ffffff" opacity=".07"/></pattern>
<radialGradient id="moon" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff6d8"/><stop offset=".7" stop-color="#ffe9a8"/><stop offset="1" stop-color="#ffd76a"/></radialGradient>
<radialGradient id="glow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffe9a8" stop-opacity=".45"/><stop offset="1" stop-color="#ffe9a8" stop-opacity="0"/></radialGradient>'''
rays=''.join(f'<path d="M800,980 L{800+1900*math.cos(math.radians(a)):.0f},{980+1900*math.sin(math.radians(a)):.0f} L{800+1900*math.cos(math.radians(a+4)):.0f},{980+1900*math.sin(math.radians(a+4)):.0f}Z" fill="#ffffff" opacity=".035"/>' for a in range(180,360,9))
body_h=(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>{rays}<rect width="{W}" height="{H}" fill="url(#dots)"/>'
 f'<circle cx="1260" cy="210" r="230" fill="url(#glow)"/><circle cx="1260" cy="210" r="110" fill="url(#moon)"/>'
 f'<circle cx="1225" cy="185" r="16" fill="#f3d98b" opacity=".6"/><circle cx="1290" cy="250" r="22" fill="#f3d98b" opacity=".5"/>'
 + skyline(760,140,330,60,130,'#0d1a4a','#ffd34d',.35,1)
 + skyline(830,90,260,70,150,'#070d26','#ffcc33',.75,2)
 + f'<rect y="828" width="{W}" height="80" fill="#05091c"/>'
 + web(0,0,520,0,math.pi/2,8,7) + web(W,0,380,math.pi/2,math.pi,6,5,op=.45)
 + '<path d="M300,0 L300,240" stroke="#fff" stroke-opacity=".6" stroke-width="2.5"/>'
 + '<g transform="translate(300,255)" fill="#0a0a0a"><ellipse rx="13" ry="17"/><circle cy="-20" r="9"/>'
 + ''.join(f'<path d="M0,-4 Q{s*26},{-18+k*10} {s*34},{-6+k*12}" stroke="#0a0a0a" stroke-width="3.5" fill="none"/>' for s in (-1,1) for k in range(4)) + '</g>'
 + '<g fill="#ffffff" opacity=".9"><path d="M120,560 l18,-48 l14,30 l30,-40 l-6,52 l34,-6 l-40,30 z" fill="#ffd34d" opacity=".0"/></g>')
open(OUT+'heroi.svg','w').write(svg(body_h,defs_h))

# ---------------- BLOCOS (base de montar com pinos) ----------------
def stud(x,y,r,base,light,dark):
    return (f'<circle cx="{x}" cy="{y+3}" r="{r}" fill="{dark}"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{base}"/>'
            f'<circle cx="{x}" cy="{y}" r="{r*.72}" fill="{light}" opacity=".35"/>'
            f'<path d="M{x-r*.55:.1f},{y-r*.25:.1f} a{r*.6:.1f},{r*.6:.1f} 0 0 1 {r*.75:.1f},{-r*.45:.1f}" stroke="#fff" stroke-opacity=".55" stroke-width="2.5" fill="none" stroke-linecap="round"/>')
def brick(x,y,cols,rows,c,light,dark,u=50):
    w,h=cols*u,rows*u; s=[f'<rect x="{x}" y="{y+6}" width="{w}" height="{h}" rx="5" fill="#000" opacity=".25"/>',
       f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{c}"/>',
       f'<rect x="{x+3}" y="{y+3}" width="{w-6}" height="{h-6}" rx="4" fill="none" stroke="{light}" stroke-opacity=".5" stroke-width="3"/>']
    for i in range(cols):
        for j in range(rows):
            s.append(stud(x+u/2+i*u,y+u/2+j*u,u*.3,c,light,dark))
    return ''.join(s)
U=50; plate='#2e9e48'
pat=f'''<pattern id="plate" width="{U}" height="{U}" patternUnits="userSpaceOnUse"><rect width="{U}" height="{U}" fill="{plate}"/>{stud(U/2,U/2,U*.3,'#34b052','#7fe08f','#1f7a34')}</pattern>
<radialGradient id="vig" cx=".5" cy=".5" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".45"/></radialGradient>'''
cols=[('#d42a2f','#ff8a80','#8e1418'),('#1565c0','#82b1ff','#0b3a75'),('#f9c80e','#fff59d','#b58900'),('#ff7a00','#ffcc80','#b04f00'),('#f5f5f5','#ffffff','#9e9e9e'),('#212121','#757575','#000000')]
bricks=[(0,0,4,2),(200,0,2,2),(1300,0,6,2),(1500,100,2,3),(0,150,2,4),(0,650,4,2),(200,750,2,3),(1350,700,5,2),(1450,550,3,3),(100,450,2,2),(1250,850,3,1),(500,850,4,1),(800,860,3,1),(600,0,3,1),(950,0,2,1),(1350,250,2,2),(1450,400,3,2),(1150,0,3,1),(0,350,1,2),(1550,600,1,2)]
bb=''.join(brick(x,y,c,r,*cols[i%len(cols)]) for i,(x,y,c,r) in enumerate(bricks))
# um bonequinho de blocos genérico (cabeça cilíndrica) no canto
fig=('<g transform="translate(1380,330)"><rect x="-26" y="-92" width="52" height="16" rx="6" fill="#f9c80e"/><rect x="-34" y="-80" width="68" height="62" rx="16" fill="#f9c80e"/>'
     '<circle cx="-13" cy="-55" r="5" fill="#222"/><circle cx="13" cy="-55" r="5" fill="#222"/><path d="M-15,-38 Q0,-26 15,-38" stroke="#222" stroke-width="4" fill="none" stroke-linecap="round"/>'
     '<path d="M-50,-14 L50,-14 L62,70 L-62,70 Z" fill="#d42a2f"/><rect x="-62" y="70" width="124" height="20" fill="#5d4037"/>'
     '<rect x="-60" y="90" width="56" height="70" fill="#1565c0"/><rect x="4" y="90" width="56" height="70" fill="#1565c0"/>'
     '<path d="M-50,-10 L-80,50" stroke="#d42a2f" stroke-width="26" stroke-linecap="round"/><path d="M50,-10 L80,50" stroke="#d42a2f" stroke-width="26" stroke-linecap="round"/>'
     '<circle cx="-82" cy="58" r="14" fill="#f9c80e"/><circle cx="82" cy="58" r="14" fill="#f9c80e"/></g>')
body_b=f'<rect width="{W}" height="{H}" fill="url(#plate)"/>{bb}<rect width="{W}" height="{H}" fill="url(#vig)"/>'
open(OUT+'blocos.svg','w').write(svg(body_b,pat))

# ---------------- NINJA (dojo à noite, montanhas, dragão dourado) ----------------
defs_n='''<linearGradient id="nsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#03140f"/><stop offset=".6" stop-color="#0b3326"/><stop offset="1" stop-color="#145c3f"/></linearGradient>
<radialGradient id="sun" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ff7043"/><stop offset=".75" stop-color="#e53935"/><stop offset="1" stop-color="#b71c1c"/></radialGradient>
<radialGradient id="sunglow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ff5722" stop-opacity=".35"/><stop offset="1" stop-color="#ff5722" stop-opacity="0"/></radialGradient>
<linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff3b0"/><stop offset=".5" stop-color="#f4c542"/><stop offset="1" stop-color="#b8860b"/></linearGradient>'''
def mountains(base,amp,color,seed,n=9):
    random.seed(seed); pts=[f'0,{H}',f'0,{base}']; x=0
    for i in range(n):
        x+=W/n; peak=base-random.uniform(.4,1)*amp
        pts.append(f'{x-W/n/2:.0f},{peak:.0f}'); pts.append(f'{x:.0f},{base-random.uniform(0,.25)*amp:.0f}')
    pts.append(f'{W},{H}'); return f'<polygon points="{" ".join(pts)}" fill="{color}"/>'
def shuriken(x,y,r,op):
    p=[]
    for k in range(4):
        a=math.radians(k*90-45)
        p+= [f'{x+r*math.cos(a):.1f},{y+r*math.sin(a):.1f}', f'{x+r*.28*math.cos(a+math.radians(45)):.1f},{y+r*.28*math.sin(a+math.radians(45)):.1f}']
    return f'<g opacity="{op}"><polygon points="{" ".join(p)}" fill="#cfd8dc"/><circle cx="{x}" cy="{y}" r="{r*.12:.1f}" fill="#03140f"/></g>'
# dragão: curva longa com escamas/espinhos
pts=[(1660-i*14, 78+34*math.sin(i/8)) for i in range(0,86)]
d='M'+' L'.join(f'{x:.0f},{y:.0f}' for x,y in pts)
spikes=''.join(f'<path d="M{x:.0f},{y-12:.0f} l-10,-26 l-12,22 z" fill="url(#gold)"/>' for i,(x,y) in enumerate(pts) if i%6==3)
dragon=(f'<path d="{d}" stroke="#7a5200" stroke-width="44" fill="none" stroke-linecap="round" opacity=".9"/>'
        f'<path d="{d}" stroke="url(#gold)" stroke-width="34" fill="none" stroke-linecap="round"/>'
        f'<path d="{d}" stroke="#7a5200" stroke-width="3" stroke-dasharray="6 14" fill="none" opacity=".6"/>{spikes}')
hx,hy=pts[-1]
head=(f'<g transform="translate({hx+10:.0f},{hy:.0f}) scale(.95)"><path d="M10,-30 C-30,-44 -80,-26 -100,-4 C-84,10 -70,12 -60,10 C-50,24 -20,32 10,26 Z" fill="url(#gold)" stroke="#7a5200" stroke-width="3"/><path d="M-100,-4 L-78,2 L-96,8" fill="#fff8e1"/>'
      '<path d="M-10,-28 L10,-70 L-2,-30 Z M-30,-30 L-22,-72 L-40,-32 Z" fill="url(#gold)" stroke="#7a5200" stroke-width="2"/>'
      '<circle cx="-48" cy="-8" r="7" fill="#e53935"/><path d="M-95,4 Q-120,30 -140,10" stroke="#f4c542" stroke-width="4" fill="none"/><path d="M-90,-6 Q-125,-40 -150,-26" stroke="#f4c542" stroke-width="4" fill="none"/></g>')
pagoda=('<g fill="#020a07" transform="translate(300,640)">'
        + ''.join(f'<rect x="{-58+k*11}" y="{-k*78-50}" width="{116-k*22}" height="52"/><path d="M{-132+k*20},{-k*78-46} Q{-80+k*14},{-k*78-56} {-70+k*12},{-k*78-84} L{70-k*12},{-k*78-84} Q{80-k*14},{-k*78-56} {132-k*20},{-k*78-46} Q{60-k*10},{-k*78-60} 0,{-k*78-58} Q{-60+k*10},{-k*78-60} {-132+k*20},{-k*78-46} Z"/>' for k in range(4))
        + '<rect x="-3" y="-400" width="6" height="90"/><circle cy="-405" r="7"/><rect x="-70" y="0" width="140" height="130"/></g>')
bamboo=''.join(f'<g fill="#0e3d2b" opacity=".95"><rect x="{x}" y="0" width="{w}" height="{H}"/>' + ''.join(f'<rect x="{x-2}" y="{y}" width="{w+4}" height="6" fill="#06231a"/>' for y in range(60,H,120+int(x)%40)) + '</g>' for x,w in [(30,22),(70,16),(1530,24),(1490,14)])
stars=''.join(f'<circle cx="{random.randint(0,W)}" cy="{random.randint(0,420)}" r="{random.choice([1,1,1.5,2])}" fill="#fff" opacity="{random.uniform(.3,.8):.2f}"/>' for _ in range(90))
clouds=''.join(f'<g fill="none" stroke="#f4c542" stroke-opacity=".55" stroke-width="3" transform="translate({x},{y})"><path d="M0,0 q20,-28 46,-6 q18,-30 48,-4 q26,-14 34,10 z"/><path d="M30,-6 q10,-12 22,-4"/></g>' for x,y in [(1080,470),(560,500),(1250,120)])
body_n=(f'<rect width="{W}" height="{H}" fill="url(#nsky)"/>{stars}{clouds}<circle cx="820" cy="330" r="300" fill="url(#sunglow)"/><circle cx="820" cy="330" r="165" fill="url(#sun)"/>'
        + mountains(560,260,'#0f4a35',3) + mountains(660,200,'#0a3727',4,7) + dragon + head + mountains(760,120,'#06261b',5,11) + pagoda + bamboo
        + shuriken(1200,780,40,.35) + shuriken(1320,700,26,.25) + shuriken(560,800,30,.25))
open(OUT+'ninja.svg','w').write(svg(body_n,defs_n))
print('ok')
