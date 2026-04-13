import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import json

st.set_page_config(layout="wide", page_title="Weave Visualizer")

st.markdown("""
<style>
div[data-testid="stCheckbox"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 40px !important;
    height: 40px !important;
    margin: 1px !important;
}
div[data-testid="stCheckbox"] label {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 36px !important;
    height: 36px !important;
    border-radius: 5px !important;
    border: 1.5px solid #444 !important;
    cursor: pointer !important;
    background: #1e1e2e !important;
    transition: background 0.12s !important;
}
div[data-testid="stCheckbox"]:has(input:checked) label {
    background: #1a56db !important;
    border-color: #1a56db !important;
}
div[data-testid="stCheckbox"] p   { display: none !important; }
div[data-testid="stCheckbox"] svg { display: none !important; }
div[data-testid="stCheckbox"] input {
    position: absolute; opacity: 0;
    width: 36px; height: 36px; cursor: pointer; margin: 0;
}
div[data-testid="column"] { padding: 0 1px !important; min-width: 0 !important; }
div[data-testid="stHorizontalBlock"] { gap: 0 !important; flex-wrap: nowrap !important; }
div[data-testid="stButton"] > button[kind="primary"] {
    background: #1a56db !important;
    color: white !important;
    border: none !important;
    font-size: 16px !important;
    padding: 0.6rem 2rem !important;
    border-radius: 8px !important;
}
/* Styling for AI Metric Cards */
div[data-testid="stMetricValue"] {
    font-size: 1.4rem !important;
    color: #e8e8f0 !important;
}
div[data-testid="stMetricLabel"] {
    color: #888 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 0.8rem !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🧵 Weave Visualizer")

# ── Presets ───────────────────────────────────────────────────────────────────
PRESETS = {
    "Plain":     [[1,0],[0,1]],
    "Twill 2/2": [[1,1,0,0],[0,1,1,0],[0,0,1,1],[1,0,0,1]],
    "Basket":    [[1,1,0,0],[1,1,0,0],[0,0,1,1],[0,0,1,1]],
    "Satin":     [[1,0,0,0,0],[0,0,1,0,0],[0,0,0,0,1],[0,1,0,0,0],[0,0,0,1,0]],
    "Herring":   [[1,0,0,1],[1,0,0,1],[0,1,1,0],[0,1,1,0]],
}

# ── Session state ─────────────────────────────────────────────────────────────
def _default_grid(r, c):
    return [[0]*c for _ in range(r)]

if "rows"           not in st.session_state: st.session_state.rows = 4
if "cols"           not in st.session_state: st.session_state.cols = 4
if "grid"           not in st.session_state: st.session_state.grid = _default_grid(4, 4)
if "warp_color"     not in st.session_state: st.session_state.warp_color  = "#d43030"
if "weft_color"     not in st.session_state: st.session_state.weft_color  = "#2255cc"
if "bg_color"       not in st.session_state: st.session_state.bg_color    = "#f5f0e8"
if "fabric_size"    not in st.session_state: st.session_state.fabric_size = 60
if "zoom_level"     not in st.session_state: st.session_state.zoom_level  = 4
if "generated"      not in st.session_state: st.session_state.generated   = False
if "ai_report"      not in st.session_state: st.session_state.ai_report   = None
if "snap_grid"      not in st.session_state: st.session_state.snap_grid   = None
if "snap_threading" not in st.session_state: st.session_state.snap_threading = None
if "snap_lifting"   not in st.session_state: st.session_state.snap_lifting   = None
if "snap_shafts"    not in st.session_state: st.session_state.snap_shafts    = 0

# ── Weave analysis ────────────────────────────────────────────────────────────
def compute_heald_and_lifting(grid):
    R = len(grid)
    C = len(grid[0]) if R else 0
    col_signatures = {}
    threading = []
    shaft_count = 0
    for j in range(C):
        sig = tuple(grid[i][j] for i in range(R))
        if sig not in col_signatures:
            col_signatures[sig] = shaft_count
            shaft_count += 1
        threading.append(col_signatures[sig])
    shaft_rep = {}
    for j, sh in enumerate(threading):
        if sh not in shaft_rep:
            shaft_rep[sh] = j
    lifting = []
    for i in range(R):
        row = [grid[i][shaft_rep[sh]] for sh in range(shaft_count)]
        lifting.append(row)
    threading_grid = [[0]*C for _ in range(shaft_count)]
    for col, shaft in enumerate(threading):
        threading_grid[shaft][col] = 1
    return threading_grid, lifting, shaft_count

# ── AI explanation (Google Gemini) ────────────────────────────────────────────
def get_ai_explanation(grid, num_shafts):
    R = len(grid)
    C = len(grid[0]) if R else 0
    warp_ups = sum(grid[i][j] for i in range(R) for j in range(C))
    total = R * C
    float_ratio = warp_ups / total if total else 0

    grid_str = "\n".join(
        f"Pick {R-i}: {grid[i]}" for i in range(R)
    )

    prompt = f"""You are an expert textile engineer specializing in woven fabric construction.
Analyze this weave design repeat and provide a structured technical report.

Design repeat ({R} picks × {C} ends):
{grid_str}
(1 = warp up / warp float, 0 = weft up / weft float)

Warp float ratio: {float_ratio:.2f}
Number of shafts required: {num_shafts}
Repeat size: {R} picks × {C} ends

Use exactly this JSON structure:
{{
  "weave_name": "string — name of this weave structure",
  "weave_family": "string — e.g. plain, twill, satin, derivative",
  "description": "string — 2-3 sentences describing the interlacement pattern",
  "num_shafts": {num_shafts},
  "repeat": "{R}P x {C}E",
  "float_length": "string — max float length for warp and weft",
  "epi_range": "string — typical ends per inch range e.g. 60-80",
  "ppi_range": "string — typical picks per inch range e.g. 55-70",
  "yarn_count_range": "string — suitable yarn count range e.g. 20s-40s Ne",
  "cover_factor": "string — low / medium / high with brief reason",
  "fabric_weight": "string — typical gsm range",
  "typical_end_uses": ["list", "of", "3-5", "end uses"],
  "loom_type": "string — suitable loom types",
  "fabric_properties": {{
    "drape": "string",
    "hand_feel": "string",
    "durability": "string",
    "breathability": "string"
  }},
  "design_notes": "string — any special notes about this weave pattern"
}}"""

    try:
        import google.generativeai as genai
        import os
        
        api_key = st.secrets["GEMINI_API_KEY"]
        if not api_key:
            return {"error": "GEMINI_API_KEY environment variable is not set."}
            
        genai.configure(api_key=api_key)
        
        # Enforcing JSON output natively
        model = genai.GenerativeModel(
            'gemini-2.5-flash-lite',
            generation_config={"response_mime_type": "application/json"}
        )
        
        response = model.generate_content(prompt)
        return json.loads(response.text)
        
    except Exception as e:
        return {"error": str(e)}

# ── Drawing helpers ───────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def darken(rgb, f=0.55):  return tuple(int(c*f) for c in rgb)
def lighten(rgb, f=1.6):  return tuple(min(255, int(c*f)) for c in rgb)

def draw_fabric(big_pattern, fs, cell_px):
    warp_rgb = hex_to_rgb(st.session_state.warp_color)
    weft_rgb = hex_to_rgb(st.session_state.weft_color)
    bg_rgb   = hex_to_rgb(st.session_state.bg_color)
    warp_dark, warp_hi = darken(warp_rgb), lighten(warp_rgb)
    weft_dark, weft_hi = darken(weft_rgb), lighten(weft_rgb)
    sz  = fs * cell_px
    img = Image.new("RGB", (sz, sz), bg_rgb)
    draw = ImageDraw.Draw(img)
    gap = max(1, cell_px // 10)
    pad = max(2, cell_px // 5)
    r   = max(1, cell_px // 4)
    for i in range(fs):
        y0, y1 = i*cell_px+pad, (i+1)*cell_px-pad
        draw.rectangle([0, y0, sz, y1], fill=weft_rgb)
        draw.rectangle([0, y1-gap, sz, y1], fill=weft_dark)
        draw.rectangle([0, y0, sz, y0+gap], fill=weft_hi)
    for j in range(fs):
        x0, x1 = j*cell_px+pad, (j+1)*cell_px-pad
        draw.rectangle([x0, 0, x1, sz], fill=warp_rgb)
        draw.rectangle([x1-gap, 0, x1, sz], fill=warp_dark)
        draw.rectangle([x0, 0, x0+gap, sz], fill=warp_hi)
    for i in range(fs):
        for j in range(fs):
            x, y = j*cell_px, i*cell_px
            if big_pattern[i][j] == 1:
                x0,x1 = x+pad, x+cell_px-pad
                y0,y1 = y-pad, y+cell_px+pad
                draw.rounded_rectangle([x0,y0,x1,y1], radius=r, fill=warp_rgb)
                draw.rectangle([x1-gap,y0,x1,y1], fill=warp_dark)
                draw.rectangle([x0,y0,x0+gap,y1], fill=warp_hi)
            else:
                x0,x1 = x-pad, x+cell_px+pad
                y0,y1 = y+pad, y+cell_px-pad
                draw.rounded_rectangle([x0,y0,x1,y1], radius=r, fill=weft_rgb)
                draw.rectangle([x0,y1-gap,x1,y1], fill=weft_dark)
                draw.rectangle([x0,y0,x1,y0+gap], fill=weft_hi)
    return img

def draw_plan(matrix, rows, cols, cell=36,
              filled=(26,86,219), empty=(30,30,46),
              border=(80,80,80), bg=(15,15,25),
              row_labels=None, col_labels=None, flip_rows=True):
    LPAD = 30
    BPAD = 24
    w = LPAD + cols * cell
    h = rows * cell + BPAD
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except:
        font = ImageFont.load_default()

    for r in range(rows):
        dr = (rows - 1 - r) if flip_rows else r
        for c in range(cols):
            x0 = LPAD + c * cell
            y0 = dr * cell
            x1, y1 = x0 + cell - 2, y0 + cell - 2
            val = matrix[r][c]
            fill = filled if val else empty
            draw.rectangle([x0, y0, x1, y1], fill=fill, outline=border)
            if val:
                cx, cy = (x0+x1)//2, (y0+y1)//2
                s = max(4, cell//5)
                draw.line([cx-s, cy-s, cx+s, cy+s], fill=(200,220,255), width=2)
                draw.line([cx+s, cy-s, cx-s, cy+s], fill=(200,220,255), width=2)

    if col_labels:
        for c, lbl in enumerate(col_labels):
            x = LPAD + c * cell + cell // 2
            draw.text((x, rows*cell + 4), str(lbl), fill=(160,160,160), font=font, anchor="mt")

    if row_labels:
        for r, lbl in enumerate(row_labels):
            dr = (rows - 1 - r) if flip_rows else r
            y = dr * cell + cell // 2
            draw.text((LPAD - 4, y), str(lbl), fill=(160,160,160), font=font, anchor="rm")

    return img

def make_fabric(grid=None):
    if grid is None:
        grid = st.session_state.grid
    R, C, fs = st.session_state.rows, st.session_state.cols, st.session_state.fabric_size
    return [[grid[i%R][j%C] for j in range(fs)] for i in range(fs)]

def resize_grid(new_r, new_c):
    old = st.session_state.grid
    old_r, old_c = len(old), len(old[0]) if old else 0
    st.session_state.grid = [
        [old[i][j] if i < old_r and j < old_c else 0 for j in range(new_c)]
        for i in range(new_r)
    ]

def load_preset(name):
    p = [row[:] for row in PRESETS[name]]
    st.session_state.rows = len(p)
    st.session_state.cols = len(p[0])
    st.session_state.grid = p
    st.session_state.generated = False
    st.session_state.ai_report = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    new_r = st.slider("Rows (picks)",   2, 12, st.session_state.rows, key="row_slider")
    new_c = st.slider("Columns (ends)", 2, 12, st.session_state.cols, key="col_slider")
    if new_r != st.session_state.rows or new_c != st.session_state.cols:
        st.session_state.rows, st.session_state.cols = new_r, new_c
        resize_grid(new_r, new_c)
        st.session_state.generated = False
        st.rerun()

    st.session_state.fabric_size = st.slider("Fabric size", 20, 120, st.session_state.fabric_size)
    st.session_state.zoom_level  = st.slider("Zoom level",  1,  10,  st.session_state.zoom_level)

    st.divider()
    st.subheader("Thread Colors")
    st.session_state.warp_color = st.color_picker("Warp",       st.session_state.warp_color)
    st.session_state.weft_color = st.color_picker("Weft",       st.session_state.weft_color)
    st.session_state.bg_color   = st.color_picker("Background", st.session_state.bg_color)

    st.divider()
    st.subheader("Presets")
    pc = st.columns(2)
    for idx, name in enumerate(PRESETS):
        with pc[idx % 2]:
            if st.button(name, key=f"preset_{name}"):
                load_preset(name); st.rerun()

    st.divider()
    if st.button("Clear"):
        st.session_state.grid = _default_grid(st.session_state.rows, st.session_state.cols)
        st.session_state.generated = False
        st.rerun()
    if st.button("Fill all"):
        st.session_state.grid = [[1]*st.session_state.cols for _ in range(st.session_state.rows)]
        st.session_state.generated = False
        st.rerun()

# ── Design input grid ─────────────────────────────────────────────────────────
st.subheader("Design Canvas")
st.caption("1 = warp up (■ blue)  |  0 = weft up (□ dark)  |  Pick rows shown bottom→top")

R = st.session_state.rows
C = st.session_state.cols
g = st.session_state.grid

hcols = st.columns([0.35] + [1]*C)
for j in range(C):
    hcols[j+1].markdown(
        f"<div style='text-align:center;font-size:11px;color:#888;margin-bottom:2px'>E{j+1}</div>",
        unsafe_allow_html=True)

for i in range(R):
    display_i = R - 1 - i
    rcols = st.columns([0.35] + [1]*C)
    rcols[0].markdown(
        f"<div style='text-align:right;font-size:11px;color:#888;padding-top:10px;padding-right:6px'>P{display_i+1}</div>",
        unsafe_allow_html=True)
    for j in range(C):
        new_val = rcols[j+1].checkbox(
            label=" ",
            value=bool(g[display_i][j]),
            key=f"cell_{display_i}_{j}",
            label_visibility="hidden"
        )
        if int(new_val) != g[display_i][j]:
            st.session_state.grid[display_i][j] = int(new_val)
            st.session_state.generated = False

# ── Generate button ───────────────────────────────────────────────────────────
st.markdown("###")
col_btn, _ = st.columns([1, 3])
with col_btn:
    generate_clicked = st.button("Generate", type="primary", use_container_width=True)

if generate_clicked:
    grid_snap = [row[:] for row in st.session_state.grid]
    threading_grid, lifting, num_shafts = compute_heald_and_lifting(grid_snap)
    st.session_state.snap_grid      = grid_snap
    st.session_state.snap_threading = threading_grid
    st.session_state.snap_lifting   = lifting
    st.session_state.snap_shafts    = num_shafts
    st.session_state.generated      = True
    with st.spinner("Analysing weave with AI..."):
        st.session_state.ai_report = get_ai_explanation(grid_snap, num_shafts)

# ── Output section ────────────────────────────────────────────────────────────
if st.session_state.generated and st.session_state.snap_grid:
    grid_snap      = st.session_state.snap_grid
    threading_grid = st.session_state.snap_threading
    lifting        = st.session_state.snap_lifting
    num_shafts     = st.session_state.snap_shafts
    R_s = len(grid_snap)
    C_s = len(grid_snap[0])

    st.markdown("---")

    # ── Technical Drafting Plans ──────────────────────────────────────────────
    st.subheader("Technical Drafting Plans")
    st.caption(f"{num_shafts} shaft(s) required  ·  End numbers along bottom, shaft numbers on left")
    
    lc, rc = st.columns([1.5, 1], gap="large")
    
    with lc:
        st.markdown("**Heald (Threading) Plan**")
        thead_img = draw_plan(
            threading_grid, rows=num_shafts, cols=C_s, cell=42,
            row_labels=[f"S{s+1}" for s in range(num_shafts)],
            col_labels=[str(j+1) for j in range(C_s)],
            flip_rows=True,
        )
        st.image(thead_img, use_container_width=False)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Design Repeat**")
        design_img = draw_plan(
            grid_snap, rows=R_s, cols=C_s, cell=42,
            filled=(26,86,219), empty=(30,30,46),
            row_labels=[f"P{i+1}" for i in range(R_s)],
            col_labels=[str(j+1) for j in range(C_s)],
            flip_rows=True,
        )
        st.image(design_img, use_container_width=False)

    with rc:
        st.markdown("**Lifting Plan**")
        lift_img = draw_plan(
            lifting, rows=R_s, cols=num_shafts, cell=42,
            row_labels=[f"P{i+1}" for i in range(R_s)],
            col_labels=[f"S{s+1}" for s in range(num_shafts)],
            flip_rows=True,
        )
        st.image(lift_img, use_container_width=False)


    st.markdown("---")

    # ── Fabric Simulation ─────────────────────────────────────────────────────
    st.subheader("Fabric Simulation")
    big      = make_fabric(grid_snap)
    fs       = st.session_state.fabric_size
    zoom     = st.session_state.zoom_level
    out_img  = draw_fabric(big, fs, cell_px=4)
    zoom_fs  = min(fs, max(4, 24 // zoom + 4))
    zoom_img = draw_fabric(big, zoom_fs, cell_px=zoom * 8)

    fc1, fc2 = st.columns(2)
    with fc1:
        st.caption("Full fabric (zoomed out)")
        st.image(out_img, use_container_width=True)
    with fc2:
        st.caption(f"Zoomed in (×{zoom})")
        st.image(zoom_img, use_container_width=True)
        buf = io.BytesIO()
        zoom_img.save(buf, format="PNG")
        st.download_button("⬇ Download Image", buf.getvalue(), "fabric.png", "image/png")

    st.markdown("---")

    # ── AI Weave Analysis ─────────────────────────────────────────────────────
    st.subheader("AI Weave Analysis")

    rpt = st.session_state.ai_report
    if rpt and "error" not in rpt:
        
        # Header block
        st.markdown(f"### {rpt.get('weave_name','—')}")
        st.markdown(
            f"<span style='background:#1e3a5f;color:#7eb8f7;padding:4px 12px;"
            f"border-radius:20px;font-size:13px;font-weight:600;letter-spacing:0.5px;'>"
            f"{rpt.get('weave_family','').upper()}</span>",
            unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"*{rpt.get('description','')}*")
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("#### Structural Specifications")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Shafts Required", rpt.get("num_shafts", num_shafts))
        m2.metric("Repeat Size", rpt.get("repeat", "—"))
        m3.metric("Float Length", rpt.get("float_length", "—"))
        m4.metric("Cover Factor", rpt.get("cover_factor", "—").title())
        
        m5, m6, m7, m8 = st.columns(4)
        m5.metric("EPI (Ends/Inch)", rpt.get("epi_range", "—"))
        m6.metric("PPI (Picks/Inch)", rpt.get("ppi_range", "—"))
        m7.metric("Yarn Count Range", rpt.get("yarn_count_range", "—"))
        m8.metric("Fabric Weight", rpt.get("fabric_weight", "—"))

        st.markdown("#### Fabric Properties")
        def info_card(label, value, col):
            col.markdown(
                f"""<div style='background:#1a1a2e;border:1px solid #2d2d4e;
                border-radius:8px;padding:14px 16px;margin-bottom:8px; height: 100%;'>
                <div style='font-size:11px;color:#888;margin-bottom:6px;
                text-transform:uppercase;letter-spacing:0.5px'>{label}</div>
                <div style='font-size:14px;color:#e8e8f0;font-weight:500;
                word-wrap:break-word;line-height:1.4'>{value}</div></div>""",
                unsafe_allow_html=True)

        p = rpt.get("fabric_properties", {})
        p1, p2, p3, p4 = st.columns(4)
        info_card("Drape", p.get("drape","—"), p1)
        info_card("Hand Feel", p.get("hand_feel","—"), p2)
        info_card("Durability", p.get("durability","—"), p3)
        info_card("Breathability", p.get("breathability","—"), p4)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # End uses pills
        uses = rpt.get("typical_end_uses", [])
        st.markdown("**Typical End Uses**")
        pills = " ".join(
            f"<span style='background:#2a2a3e;color:#b0b0c0;padding:6px 14px;"
            f"border-radius:20px;font-size:13px;margin-right:6px;margin-bottom:6px;display:inline-block; border: 1px solid #3d3d5e;'>"
            f"{u}</span>" for u in uses)
        st.markdown(pills, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Bottom notes
        lc2, rc2 = st.columns(2)
        with lc2:
            info_card("Suitable Loom Type", rpt.get('loom_type','—'), lc2)
        with rc2:
            info_card("Design Notes", rpt.get('design_notes','—'), rc2)

    elif rpt and "error" in rpt:
        st.error(f"AI analysis failed: {rpt['error']}")
    else:
        st.info("AI analysis pending.")

else:
    st.info("Draw your design repeat above, then click Generate to see the technical plans, fabric simulation, and expert analysis.")