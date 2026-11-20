"""Generate assets/dashboard-preview.png  (1280x720, dark theme)."""
from PIL import Image, ImageDraw, ImageFont
import os, math, random

W, H   = 1280, 720
BG     = (6,   9,  16)
S1     = (13,  17, 23)
S2     = (17,  24, 32)
BORDER = (30,  42, 56)
TEXT   = (232, 240, 254)
MUTED  = (90, 112, 144)
BLUE   = (79,  158, 255)
GREEN  = (16,  185, 129)
RED    = (239,  68,  73)
AMBER  = (245, 158,  11)
PURPLE = (168,  85, 247)
CYAN   = (6,   182, 212)

def fnt(sz=11, bold=False):
    for path in (
        ("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        ("C:/Windows/Fonts/arialbd.ttf"  if bold else "C:/Windows/Fonts/arial.ttf"),
    ):
        if os.path.exists(path):
            try: return ImageFont.truetype(path, sz)
            except: pass
    return ImageFont.load_default()

img = Image.new("RGB", (W, H), BG)
d   = ImageDraw.Draw(img)

# subtle grid lines
for x in range(0, W, 40):
    d.line([(x,0),(x,H)], fill=(12,18,28), width=1)
for y in range(0, H, 40):
    d.line([(0,y),(W,y)], fill=(12,18,28), width=1)

# ── NAV ───────────────────────────────────────────────────────
d.rectangle([0,0,W,54], fill=(6,9,16))
d.rectangle([0,54,W,55], fill=BORDER)
# shield icon placeholder
d.rounded_rectangle([20,15,38,39], radius=5, outline=BLUE, width=2)
d.text((23,20), "✦", font=fnt(10,True), fill=BLUE)
d.text((44,19), "FraudDetector", font=fnt(16,True), fill=TEXT)
# live badge
d.rounded_rectangle([182,18,222,36], radius=9, fill=(40,8,8), outline=(120,30,30))
d.text((191,22), "LIVE", font=fnt(9,True), fill=RED)
# right pulse
d.ellipse([W-180,22,W-173,29], fill=GREEN)
d.text((W-167,19), "Refreshes every 15s", font=fnt(10), fill=MUTED)
d.text((W-80,20), "08:04:32", font=fnt(10), fill=(58,80,112))

# ── KPI CARDS ─────────────────────────────────────────────────
kpis = [
    ("TOTAL TXNS",      "326",        BLUE,   "last hour: 12"),
    ("OPEN FLAGS",      "14",         RED,    "unresolved"),
    ("AVG RISK SCORE",  "72.4",       AMBER,  "open flags"),
    ("ACTIVE USERS",    "8",          GREEN,  "24h distinct"),
    ("TXNS LAST HOUR",  "12",         PURPLE, "past 60 min"),
    ("VOLUME 24H",      "₹4,82,000",  CYAN,   "total amount"),
]
n_k   = len(kpis)
kw    = (W - 40 - (n_k-1)*10) // n_k
ky    = 68
kh    = 86

for i,(label,val,color,sub) in enumerate(kpis):
    x = 20 + i*(kw+10)
    # card bg + border
    d.rounded_rectangle([x,ky,x+kw,ky+kh], radius=10, fill=S1, outline=BORDER)
    # top accent bar gradient simulation
    for px in range(kw-2):
        alpha = int(180 * (1 - px/(kw-2)) * 0.4 + 180 * (px/(kw-2)) * 1.0)
        c2 = tuple(min(255,int(c*0.5)) for c in color)
        c3 = tuple(int(c2[j] + (color[j]-c2[j])*(px/(kw-2))) for j in range(3))
        d.line([(x+1+px,ky),(x+1+px,ky+2)], fill=c3)
    # glow
    for r_ in range(3,0,-1):
        d.rectangle([x,ky,x+kw,ky+r_],
                    fill=tuple(int(c*0.15) for c in color))
    d.text((x+12,ky+10), label, font=fnt(8,True), fill=MUTED)
    d.text((x+12,ky+24), val,   font=fnt(20,True), fill=color)
    d.text((x+12,ky+kh-18), sub, font=fnt(9),  fill=MUTED)

# ── SECTION LABEL ─────────────────────────────────────────────
sy = ky+kh+18
d.text((20,sy), "ANALYTICS", font=fnt(9,True), fill=MUTED)
d.line([(100,sy+6),(W-20,sy+6)], fill=BORDER, width=1)

# ── MERCHANT FRAUD RATE CHART ─────────────────────────────────
cy2 = sy+18
cw, ch = 540, 190
d.rounded_rectangle([20,cy2,20+cw,cy2+ch], radius=10, fill=S1, outline=BORDER)
d.text((34,cy2+12), "Merchant Fraud Rate",  font=fnt(13,True), fill=TEXT)
d.text((34,cy2+28), "Rolling 7-day · RANGE BETWEEN window", font=fnt(9), fill=MUTED)

merch_data = [("WazirX",28.5,RED),("CoinDCX",21.0,RED),("MPL",14.3,RED),
              ("Dream11",8.6,BLUE),("PhonePe",3.2,BLUE),("Swiggy",1.1,BLUE)]
bx1,bx2 = 44, 20+cw-16
by1,by2 = cy2+50, cy2+ch-24
bw2 = (bx2-bx1) // len(merch_data) - 6
max_r2 = 32
for i,(name,rate,color) in enumerate(merch_data):
    bx = bx1 + i*(bw2+6)
    bh = int((rate/max_r2)*(by2-by1-8))
    top = by2-bh
    # bar
    d.rounded_rectangle([bx,top,bx+bw2,by2], radius=4, fill=color)
    # value
    d.text((bx+bw2//2-10,top-14), f"{rate}%", font=fnt(9,True), fill=TEXT)
    # label
    d.text((bx+2,by2+4), name[:6], font=fnt(8), fill=MUTED)

# ── USER RISK CHART ───────────────────────────────────────────
rx2 = 20+cw+12
rw, rch = W-rx2-20, 190
d.rounded_rectangle([rx2,cy2,rx2+rw,cy2+rch], radius=10, fill=S1, outline=BORDER)
d.text((rx2+14,cy2+12), "User Risk Ranking",  font=fnt(13,True), fill=TEXT)
d.text((rx2+14,cy2+28), "PERCENT_RANK + NTILE · top 8", font=fnt(9), fill=MUTED)

users2 = [("Rahul S",5),("Anjali M",4),("Arjun N",4),("Rohan G",3),
          ("Priya P",3),("Vikram S",2),("Sonal K",2),("Dev R",1)]
bar_x1 = rx2+90
bar_x2 = rx2+rw-20
max_f2  = 6
rbar_h = 15
rbar_g = 7
for i,(name,cnt) in enumerate(users2):
    ry3 = cy2+46+i*(rbar_h+rbar_g)
    blen = int((cnt/max_f2)*(bar_x2-bar_x1))
    alpha = int(200 - i*18)
    c3 = (RED[0],RED[1],RED[2])
    d.text((rx2+14,ry3+2), name, font=fnt(10), fill=MUTED)
    d.rounded_rectangle([bar_x1,ry3,bar_x1+blen,ry3+rbar_h], radius=3, fill=c3)
    d.text((bar_x1+blen+5,ry3+2), str(cnt), font=fnt(10,True), fill=TEXT)

# ── FLAGS TABLE ────────────────────────────────────────────────
ty = cy2+ch+28
d.text((20,ty), "OPEN FRAUD FLAGS", font=fnt(9,True), fill=MUTED)
d.line([(162,ty+6),(W-20,ty+6)], fill=BORDER, width=1)

ty += 16
rows = [
    ("MULE_CHAIN",         PURPLE, 90, "Rahul Sharma",  "UnknownShop",  15000,  "chain_depth:3",        "2m ago"),
    ("VELOCITY_10M",       RED,    85, "Anjali Mehta",  "WazirX",        950,   "txn_count_10m:7",     "5m ago"),
    ("HIGH_AMOUNT_ANOMALY",RED,    75, "Arjun Nair",    "CoinDCX",      95000,  "ratio:475",           "1h ago"),
    ("MULTI_DEVICE_1H",    AMBER,  80, "Rohan Gupta",   "MPL Games",     2200,  "distinct_devices:4",  "18m ago"),
    ("RAPID_REPEAT",       BLUE,   70, "Priya Patel",   "Dream11",       1100,  "gap_seconds:28",      "34m ago"),
]
row_h = 30
hdr_h = 24
tbl_h = hdr_h + row_h*len(rows) + 4
d.rounded_rectangle([20,ty,W-20,ty+tbl_h], radius=10, fill=S1, outline=BORDER)

cols = [("RULE",145),("RISK",80),("USER",130),("MERCHANT",110),("AMOUNT",90),("DETAILS",0)]
hx = 32
d.rectangle([20,ty,W-20,ty+hdr_h], fill=S2)
d.line([(20,ty+hdr_h),(W-20,ty+hdr_h)], fill=BORDER, width=1)
for col,cw2 in cols:
    d.text((hx,ty+7), col, font=fnt(8,True), fill=MUTED)
    hx += cw2 if cw2 else 0

for ri,(rule,color,score,user,merch,amt,det,when) in enumerate(rows):
    ry4 = ty+hdr_h+ri*row_h+1
    if ri%2==1:
        d.rectangle([21,ry4,W-21,ry4+row_h-1], fill=(10,14,20))
    rx3 = 32
    # pill
    pw = len(rule)*5+14
    pill_colors = {
        RED:    ((60,10,10),(120,30,30)),
        PURPLE: ((40,10,60),(80,30,120)),
        AMBER:  ((50,30,5),(100,65,10)),
        BLUE:   ((10,30,60),(20,60,120)),
    }
    bg_c, br_c = pill_colors.get(color,((30,30,30),(60,60,60)))
    d.rounded_rectangle([rx3,ry4+6,rx3+pw,ry4+row_h-6], radius=9, fill=bg_c, outline=br_c)
    d.text((rx3+5,ry4+9), rule, font=fnt(8,True), fill=color)
    rx3 += 145
    # score bar
    blen2 = int(score*0.36)
    d.rounded_rectangle([rx3,ry4+11,rx3+blen2,ry4+17], radius=2,
                         fill=(max(0,RED[0]-30),max(0,RED[1]-20),max(0,RED[2]-20)))
    d.rectangle([rx3,ry4+11,rx3+blen2,ry4+17], fill=RED)
    d.text((rx3+blen2+5,ry4+9), str(score), font=fnt(10,True), fill=TEXT)
    rx3 += 80
    d.text((rx3,ry4+9), user,                   font=fnt(10,True), fill=TEXT);  rx3+=130
    d.text((rx3,ry4+9), merch,                  font=fnt(10), fill=MUTED);      rx3+=110
    d.text((rx3,ry4+9), f"₹{amt:,}",           font=fnt(10,True), fill=GREEN); rx3+=90
    d.text((rx3,ry4+9), "{"+det+"}",            font=fnt(9), fill=MUTED)

# ── FOOTER ─────────────────────────────────────────────────────
d.rectangle([0,H-26,W,H], fill=(5,8,14))
d.line([(0,H-27),(W,H-27)], fill=BORDER, width=1)
d.text((20,H-19), "FraudDetector · PostgreSQL · FastAPI · Advanced SQL",
       font=fnt(9), fill=MUTED)
d.text((W-370,H-19),
       "Demo mode · recursive CTEs · LATERAL joins · PL/pgSQL triggers",
       font=fnt(9), fill=(45,65,88))

os.makedirs("assets", exist_ok=True)
out = "assets/dashboard-preview.png"
img.save(out, "PNG", optimize=True)
print(f"✓  {out}  {W}×{H}")
