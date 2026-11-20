"""
Generate assets/dashboard-preview.png  1280×800
Matches dashboard v4: Zinc/Indigo palette, proper header, footer, monospace badges.
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

W, H = 1280, 900

# ── palette (dashboard v4) ────────────────────────────────────
BG   = ( 9,  9, 11)   # zinc-950
S1   = (24, 24, 27)   # zinc-900
S2   = (28, 28, 31)   # zinc-900 alt
S3   = (35, 35, 39)   # zinc-800
BD   = (39, 39, 42)   # zinc-800 border
BD2  = (63, 63, 70)   # zinc-700
TX   = (250,250,250)  # zinc-50
TX2  = (161,161,170)  # zinc-400
TX3  = ( 82, 82, 91)  # zinc-600
AC   = ( 79, 70,229)  # indigo-600
AC2  = ( 99,102,241)  # indigo-500
AC3  = (129,140,248)  # indigo-400
DG   = (220, 38, 38)  # red-600
WN   = (217,119,  6)  # amber-600
GD   = ( 22,163, 74)  # green-600

def fnt(sz=11, bold=False):
    for path in [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf"  if bold else "C:/Windows/Fonts/arial.ttf",
    ]:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, sz)
            except: pass
    return ImageFont.load_default()

img = Image.new("RGB", (W, H), BG)
d   = ImageDraw.Draw(img)

# ── subtle grid ───────────────────────────────────────────────
for x in range(0, W, 44):
    d.line([(x,0),(x,H)], fill=(255,255,255,3), width=1)
for y in range(0, H, 44):
    d.line([(0,y),(W,y)], fill=(255,255,255,3), width=1)

# ══ HEADER ════════════════════════════════════════════════════
NAV = 58
d.rectangle([0,0,W,NAV], fill=( 9, 9,11))
d.rectangle([0,NAV-1,W,NAV], fill=BD)

# logo icon (indigo shield)
LX, LY = 20, NAV//2
def shield(ox,oy,sz=15):
    pts=[
        (ox, oy-sz),(ox+sz*.8,oy-sz*.5),(ox+sz*.8,oy+sz*.2),
        (ox,oy+sz),(ox-sz*.8,oy+sz*.2),(ox-sz*.8,oy-sz*.5),
    ]
    d.polygon(pts, fill=AC)
    # checkmark
    d.line([(ox-sz*.3,oy+sz*.1),(ox-sz*.05,oy+sz*.4),(ox+sz*.4,oy-sz*.3)],
           fill=TX, width=2)

shield(LX+14, LY)

d.text((LX+32, LY-11), "FraudDetector", font=fnt(15,True), fill=TX)
d.text((LX+33, LY+3),  "Risk Intelligence Platform", font=fnt(8), fill=TX3)

# nav links
nav_items = ["Dashboard","Flags","Analytics","Chains"]
nx = 220
for i,item in enumerate(nav_items):
    col = TX if i==0 else TX3
    bg  = S3 if i==0 else None
    if bg:
        d.rounded_rectangle([nx-6,LY-10,nx+len(item)*7+2,LY+12], radius=5, fill=bg)
    d.text((nx, LY-8), item, font=fnt(11, i==0), fill=col)
    nx += len(item)*7 + 20

# header right — status + flags + clock
sx = W-320
d.rounded_rectangle([sx,LY-13,sx+180,LY+13], radius=6, fill=S1, outline=BD)
d.ellipse([sx+10,LY-4,sx+17,LY+3], fill=GD)
d.text((sx+22,LY-8), "System operational", font=fnt(10), fill=TX2)
d.line([sx+150,LY-8,sx+151,LY+8], fill=BD, width=1)
d.text((sx+156,LY-8), "14", font=fnt(11,True), fill=DG)
d.text((sx+170,LY-8), " flags", font=fnt(10), fill=TX3)

d.rounded_rectangle([W-120,LY-13,W-16,LY+13], radius=6, fill=S1, outline=BD)
d.text((W-114,LY-8), "08:04:32 IST", font=fnt(10), fill=TX3)

# ══ HERO ══════════════════════════════════════════════════════
HY = NAV+10
HH = 165
d.rounded_rectangle([16,HY,W-16,HY+HH], radius=10, fill=S1, outline=BD)

# hero left content
d.text((32,HY+14), "REAL-TIME FRAUD DETECTION", font=fnt(8,True), fill=AC3)
# gradient title simulation — draw "Catch fraud" in white, "before it lands." in indigo
d.text((32,HY+30), "Catch fraud", font=fnt(22,True), fill=TX)
d.text((32,HY+56), "before it lands.", font=fnt(22,True), fill=AC2)
d.text((32,HY+86), "Advanced PostgreSQL rules engine — recursive CTEs, LATERAL joins,",
       font=fnt(9), fill=TX3)
d.text((32,HY+100), "PL/pgSQL triggers. Flags appear within milliseconds of INSERT.",
       font=fnt(9), fill=TX3)

# chips
chips_ac = ["Recursive CTE","LATERAL Join","RANGE BETWEEN"]
chips_sl = ["PL/pgSQL Triggers","Materialized View","PERCENT_RANK"]
cx2 = 32
for chip in chips_ac:
    cw2 = len(chip)*6+16
    d.rounded_rectangle([cx2,HY+118,cx2+cw2,HY+133], radius=10,
                         fill=(AC[0]//8,AC[1]//8,AC[2]//4+10), outline=(*AC,80))
    d.text((cx2+7,HY+120), chip, font=fnt(8,True), fill=AC3)
    cx2 += cw2+6
for chip in chips_sl:
    cw2 = len(chip)*6+16
    d.rounded_rectangle([cx2,HY+118,cx2+cw2,HY+133], radius=10, fill=S3, outline=BD)
    d.text((cx2+7,HY+120), chip, font=fnt(8,True), fill=TX3)
    cx2 += cw2+6

# hero stats
hstats = [("14",DG,"OPEN FLAGS"),("326",AC2,"TRANSACTIONS"),("72.4",WN,"AVG RISK")]
sx2 = 32
d.line([(30,HY+140),(560,HY+141)], fill=BD, width=1)
for val,col,lbl in hstats:
    d.text((sx2,HY+146), val, font=fnt(16,True), fill=col)
    sx2 += len(val)*9+4
    d.text((sx2,HY+148), lbl, font=fnt(8), fill=TX3)
    sx2 += len(lbl)*5+28

# hero right — illustration area (gradient block)
himg_x = W-16-320
d.rectangle([himg_x,HY+1,W-17,HY+HH-1], fill=S1)
# load actual hero image if available
hero_path = "dashboard/hero-bg.png"
if os.path.exists(hero_path):
    from PIL import Image as PILImage
    hi = PILImage.open(hero_path).convert("RGB")
    hi = hi.resize((320, HH-2), PILImage.LANCZOS)
    # apply mask: fade left edge
    from PIL import ImageFilter
    mask = PILImage.new("L", (320, HH-2), 0)
    md = ImageDraw.Draw(mask)
    for x in range(320):
        alpha = min(255, int(255 * max(0, (x-60)/180)))
        md.line([(x,0),(x,HH-2)], fill=alpha)
    img.paste(hi, (himg_x, HY+1), mask)
else:
    # fallback gradient
    for x in range(320):
        a = int(40 * x/320)
        d.line([(himg_x+x,HY+1),(himg_x+x,HY+HH-1)], fill=(AC[0]//6,AC[1]//6,AC[2]//4))

# ══ SECTION: OVERVIEW ════════════════════════════════════════
SY = HY+HH+14
d.text((16,SY), "OVERVIEW", font=fnt(8,True), fill=TX3)
d.line([(76,SY+5),(W-16,SY+6)], fill=BD, width=1)

# ══ KPI CARDS ═════════════════════════════════════════════════
KY = SY+16
KH = 76
kpis = [
    ("TOTAL TRANSACTIONS","326",AC,  "last hour: 12", .65),
    ("OPEN FLAGS",        "14", DG,  "unresolved",    .45),
    ("AVG RISK SCORE",    "72.4",WN, "open flags",    .72),
    ("ACTIVE USERS 24H",  "8",  GD,  "24h distinct",  .40),
    ("TXNS LAST HOUR",    "12", TX3, "past 60 min",   .30),
    ("VOLUME 24H",    "₹4,82,000",TX3,"total amount", .55),
]
n_k=6; gap=10; pad=16
kw=(W-pad*2-gap*(n_k-1))//n_k

for i,(lbl,val,col,sub,pct) in enumerate(kpis):
    x=pad+i*(kw+gap)
    d.rounded_rectangle([x,KY,x+kw,KY+KH], radius=8, fill=S1, outline=BD)
    # accent top line
    d.rectangle([x+1,KY,x+kw-1,KY+1], fill=col)
    d.text((x+10,KY+8),  lbl, font=fnt(7,True), fill=TX3)
    d.text((x+10,KY+22), val, font=fnt(18,True), fill=col if col!=TX3 else TX2)
    d.text((x+10,KY+KH-16), sub, font=fnt(8), fill=TX3)
    # bottom fill bar
    bw2=int((kw-20)*pct)
    d.rounded_rectangle([x+10,KY+KH-6,x+10+bw2,KY+KH-4], radius=1,
                         fill=col if col!=TX3 else BD2)

# ══ SECTION: ANALYTICS ═══════════════════════════════════════
AY = KY+KH+16
d.text((16,AY), "ANALYTICS", font=fnt(8,True), fill=TX3)
d.line([(78,AY+5),(W-16,AY+6)], fill=BD, width=1)

CY = AY+16
CW1,CW2,CH = 570,W-570-16*3,195

# Merchant chart card
d.rounded_rectangle([16,CY,16+CW1,CY+CH], radius=8, fill=S1, outline=BD)
d.text((30,CY+12), "Merchant Fraud Rate", font=fnt(12,True), fill=TX)
d.text((30,CY+27), "Rolling 7-day · RANGE BETWEEN window", font=fnt(8), fill=TX3)
merch=[("WazirX",28.5,True),("CoinDCX",21.0,True),("MPL",14.3,True),
       ("Dream11",8.6,False),("PhonePe",3.2,False),("Swiggy",1.1,False)]
bx1,bx2=38,16+CW1-18
by1,by2=CY+50,CY+CH-24
bw3=(bx2-bx1)//len(merch)-7
for i,(name,rate,is_hi) in enumerate(merch):
    bx=bx1+i*(bw3+7)
    bh=int((rate/32)*(by2-by1-6))
    top=by2-bh
    color=DG if is_hi else AC
    d.rounded_rectangle([bx,top,bx+bw3,by2], radius=4, fill=color)
    d.text((bx+2,top-13), f"{rate}%", font=fnt(8,True), fill=TX)
    d.text((bx+2,by2+4), name[:6], font=fnt(7), fill=TX3)

# User risk chart card
rx3=16+CW1+12
d.rounded_rectangle([rx3,CY,rx3+CW2,CY+CH], radius=8, fill=S1, outline=BD)
d.text((rx3+12,CY+12), "User Risk Ranking", font=fnt(12,True), fill=TX)
d.text((rx3+12,CY+27), "PERCENT_RANK + NTILE(10) · top 8", font=fnt(8), fill=TX3)
users=[("Rahul S",5),("Anjali M",4),("Arjun N",4),("Rohan G",3),
       ("Priya P",3),("Vikram S",2),("Sonal K",2),("Dev R",1)]
bax1=rx3+72; bax2=rx3+CW2-18; max_f=6; rh=14; rg=6
for i,(name,cnt) in enumerate(users):
    ry5=CY+46+i*(rh+rg)
    blen=int((cnt/max_f)*(bax2-bax1))
    alpha=int(200-i*18)
    for xx in range(blen):
        t2=xx/max(blen-1,1)
        rc=tuple(int(DG[j]*(.7+.3*(1-t2))) for j in range(3))
        d.rectangle([bax1+xx,ry5,bax1+xx+1,ry5+rh], fill=rc)
    d.text((rx3+8,ry5+2), name, font=fnt(9), fill=TX2)
    d.text((bax1+blen+5,ry5+2), str(cnt), font=fnt(9,True), fill=TX)

# ══ SECTION: FLAGS ════════════════════════════════════════════
FY = CY+CH+16
d.text((16,FY), "OPEN FRAUD FLAGS", font=fnt(8,True), fill=TX3)
d.line([(128,FY+5),(W-16,FY+6)], fill=BD, width=1)

TY=FY+16
rows=[
    ("MULE_CHAIN",         AC,  90,"Rahul Sharma","UnknownShop","₹15,000","chain_depth:3",   "2m ago"),
    ("VELOCITY_10M",       DG,  85,"Anjali Mehta","WazirX",     "₹950",  "txn_count_10m:7", "5m ago"),
    ("HIGH_AMOUNT_ANOMALY",DG,  75,"Arjun Nair",  "CoinDCX",    "₹95,000","ratio:475",      "1h ago"),
    ("MULTI_DEVICE_1H",    WN,  80,"Rohan Gupta", "MPL Games",  "₹2,200","devices_1h:4",   "18m ago"),
    ("RAPID_REPEAT",       WN,  70,"Priya Patel", "Dream11",    "₹1,100","gap_seconds:28",  "34m ago"),
]
row_h=26; hdr_h=22
tbl_h=hdr_h+row_h*len(rows)+4
tw3=W-32

d.rounded_rectangle([16,TY,16+tw3,TY+tbl_h], radius=8, fill=S1, outline=BD)
# header row
d.rectangle([17,TY,16+tw3-1,TY+hdr_h], fill=S2)
d.rectangle([17,TY,16+tw3-1,TY+1], fill=BD)
cols=[("RULE",148),("RISK",82),("USER",130),("MERCHANT",110),("AMOUNT",92),("DETAILS",0)]
hx3=28
for col,cw4 in cols:
    d.text((hx3,TY+6), col, font=fnt(7,True), fill=TX3)
    hx3+=cw4 if cw4 else 0

for ri,(rule,color,score,user,merch2,amt,det,when) in enumerate(rows):
    ry6=TY+hdr_h+ri*row_h
    if ri%2:
        d.rectangle([17,ry6,16+tw3-1,ry6+row_h], fill=S2)
    rx5=28
    # monospace badge
    pw=len(rule)*5+14
    badge_bg={AC:(12,10,45),DG:(40,8,8),WN:(40,30,5)}
    badge_bd={AC:(*AC,100),DG:(*DG,100),WN:(*WN,100)}
    d.rounded_rectangle([rx5,ry6+4,rx5+pw,ry6+row_h-4], radius=4,
                         fill=badge_bg.get(color,(20,20,25)),
                         outline=badge_bd.get(color,(*BD2,255)))
    d.text((rx5+5,ry6+7), rule, font=fnt(8,True), fill=color)
    rx5+=148
    # score bar
    blen3=int(score*0.36)
    for xx in range(blen3):
        t3=xx/max(blen3-1,1)
        rc=tuple(int(WN[j]+(DG[j]-WN[j])*t3) for j in range(3))
        d.rectangle([rx5+xx,ry6+10,rx5+xx+1,ry6+16], fill=rc)
    d.text((rx5+blen3+5,ry6+7), str(score), font=fnt(9,True), fill=TX)
    rx5+=82
    d.text((rx5,ry6+7), user,  font=fnt(9,True), fill=TX);  rx5+=130
    d.text((rx5,ry6+7), merch2,font=fnt(9), fill=TX2);     rx5+=110
    d.text((rx5,ry6+7), amt,   font=fnt(9,True), fill=TX); rx5+=92
    d.text((rx5,ry6+7), "{"+det+"}", font=fnt(8), fill=TX3)

# ══ FOOTER ════════════════════════════════════════════════════
footY=TY+tbl_h+12
d.rectangle([0,footY,W,H], fill=S1)
d.rectangle([0,footY,W,footY+1], fill=BD)

# footer logo
shield(32, footY+22, sz=12)
d.text((50,footY+13), "FraudDetector", font=fnt(12,True), fill=TX)
d.text((50,footY+28), "Real-time fraud detection engine · raw SQL · no ML",
       font=fnt(8), fill=TX3)

# footer links
fl_x=400
for group,items in [
    ("DETECTION RULES",["VELOCITY_10M","RAPID_REPEAT","MULE_CHAIN","HIGH_AMOUNT_ANOMALY"]),
    ("RESOURCES",["GitHub Repository","API Reference","SQL Highlights","SmartInventory"]),
]:
    d.text((fl_x,footY+8), group, font=fnt(7,True), fill=TX3)
    for j,item in enumerate(items):
        d.text((fl_x,footY+20+j*13), item, font=fnt(9), fill=TX2)
    fl_x+=200

# footer bottom bar
btmY = footY+78
d.line([(16,btmY),(W-16,btmY)], fill=BD, width=1)
d.text((16,btmY+8), "© 2026 Ansh · MIT License", font=fnt(8), fill=TX3)
# tech tags
tags=["Python 3.11","PostgreSQL 15","FastAPI","38 tests"]
tx4=W-16
for tag in reversed(tags):
    tw4=len(tag)*5+14
    tx4-=tw4+6
    d.rounded_rectangle([tx4,btmY+6,tx4+tw4,btmY+18], radius=3, fill=S2, outline=BD)
    d.text((tx4+5,btmY+8), tag, font=fnt(7), fill=TX3)

# save
os.makedirs("assets", exist_ok=True)
out="assets/dashboard-preview.png"
img.save(out,"PNG",optimize=True)
print(f"✓  {out}  {W}×{H}")
