import streamlit as st
from PIL import Image, ImageDraw
import io

st.set_page_config(layout="wide", page_title="Weave Visualizer")

st.markdown("""
<style>
/* Style checkboxes as square toggle cells */
div[data-testid="stCheckbox"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 44px !important;
    height: 44px !important;
    margin: 2px !important;
}
div[data-testid="stCheckbox"] label {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 40px !important;
    height: 40px !important;
    border-radius: 6px !important;
    border: 1.5px solid #444 !important;
    cursor: pointer !important;
    background: #1e1e2e !important;
    transition: background 0.12s !important;
}
div[data-testid="stCheckbox"]:has(input:checked) label {
    background: #1a56db !important;
    border-color: #1a56db !important;
}
div[data-testid="stCheckbox"] p { display: none !important; }
div[data-testid="stCheckbox"] svg { display: none !important; }
div[data-testid="stCheckbox"] input {
    position: absolute; opacity: 0;
    width: 40px; height: 40px; cursor: pointer; margin: 0;
}
div[data-testid="column"] { padding: 0 1px !important; min-width: 0 !important; }
div[data-testid="stHorizontalBlock"] { gap: 0 !important; flex-wrap: nowrap !important; }
</style>
""", unsafe_allow_html=True)

st.title("🧵 Weave Visualizer")

# ── Presets ───────────────────────────────────────────────────────────────────
PRESETS = {
    "Plain":     [[0,1],[1,0]],
    "Twill 2/2": [[1,1,0,0],[0,1,1,0],[0,0,1,1],[1,0,0,1]],
    "Basket":    [[1,1,0,0],[1,1,0,0],[0,0,1,1],[0,0,1,1]],
    "Satin":     [[1,0,0,0,0],[0,0,1,0,0],[0,0,0,0,1],[0,1,0,0,0],[0,0,0,1,0]],
    "Herring":   [[1,0,0,1],[1,0,0,1],[0,1,1,0],[0,1,1,0]],
}

# ── Session state ─────────────────────────────────────────────────────────────
def _default_grid(r, c):
    return [[0]*c for _ in range(r)]

if "rows"        not in st.session_state: st.session_state.rows = 4
if "cols"        not in st.session_state: st.session_state.cols = 4
if "grid"        not in st.session_state: st.session_state.grid = _default_grid(4, 4)
if "warp_color"  not in st.session_state: st.session_state.warp_color  = "#d43030"
if "weft_color"  not in st.session_state: st.session_state.weft_color  = "#2255cc"
if "bg_color"    not in st.session_state: st.session_state.bg_color    = "#f5f0e8"
if "fabric_size" not in st.session_state: st.session_state.fabric_size = 60
if "zoom_level"  not in st.session_state: st.session_state.zoom_level  = 4

# ── Helpers ───────────────────────────────────────────────────────────────────
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

    for i in range(fs):   # weft base layer
        y0, y1 = i*cell_px+pad, (i+1)*cell_px-pad
        draw.rectangle([0, y0, sz, y1], fill=weft_rgb)
        draw.rectangle([0, y1-gap, sz, y1], fill=weft_dark)
        draw.rectangle([0, y0, sz, y0+gap], fill=weft_hi)

    for j in range(fs):   # warp base layer
        x0, x1 = j*cell_px+pad, (j+1)*cell_px-pad
        draw.rectangle([x0, 0, x1, sz], fill=warp_rgb)
        draw.rectangle([x1-gap, 0, x1, sz], fill=warp_dark)
        draw.rectangle([x0, 0, x0+gap, sz], fill=warp_hi)

    for i in range(fs):   # over-thread per cell
        for j in range(fs):
            x, y = j*cell_px, i*cell_px
            if big_pattern[i][j] == 1:   # warp on top
                x0,x1 = x+pad, x+cell_px-pad
                y0,y1 = y-pad, y+cell_px+pad
                draw.rounded_rectangle([x0,y0,x1,y1], radius=r, fill=warp_rgb)
                draw.rectangle([x1-gap,y0,x1,y1], fill=warp_dark)
                draw.rectangle([x0,y0,x0+gap,y1], fill=warp_hi)
            else:                         # weft on top
                x0,x1 = x-pad, x+cell_px+pad
                y0,y1 = y+pad, y+cell_px-pad
                draw.rounded_rectangle([x0,y0,x1,y1], radius=r, fill=weft_rgb)
                draw.rectangle([x0,y1-gap,x1,y1], fill=weft_dark)
                draw.rectangle([x0,y0,x1,y0+gap], fill=weft_hi)
    return img

def make_fabric():
    g, R, C, fs = st.session_state.grid, st.session_state.rows, st.session_state.cols, st.session_state.fabric_size
    return [[g[i%R][j%C] for j in range(fs)] for i in range(fs)]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    new_r = st.slider("Rows",    2, 12, st.session_state.rows, key="row_slider")
    new_c = st.slider("Columns", 2, 12, st.session_state.cols, key="col_slider")
    if new_r != st.session_state.rows or new_c != st.session_state.cols:
        st.session_state.rows, st.session_state.cols = new_r, new_c
        resize_grid(new_r, new_c)
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
        st.session_state.grid = _default_grid(st.session_state.rows, st.session_state.cols); st.rerun()
    if st.button("Fill all"):
        st.session_state.grid = [[1]*st.session_state.cols for _ in range(st.session_state.rows)]; st.rerun()

# ── Lifting plan grid ─────────────────────────────────────────────────────────
st.subheader("Lifting plan — click cells to toggle")

R = st.session_state.rows
C = st.session_state.cols
g = st.session_state.grid

# Column number headers
hcols = st.columns([0.3] + [1]*C)
for j in range(C):
    hcols[j+1].markdown(
        f"<div style='text-align:center;font-size:11px;color:#888;margin-bottom:2px'>{j+1}</div>",
        unsafe_allow_html=True)

# Grid rows — each cell is a checkbox (styled as blue square when checked)
for i in range(R):
    rcols = st.columns([0.3] + [1]*C)
    rcols[0].markdown(
        f"<div style='text-align:right;font-size:11px;color:#888;padding-top:12px;padding-right:4px'>{i+1}</div>",
        unsafe_allow_html=True)
    for j in range(C):
        new_val = rcols[j+1].checkbox(
            label=" ",
            value=bool(g[i][j]),
            key=f"cell_{i}_{j}",
            label_visibility="hidden"
        )
        if int(new_val) != g[i][j]:
            st.session_state.grid[i][j] = int(new_val)
            st.rerun()

# ── Fabric display ────────────────────────────────────────────────────────────
st.divider()
big  = make_fabric()
fs   = st.session_state.fabric_size
zoom = st.session_state.zoom_level

out_img  = draw_fabric(big, fs, cell_px=4)
zoom_fs  = min(fs, max(4, 24 // zoom + 4))
zoom_img = draw_fabric(big, zoom_fs, cell_px=zoom * 8)

col1, col2 = st.columns(2)
with col1:
    st.caption("Full fabric (zoomed out)")
    st.image(out_img, use_container_width=True)

with col2:
    st.caption(f"Zoomed in (×{zoom})")
    st.image(zoom_img, use_container_width=True)
    buf = io.BytesIO()
    zoom_img.save(buf, format="PNG")
    st.download_button("⬇ Download", buf.getvalue(), "fabric.png", "image/png")