"""
Generate assets/dashboard-preview.png  1280×720
Matches dashboard v3: violet/rose palette, custom logo, SVG icons, Inter font.
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

W, H = 1280, 720

# ── palette ───────────────────────────────────────────────────
BG   = (5,   7,  15)
S0   = (8,  12,  24)
S1   = (12,  18,  34)
S2   = (17,  25,  48)
S3   = (25,  37,  58)
BD   = (255, 255, 255,  13)   # rgba border
TX   = (226, 232, 244)
TX2  = (124, 143, 168)
TX3  = ( 61,  80, 104)

VI   = (124, 106, 245)   # violet
RO   = (244,  63, 114)   # rose
GO   = (249, 115,  22)   # orange
EM   = ( 52, 211, 153)   # emerald
SKY  = ( 56, 189, 248)   # sky
SL   = (148, 163, 184)   # slate

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
d   = ImageDraw.Draw(img, "RGBA")

# ── ambient glow blobs ────────────────────────────────────────
def blob(cx, cy, r, color, alpha_max=50):
    for i in range(r, 0, -4):
        a = int(alpha_max * (1 - i/r)**1.4)
        d.ellipse([cx-i, cy-i, cx+i, cy+i], fill=(*color, a))

blob(-120, -80,  480, VI, 38)
blob(W+100, 300, 380, RO, 28)
blob(W//2,  H+60, 320, SKY, 20)

# ── subtle grid ───────────────────────────────────────────────
for x in range(0, W, 44):
    d.line([(x,0),(x,H)], fill=(255,255,255, 4), width=1)
for y in range(0, H, 44):
    d.line([(0,y),(W,y)], fill=(255,255,255, 4), width=1)

# ══════════════════════════════════════════════════════════════
# NAV
# ══════════════════════════════════════════════════════════════
NAV_H = 54
d.rectangle([0, 0, W, NAV_H], fill=(5, 7, 15, 210))
d.rectangle([0, NAV_H-1, W, NAV_H], fill=(255,255,255, 10))

# shield logo
def shield(ox, oy, sz=28):
    # body
    pts = []
    for a in range(-90, 270, 5):
        t = a * math.pi/180
        pts.append((ox + sz*0.52*math.cos(t), oy + sz*0.6*math.sin(t)))
    # simplified shield via polygon
    sp = [
        (ox, oy-sz*.52),
        (ox+sz*.44, oy-sz*.28),
        (ox+sz*.44, oy+sz*.12),
        (ox, oy+sz*.52),
        (ox-sz*.44, oy+sz*.12),
        (ox-sz*.44, oy-sz*.28),
    ]
    # gradient shield: draw layered
    for i, col in enumerate([(*VI,180), (*RO,120), (*VI,60)]):
        scale = 1 - i*0.08
        pts2 = [(ox+(x-ox)*scale, oy+(y-oy)*scale) for x,y in sp]
        d.polygon(pts2, fill=col)
    # checkmark
    d.line([(ox-sz*.16, oy+sz*.04),(ox-sz*.02, oy+sz*.18),(ox+sz*.20, oy-sz*.12)],
           fill=(255,255,255,230), width=2)

shield(26, NAV_H//2)

# logo text
d.text((46, 10), "FraudDetector", font=fnt(16, True), fill=TX)
d.text((47, 29), "RISK INTELLIGENCE", font=fnt(8), fill=TX3)

# separator
d.rectangle([195, 14, 196, NAV_H-14], fill=(255,255,255, 18))

# status chip
cx, cy2, cw, ch2 = 204, 14, 112, 26
d.rounded_rectangle([cx, cy2, cx+cw, cy2+ch2], radius=13,
                     fill=(52,211,153,22), outline=(52,211,153,45))
d.ellipse([cx+10, cy2+9, cx+16, cy2+15], fill=EM)
d.text((cx+20, cy2+6), "System Live", font=fnt(10), fill=EM)

# nav right — open flags
d.text((W-220, 8), "14", font=fnt(20, True), fill=RO)
d.text((W-220, 30), "OPEN FLAGS", font=fnt(8), fill=TX3)
# clock
d.rounded_rectangle([W-130, 14, W-20, 40], radius=6, fill=S1, outline=(255,255,255,18))
d.text((W-124, 20), "08:04:32 IST", font=fnt(10), fill=TX3)

# ══════════════════════════════════════════════════════════════
# KPI CARDS  (6 across)
# ══════════════════════════════════════════════════════════════
kpis = [
    ("TOTAL TXNS",      "326",        VI,  "last hour: 12"),
    ("OPEN FLAGS",      "14",         RO,  "unresolved alerts"),
    ("AVG RISK SCORE",  "72.4",       GO,  "across open flags"),
    ("ACTIVE USERS",    "8",          EM,  "24h distinct"),
    ("TXNS LAST HOUR",  "12",         SKY, "past 60 min"),
    ("VOLUME 24H",      "₹4,82,000",  SL,  "total amount"),
]
n_k = 6
pad = 20
gap = 10
kw  = (W - pad*2 - gap*(n_k-1)) // n_k
ky  = NAV_H + 14
kh  = 88

for i, (label, val, color, sub) in enumerate(kpis):
    x = pad + i*(kw+gap)
    # card bg
    d.rounded_rectangle([x, ky, x+kw, ky+kh], radius=12,
                         fill=(*S1, 180), outline=(255,255,255, 18))
    # top-right glow
    for r_ in range(50, 0, -5):
        a = int(28 * (1 - r_/50)**1.5)
        d.ellipse([x+kw-r_//2, ky-r_//2, x+kw+r_//2, ky+r_//2],
                  fill=(*color, a))
    # highlight shimmer top edge
    d.rectangle([x+1, ky+1, x+kw-1, ky+2], fill=(255,255,255, 12))
    # label
    d.text((x+12, ky+10), label, font=fnt(8, True), fill=TX3)
    # value
    d.text((x+12, ky+24), val, font=fnt(21, True), fill=color)
    # sub
    d.text((x+12, ky+kh-18), sub, font=fnt(9), fill=TX3)
    # bottom fill bar
    bw2 = int(kw * [.65, .45, .72, .40, .30, .55][i])
    d.rounded_rectangle([x+10, ky+kh-6, x+10+bw2, ky+kh-4],
                         radius=1, fill=(*color, 90))

# ══════════════════════════════════════════════════════════════
# SECTION HEADER
# ══════════════════════════════════════════════════════════════
sy = ky + kh + 14
d.text((pad, sy), "ANALYTICS", font=fnt(9, True), fill=TX3)
d.rectangle([pad+80, sy+6, W-pad, sy+7], fill=(255,255,255, 14))
# badge
bx = W-pad-70
d.rounded_rectangle([bx-2, sy-1, bx+58, sy+14], radius=7,
                     fill=(*VI, 25), outline=(*VI, 50))
d.text((bx+2, sy+1), "Live data", font=fnt(8), fill=VI)

# ══════════════════════════════════════════════════════════════
# MERCHANT FRAUD RATE CHART
# ══════════════════════════════════════════════════════════════
cy3 = sy + 16
cw2, ch3 = 580, 192
d.rounded_rectangle([pad, cy3, pad+cw2, cy3+ch3], radius=12,
                     fill=(*S1, 160), outline=(255,255,255, 15))
# shimmer
d.rectangle([pad+1, cy3+1, pad+cw2-1, cy3+2], fill=(255,255,255, 10))
d.text((pad+14, cy3+12), "Merchant Fraud Rate", font=fnt(13, True), fill=TX)
d.text((pad+14, cy3+28), "Rolling 7-day · RANGE BETWEEN window", font=fnt(9), fill=TX3)

merch = [("WazirX",28.5,RO),("CoinDCX",21.0,RO),("MPL",14.3,RO),
         ("Dream11",8.6,VI),("PhonePe",3.2,VI),("Swiggy",1.1,VI)]
bx1, bx2 = pad+28, pad+cw2-18
by1, by2 = cy3+50, cy3+ch3-26
bw3 = (bx2-bx1) // len(merch) - 8
max_r = 32
for i, (name, rate, color) in enumerate(merch):
    bx3 = bx1 + i*(bw3+8)
    bh  = int((rate/max_r)*(by2-by1-6))
    top = by2 - bh
    # bar with gradient effect
    for yy in range(bh):
        alpha = int(180 + 60 * yy/max(bh,1))
        d.rectangle([bx3, by2-yy-1, bx3+bw3, by2-yy], fill=(*color, min(220,alpha)))
    # value label
    d.text((bx3+2, top-14), f"{rate}%", font=fnt(9, True), fill=TX)
    # x label
    d.text((bx3+2, by2+4), name[:6], font=fnt(8), fill=TX3)

# grid lines for chart
for pct in [0, 10, 20, 30]:
    gy = by2 - int(pct/max_r*(by2-by1))
    d.line([(bx1-6, gy),(bx2, gy)], fill=(255,255,255,8), width=1)
    d.text((pad+14, gy-5), f"{pct}%", font=fnt(7), fill=TX3)

# ══════════════════════════════════════════════════════════════
# USER RISK RANKING CHART
# ══════════════════════════════════════════════════════════════
rx = pad + cw2 + 14
rw = W - rx - pad
d.rounded_rectangle([rx, cy3, rx+rw, cy3+ch3], radius=12,
                     fill=(*S1, 160), outline=(255,255,255, 15))
d.rectangle([rx+1, cy3+1, rx+rw-1, cy3+2], fill=(255,255,255, 10))
d.text((rx+14, cy3+12), "User Risk Ranking", font=fnt(13, True), fill=TX)
d.text((rx+14, cy3+28), "PERCENT_RANK + NTILE(10) · top 8", font=fnt(9), fill=TX3)

users = [("Rahul S",5),("Anjali M",4),("Arjun N",4),("Rohan G",3),
         ("Priya P",3),("Vikram S",2),("Sonal K",2),("Dev R",1)]
bax1 = rx + 72
bax2 = rx + rw - 18
max_f = 6
rh3 = 15
rg  = 7
for i, (name, cnt) in enumerate(users):
    ry3 = cy3+46+i*(rh3+rg)
    blen = int((cnt/max_f)*(bax2-bax1))
    alpha = int(210 - i*18)
    # bar
    for xx in range(blen):
        a2 = int(alpha * (1 - xx/(blen+1)*.3))
        d.rectangle([bax1+xx, ry3, bax1+xx+1, ry3+rh3], fill=(*RO, a2))
    d.text((rx+10, ry3+2), name, font=fnt(10), fill=TX2)
    d.text((bax1+blen+5, ry3+2), str(cnt), font=fnt(10, True), fill=TX)

# ══════════════════════════════════════════════════════════════
# SECTION: OPEN FRAUD FLAGS
# ══════════════════════════════════════════════════════════════
ty = cy3 + ch3 + 14
d.text((pad, ty), "OPEN FRAUD FLAGS", font=fnt(9, True), fill=TX3)
d.rectangle([pad+128, ty+6, W-pad, ty+7], fill=(255,255,255, 14))

ty += 16
rows = [
    ("MULE_CHAIN",         VI,  90, "Rahul Sharma",  "UnknownShop",  "₹15,000",  "chain_depth:3",    "2m ago"),
    ("VELOCITY_10M",       RO,  85, "Anjali Mehta",  "WazirX",       "₹950",     "txn_count_10m:7",  "5m ago"),
    ("HIGH_AMOUNT_ANOMALY",RO,  75, "Arjun Nair",    "CoinDCX",      "₹95,000",  "ratio:475",        "1h ago"),
    ("MULTI_DEVICE_1H",    GO,  80, "Rohan Gupta",   "MPL Games",    "₹2,200",   "devices_1h:4",     "18m ago"),
    ("RAPID_REPEAT",       GO,  70, "Priya Patel",   "Dream11",      "₹1,100",   "gap_seconds:28",   "34m ago"),
]
row_h2 = 30
hdr_h2 = 22
tbl_h2 = hdr_h2 + row_h2*len(rows) + 4
tw2 = W - pad*2

d.rounded_rectangle([pad, ty, pad+tw2, ty+tbl_h2], radius=12,
                     fill=(*S1, 160), outline=(255,255,255, 15))
d.rectangle([pad+1, ty, pad+tw2-1, ty+hdr_h2], fill=(*S2, 120))
d.rectangle([pad+1, ty, pad+tw2-1, ty+2], fill=(255,255,255, 8))

# header
cols = [("RULE",145),("RISK",80),("USER",130),("MERCHANT",110),("AMOUNT",90),("DETAILS",0)]
hx2 = pad+16
for col,cw3 in cols:
    d.text((hx2, ty+6), col, font=fnt(8, True), fill=TX3)
    hx2 += cw3 if cw3 else 0

for ri, (rule, color, score, user, merch2, amt, det, when) in enumerate(rows):
    ry4 = ty + hdr_h2 + ri*row_h2
    if ri % 2:
        d.rectangle([pad+1, ry4, pad+tw2-1, ry4+row_h2], fill=(*S0, 80))

    rx4 = pad+16
    # pill
    pw = len(rule)*5+14
    pill_bg = {VI:(30,20,60), RO:(60,10,30), GO:(55,30,8)}
    pill_brd= {VI:(80,55,160),RO:(140,30,70),GO:(130,70,20)}
    d.rounded_rectangle([rx4, ry4+6, rx4+pw, ry4+row_h2-6],
                         radius=9, fill=pill_bg.get(color,(30,30,40)),
                         outline=pill_brd.get(color,(60,60,80)))
    d.text((rx4+5, ry4+9), rule, font=fnt(9, True), fill=color)
    rx4 += 145

    # score bar
    blen2 = int(score * 0.36)
    # gradient bar
    for xx in range(blen2):
        t2 = xx/max(blen2-1,1)
        rc = tuple(int(GO[j]+(RO[j]-GO[j])*t2) for j in range(3))
        d.rectangle([rx4+xx, ry4+12, rx4+xx+1, ry4+row_h2-10], fill=rc)
    d.text((rx4+blen2+5, ry4+9), str(score), font=fnt(10, True), fill=TX)
    rx4 += 80
    d.text((rx4, ry4+9), user,   font=fnt(10, True), fill=TX);  rx4+=130
    d.text((rx4, ry4+9), merch2, font=fnt(10), fill=TX2);       rx4+=110
    d.text((rx4, ry4+9), amt,    font=fnt(10, True), fill=EM);  rx4+=90
    d.text((rx4, ry4+9), "{"+det+"}", font=fnt(9), fill=TX3)

# ── footer ─────────────────────────────────────────────────────
d.rectangle([0, H-26, W, H], fill=(4, 6, 12))
d.rectangle([0, H-27, W, H-26], fill=(255,255,255, 10))
d.text((pad, H-18), "FraudDetector · Risk Intelligence · PostgreSQL · FastAPI",
       font=fnt(9), fill=TX3)
d.text((W-430, H-18),
       "Demo · recursive CTEs · LATERAL joins · PL/pgSQL triggers · 38 tests",
       font=fnt(9), fill=(45, 60, 85))

os.makedirs("assets", exist_ok=True)
out = "assets/dashboard-preview.png"
img.save(out, "PNG", optimize=True)
print(f"✓  {out}  {W}×{H}")
