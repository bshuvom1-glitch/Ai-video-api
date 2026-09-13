#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔴 FILE STORE - RENDER DEPLOYMENT VERSION
All features: Thumbnail, Free Watch, Locked Download, Manage, Delete
"""

import os, sys, sqlite3, hashlib, secrets, logging
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template_string, request, redirect, url_for,
                   session, send_from_directory, flash, abort)
from werkzeug.utils import secure_filename

# ==================== RENDER-COMPATIBLE PATHS ====================
# Render এ Disk mount করলে RENDER_DATA_DIR env var use হবে
# না করলে local folder এ data রাখবে
BASE_DIR = os.environ.get("RENDER_DATA_DIR", os.path.abspath(os.path.dirname(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "file_store.db")
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "SHUVOM_2024")
OWNER_NAME = os.environ.get("OWNER_NAME", "SHUVOM")

ALLOWED_VIDEO_EXT = {"mp4","webm","mkv","mov","avi","m4v"}
ALLOWED_IMG_EXT = {"png","jpg","jpeg","gif","webp"}
ALLOWED_FILE_EXT = {"zip","rar","7z","pdf","apk","exe","doc","docx","txt",
                    "png","jpg","jpeg","gif","mp3","json","html","css","js","py"}

for d in [UPLOAD_DIR, os.path.join(UPLOAD_DIR,"videos"),
          os.path.join(UPLOAD_DIR,"files"), os.path.join(UPLOAD_DIR,"bg"),
          os.path.join(UPLOAD_DIR,"thumbnails")]:
    os.makedirs(d, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 5000 * 1024 * 1024
app.config['MAX_FORM_MEMORY_SIZE'] = 500 * 1024 * 1024
app.config['MAX_FORM_PARTS'] = 10000

# ==================== DB ====================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, description TEXT DEFAULT '', video_filename TEXT DEFAULT '',
        video_original TEXT DEFAULT '', video_size INTEGER DEFAULT 0,
        password_hash TEXT NOT NULL, views INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL, filename TEXT NOT NULL, original_name TEXT NOT NULL,
        file_size INTEGER DEFAULT 0, file_type TEXT DEFAULT '', sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')), FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attachments (id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL, filename TEXT NOT NULL, original_name TEXT NOT NULL,
        file_size INTEGER DEFAULT 0, file_type TEXT DEFAULT '', downloads INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')), FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS unlock_log (id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL, ip TEXT DEFAULT '', unlocked_at TEXT DEFAULT (datetime('now')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS bg_video (id INTEGER PRIMARY KEY CHECK (id=1), filename TEXT)''')
    conn.commit()

    def add(t, col, d):
        try: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {d}")
        except sqlite3.OperationalError: pass
    for t, col, d in [
        ("videos","file_type","TEXT DEFAULT ''"),("videos","sort_order","INTEGER DEFAULT 0"),
        ("videos","file_size","INTEGER DEFAULT 0"),("videos","original_name","TEXT DEFAULT ''"),
        ("videos","filename","TEXT DEFAULT ''"),("attachments","file_type","TEXT DEFAULT ''"),
        ("attachments","downloads","INTEGER DEFAULT 0"),("attachments","file_size","INTEGER DEFAULT 0"),
        ("items","video_filename","TEXT DEFAULT ''"),("items","video_original","TEXT DEFAULT ''"),
        ("items","video_size","INTEGER DEFAULT 0"),("items","thumbnail","TEXT DEFAULT ''")]:
        add(t, col, d)
    conn.commit(); conn.close()

init_db()

def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()
def is_admin(): return session.get('admin_logged_in') is True
def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if not is_admin(): return redirect(url_for('admin_login'))
        return f(*a, **k)
    return w
def get_file_size(p):
    try: return os.path.getsize(p)
    except: return 0
def format_size(s):
    s = float(s or 0)
    for u in ['B','KB','MB','GB']:
        if s < 1024: return f"{s:.2f} {u}"
        s /= 1024
    return f"{s:.2f} TB"
def get_ext(fn): return fn.rsplit('.',1)[-1].lower() if '.' in fn else ''
def get_bg_video():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT filename FROM bg_video WHERE id=1")
    r = c.fetchone(); conn.close()
    return r['filename'] if r else None

# ==================== CSS ====================
BASE_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Poppins:wght@300;400;600&display=swap');
*{margin:0;padding:0;box-sizing:border-box}html,body{min-height:100%}
body{font-family:'Poppins',sans-serif;background:#050000;color:#ff4444;min-height:100vh;overflow-x:hidden}
#bg-video{position:fixed;top:0;left:0;width:100vw;height:100vh;object-fit:cover;z-index:-3;opacity:.35;filter:brightness(.6) saturate(1.4) hue-rotate(-10deg) contrast(1.2);pointer-events:none}
#bg-overlay{position:fixed;inset:0;z-index:-2;pointer-events:none;background:radial-gradient(circle at 50% 50%,rgba(0,0,0,.35),rgba(0,0,0,.85) 80%),linear-gradient(180deg,rgba(80,0,0,.35),rgba(0,0,0,.9))}
#bg-grid{position:fixed;inset:0;z-index:-1;pointer-events:none;background-image:linear-gradient(rgba(255,0,0,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(255,0,0,.06) 1px,transparent 1px);background-size:45px 45px;animation:gridMove 20s linear infinite}
@keyframes gridMove{to{background-position:45px 45px,45px 45px}}
#particles{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden}
.hacker{position:absolute;width:38px;height:44px;animation:floatUp linear infinite;filter:drop-shadow(0 0 10px rgba(255,0,0,.9))}
.hacker .hood{position:absolute;top:0;left:50%;transform:translateX(-50%);width:34px;height:28px;background:linear-gradient(180deg,#1a0000,#0a0000);border:2px solid #f00;border-radius:50% 50% 20% 20%/60% 60% 40% 40%}
.hacker .face{position:absolute;top:10px;left:50%;transform:translateX(-50%);width:22px;height:15px;background:#050000;border-radius:50%;border:1px solid rgba(255,0,0,.6)}
.hacker .eye{position:absolute;top:15px;width:5px;height:5px;background:#f00;border-radius:50%;box-shadow:0 0 8px #f00;animation:hb 2.5s ease-in-out infinite}
.hacker .eye.left{left:12px}.hacker .eye.right{right:12px}
@keyframes hb{0%,90%,100%{opacity:1}95%{opacity:.1}}
.hacker .body{position:absolute;bottom:0;left:50%;transform:translateX(-50%);width:26px;height:14px;background:#1a0000;border:1px solid rgba(255,0,0,.5);border-radius:30% 30% 10% 10%}
@keyframes floatUp{0%{transform:translateY(105vh) scale(.55);opacity:0}10%,90%{opacity:.95}100%{transform:translateY(-15vh) scale(.7);opacity:0}}
.orb{position:absolute;border-radius:50%;background:radial-gradient(circle,#f44,transparent 70%);animation:ob linear infinite;opacity:.6}
@keyframes ob{0%{opacity:0}20%,80%{opacity:.7}100%{transform:translate(60px,-100vh);opacity:0}}
.bin{position:absolute;color:#f00;font-family:monospace;opacity:.25;animation:bf linear infinite;text-shadow:0 0 8px #f00;user-select:none}
@keyframes bf{0%{transform:translateY(-20vh);opacity:0}10%,90%{opacity:.4}100%{transform:translateY(110vh);opacity:0}}
.name-reveal{font-family:'Orbitron',sans-serif;font-size:clamp(34px,8vw,78px);font-weight:900;letter-spacing:10px;background:linear-gradient(90deg,#f00,#f66,#fff,#f66,#f00);background-size:300% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:sn 4s linear infinite;filter:drop-shadow(0 0 25px rgba(255,0,0,.9));margin-bottom:8px}
@keyframes sn{to{background-position:300% center}}
.container{position:relative;z-index:2;max-width:1200px;margin:0 auto;padding:20px}
.navbar{background:linear-gradient(135deg,rgba(30,0,0,.85),rgba(60,0,0,.75));border:1px solid rgba(255,0,0,.5);border-radius:15px;padding:18px 25px;margin-bottom:30px;display:flex;justify-content:space-between;align-items:center;backdrop-filter:blur(12px);flex-wrap:wrap;gap:10px}
.logo{font-family:'Orbitron',sans-serif;font-size:26px;font-weight:900;color:#f22;text-shadow:0 0 15px #f00,0 0 30px #f00;letter-spacing:3px}
.logo span{color:#fff}
.nav-links a{color:#f66;text-decoration:none;margin-left:20px;font-weight:600;padding:8px 16px;border-radius:8px;transition:all .3s}
.nav-links a:hover{background:rgba(255,0,0,.2);color:#fff;box-shadow:0 0 15px rgba(255,0,0,.5)}
.hero{text-align:center;padding:55px 20px;border:2px solid #f00;border-radius:20px;background:linear-gradient(135deg,rgba(30,0,0,.8),rgba(60,0,0,.5));box-shadow:0 0 50px rgba(255,0,0,.4);margin-bottom:40px;position:relative;overflow:hidden;backdrop-filter:blur(10px)}
.hero h1{font-family:'Orbitron',sans-serif;font-size:clamp(28px,6vw,52px);font-weight:900;color:#f22;text-shadow:0 0 20px #f00;letter-spacing:4px;margin-bottom:15px}
.hero p{color:#f99;font-size:16px;letter-spacing:3px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:25px;margin-bottom:40px}
.card{background:linear-gradient(135deg,rgba(26,0,0,.85),rgba(13,0,0,.8));border:1px solid rgba(255,0,0,.45);border-radius:15px;padding:20px;transition:all .35s;backdrop-filter:blur(8px)}
.card:hover{transform:translateY(-6px);border-color:#f00;box-shadow:0 0 50px rgba(255,0,0,.5)}
.card-icon{font-size:42px;margin-bottom:15px;text-align:center;filter:drop-shadow(0 0 12px #f00)}
.card-thumb{width:100%;height:180px;border-radius:10px;overflow:hidden;margin-bottom:15px;border:2px solid rgba(255,0,0,.5);background:#000;box-shadow:0 0 20px rgba(255,0,0,.3)}
.card-thumb img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .4s}
.card:hover .card-thumb img{transform:scale(1.05)}
.card h3{font-family:'Orbitron',sans-serif;color:#f33;font-size:20px;margin-bottom:12px;word-break:break-word}
.card p{color:#f99;font-size:14px;line-height:1.6;margin-bottom:15px}
.card-meta{display:flex;justify-content:space-between;font-size:12px;color:#c55;margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,0,0,.25);flex-wrap:wrap;gap:8px}
.btn{display:inline-block;padding:12px 26px;background:linear-gradient(135deg,#f00,#c00);color:#fff;text-decoration:none;border-radius:10px;font-weight:700;font-family:'Orbitron',sans-serif;letter-spacing:1px;border:none;cursor:pointer;transition:all .3s;box-shadow:0 0 20px rgba(255,0,0,.5);font-size:14px}
.btn:hover{background:linear-gradient(135deg,#f22,#f00);transform:translateY(-2px);box-shadow:0 0 40px rgba(255,0,0,.9)}
.btn-ghost{background:transparent;border:1px solid #f00;color:#f33;box-shadow:none}
.btn-ghost:hover{background:rgba(255,0,0,.25);color:#fff}
.btn-danger{background:linear-gradient(135deg,#600,#300);border:1px solid #f00}
.btn-danger:hover{background:linear-gradient(135deg,#f00,#900);box-shadow:0 0 25px rgba(255,0,0,.9)}
.btn-block{display:block;width:100%;text-align:center}
.btn-sm{padding:8px 14px;font-size:12px}
.btn-locked{background:linear-gradient(135deg,#553300,#332200);border:1px solid #fa0;color:#fc6}
.btn-locked:hover{background:linear-gradient(135deg,#885500,#553300);box-shadow:0 0 25px rgba(255,150,0,.7)}
.form-group{margin-bottom:20px}
.form-group label{display:block;color:#f66;margin-bottom:8px;font-weight:600;font-size:13px;letter-spacing:1px}
.form-group input,.form-group textarea{width:100%;padding:14px;background:rgba(10,0,0,.8);border:1px solid rgba(255,0,0,.45);border-radius:10px;color:#fff;font-size:14px;font-family:'Poppins',sans-serif;outline:none;transition:all .3s}
.form-group input:focus,.form-group textarea:focus{border-color:#f00;box-shadow:0 0 25px rgba(255,0,0,.5)}
.form-group textarea{min-height:100px;resize:vertical}
.alert{padding:15px 20px;border-radius:10px;margin-bottom:20px;font-weight:600;border-left:4px solid;word-break:break-word}
.alert-success{background:rgba(0,255,0,.12);border-color:#0f0;color:#6f6}
.alert-error{background:rgba(255,0,0,.15);border-color:#f00;color:#f66}
.alert-info{background:rgba(255,150,0,.12);border-color:#fa0;color:#fc6}
.footer{text-align:center;padding:30px;color:#a55;font-size:13px;border-top:1px solid rgba(255,0,0,.25);margin-top:40px}
.video-container{background:#000;border:2px solid #f00;border-radius:15px;overflow:hidden;box-shadow:0 0 50px rgba(255,0,0,.6);margin-bottom:25px}
.video-container video{width:100%;display:block;max-height:70vh;background:#000}
.video-tabs{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px;justify-content:center;padding:15px;background:rgba(20,0,0,.6);border-radius:12px;border:1px solid rgba(255,0,0,.35)}
.video-tab{padding:10px 18px;background:rgba(30,0,0,.85);color:#f88;border:1px solid rgba(255,0,0,.5);border-radius:8px;font-family:'Orbitron',sans-serif;font-size:13px;font-weight:700;cursor:pointer;transition:all .3s;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.video-tab.active{background:linear-gradient(135deg,#f22,#c00);color:#fff}
.file-list{margin-top:25px}
.file-item{display:flex;align-items:center;justify-content:space-between;padding:15px 20px;background:linear-gradient(135deg,rgba(21,0,0,.85),rgba(13,0,0,.8));border:1px solid rgba(255,0,0,.35);border-radius:10px;margin-bottom:10px;gap:12px;flex-wrap:wrap}
.file-info{display:flex;align-items:center;gap:15px;flex:1;min-width:0}
.file-icon{font-size:28px;filter:drop-shadow(0 0 10px #f00);flex-shrink:0}
.file-details h4{color:#f55;font-size:15px;margin-bottom:3px;word-break:break-all}
.file-details small{color:#c55;font-size:12px}
.lock-screen{text-align:center;padding:60px 30px;border:2px solid #f00;border-radius:20px;background:linear-gradient(135deg,rgba(30,0,0,.9),rgba(13,0,0,.85));max-width:500px;margin:40px auto;backdrop-filter:blur(12px)}
.lock-icon{font-size:80px;margin-bottom:20px;filter:drop-shadow(0 0 25px #f00)}
.lock-screen h2{font-family:'Orbitron',sans-serif;color:#f22;font-size:26px;margin-bottom:15px}
.lock-screen p{color:#f99;margin-bottom:30px}
.input-group{display:flex;gap:10px;flex-wrap:wrap}
.input-group input{flex:1;min-width:200px;padding:16px;background:rgba(10,0,0,.85);border:1px solid #f00;border-radius:12px;color:#fff;font-size:16px;text-align:center;font-family:'Orbitron',sans-serif}
.empty-state{text-align:center;padding:80px 20px;color:#a55}
.empty-state .icon{font-size:80px;margin-bottom:20px;opacity:.55}
.empty-state h3{font-family:'Orbitron',sans-serif;color:#f33;margin-bottom:10px}
.table-wrap{overflow-x:auto;border-radius:15px;border:1px solid rgba(255,0,0,.35)}
table{width:100%;border-collapse:collapse;background:rgba(13,0,0,.75)}
table th{background:linear-gradient(135deg,#2a0000,#1a0000);color:#f66;padding:15px;text-align:left;font-family:'Orbitron',sans-serif;font-size:13px;border-bottom:2px solid #f00;white-space:nowrap}
table td{padding:14px 15px;color:#f99;border-bottom:1px solid rgba(255,0,0,.18);font-size:14px;word-break:break-word}
table tr:hover td{background:rgba(255,0,0,.1);color:#fff}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;background:rgba(255,0,0,.25);border:1px solid #f00;color:#f55}
.badge-unlock{background:rgba(0,255,0,.2);border-color:#0f0;color:#6f6}
.badge-lock{background:rgba(255,150,0,.2);border-color:#fa0;color:#fc6}
.slot-row{display:flex;gap:10px;margin-bottom:12px;align-items:center;flex-wrap:wrap;padding:10px;background:rgba(20,0,0,.5);border:1px solid rgba(255,0,0,.25);border-radius:10px}
.slot-row:hover{border-color:rgba(255,0,0,.6)}
.slot-row input[type="file"]{display:block !important;flex:1;min-width:200px;padding:10px;background:rgba(10,0,0,.85);border:1px solid rgba(255,0,0,.5);border-radius:8px;color:#fff;font-size:13px;cursor:pointer;font-family:'Poppins',sans-serif}
.slot-row input[type="file"]::file-selector-button{background:linear-gradient(135deg,#f00,#c00);color:#fff;border:none;padding:8px 16px;border-radius:6px;font-family:'Orbitron',sans-serif;font-weight:700;cursor:pointer;margin-right:12px}
.slot-num{font-family:'Orbitron',sans-serif;color:#f55;font-weight:900;font-size:16px;text-align:center;background:rgba(255,0,0,.15);border:1px solid rgba(255,0,0,.5);border-radius:50%;width:34px;height:34px;line-height:32px;flex-shrink:0}
.remove-btn{background:linear-gradient(135deg,#600,#300);color:#fff;border:1px solid #f00;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:15px;flex-shrink:0}
.remove-btn:hover{background:linear-gradient(135deg,#f00,#900)}
.add-btn{display:block;margin:15px auto 0;padding:14px 32px;background:transparent;border:2px dashed #f00;color:#f55;border-radius:10px;font-family:'Orbitron',sans-serif;font-weight:700;cursor:pointer;transition:all .3s;font-size:14px}
.add-btn:hover{background:rgba(255,0,0,.15);color:#fff;border-style:solid}
.hint{color:#fc6;font-size:13px;margin-bottom:15px;padding:10px 14px;background:rgba(255,150,0,.1);border-left:3px solid #fa0;border-radius:5px}
.unlock-banner{background:linear-gradient(135deg,rgba(255,150,0,.15),rgba(255,80,0,.1));border:2px solid #fa0;border-radius:12px;padding:18px;margin-bottom:25px;text-align:center}
.unlock-banner p{color:#fc6;font-weight:600;margin-bottom:12px;font-size:14px}
.upload-zone{border:2px dashed rgba(255,0,0,.6);border-radius:15px;padding:30px;text-align:center;background:rgba(255,0,0,.04);transition:all .3s;cursor:pointer}
.upload-zone:hover{border-color:#f00;background:rgba(255,0,0,.1);box-shadow:0 0 30px rgba(255,0,0,.3) inset}
.upload-zone .icon{font-size:40px;margin-bottom:10px}
.upload-zone p{color:#f99;font-size:14px;word-break:break-word}
.upload-zone small{color:#c55;display:block;margin-top:8px}
.hero-thumb{width:100%;max-width:600px;margin:0 auto 20px;border-radius:12px;overflow:hidden;border:2px solid #f00;box-shadow:0 0 30px rgba(255,0,0,.5)}
.hero-thumb img{width:100%;display:block}
.manage-section{background:linear-gradient(135deg,rgba(30,0,0,.9),rgba(13,0,0,.85));border:2px solid #f00;border-radius:20px;padding:25px;margin-bottom:30px;backdrop-filter:blur(12px)}
.manage-section h2{font-family:'Orbitron',sans-serif;color:#f33;margin-bottom:20px;font-size:22px;text-shadow:0 0 15px rgba(255,0,0,.6)}
.manage-item{display:flex;align-items:center;justify-content:space-between;padding:12px 18px;background:rgba(20,0,0,.6);border:1px solid rgba(255,0,0,.3);border-radius:10px;margin-bottom:10px;gap:12px;flex-wrap:wrap;transition:all .3s}
.manage-item:hover{border-color:rgba(255,0,0,.7);background:rgba(40,0,0,.7)}
.manage-info{display:flex;align-items:center;gap:15px;flex:1;min-width:0}
.manage-info .mi-icon{font-size:24px;flex-shrink:0;filter:drop-shadow(0 0 8px #f00)}
.manage-info .mi-text{min-width:0;flex:1}
.manage-info .mi-text h5{color:#f66;font-size:14px;margin-bottom:2px;word-break:break-all;font-weight:600}
.manage-info .mi-text small{color:#a55;font-size:11px}
.manage-actions{display:flex;gap:8px;flex-wrap:wrap}
.thumb-preview{width:80px;height:50px;object-fit:cover;border-radius:6px;border:2px solid #f00;box-shadow:0 0 15px rgba(255,0,0,.4)}
.empty-manage{text-align:center;padding:30px;color:#a55;font-size:13px}
.warning-box{background:rgba(255,0,0,.15);border:2px solid #f00;border-radius:10px;padding:15px;margin-bottom:20px;color:#f66;font-weight:600}
@media(max-width:768px){.navbar{flex-direction:column}.grid{grid-template-columns:1fr}.file-item{flex-direction:column;text-align:center}.slot-row{flex-direction:column;align-items:stretch}.slot-num{align-self:center}.manage-item{flex-direction:column}.manage-actions{width:100%}.manage-actions .btn{flex:1}}
</style>"""

BACKGROUND_HTML = """
{% if bg_video %}<video id="bg-video" autoplay muted loop playsinline preload="auto"><source src="/bg-stream" type="video/mp4"></video>{% endif %}
<div id="bg-overlay"></div><div id="bg-grid"></div><div id="particles"></div>
<script>(function(){const c=document.getElementById('particles');if(!c)return;
for(let i=0;i<14;i++){const h=document.createElement('div');h.className='hacker';
h.style.transform='scale('+(0.55+Math.random()*0.75)+')';h.style.left=Math.random()*100+'%';
h.style.animationDuration=(14+Math.random()*16)+'s';h.style.animationDelay=(-Math.random()*25)+'s';
h.innerHTML='<div class="hood"></div><div class="face"></div><div class="eye left"></div><div class="eye right"></div><div class="body"></div>';c.appendChild(h);}
for(let i=0;i<25;i++){const o=document.createElement('div');o.className='orb';const s=4+Math.random()*10;
o.style.width=s+'px';o.style.height=s+'px';o.style.left=Math.random()*100+'%';o.style.top=(100+Math.random()*20)+'%';
o.style.animationDuration=(8+Math.random()*12)+'s';o.style.animationDelay=(-Math.random()*15)+'s';c.appendChild(o);}
for(let i=0;i<30;i++){const b=document.createElement('div');b.className='bin';b.textContent=Math.random()>0.5?'1':'0';
b.style.left=Math.random()*100+'%';b.style.top=(-20-Math.random()*30)+'%';
b.style.animationDuration=(6+Math.random()*10)+'s';b.style.animationDelay=(-Math.random()*20)+'s';c.appendChild(b);}})();
(function(){const n=document.getElementById('animated-name');if(!n)return;const t=n.dataset.name||'SHUVOM';
let i=0;n.textContent='';const timer=setInterval(()=>{if(i<t.length){n.textContent+=t[i];i++;}else clearInterval(timer);},220);})();
</script>"""

# ==================== TEMPLATES ====================
HOME_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>🔴 FILE STORE</title>""" + BASE_CSS + """</head><body>""" + BACKGROUND_HTML + """
<div class="container"><div class="navbar"><div class="logo">🔴 FILE<span>STORE</span></div>
<div class="nav-links"><a href="/">🏠 Home</a><a href="/admin">🔐 Admin</a></div></div>
<div class="hero"><h1 class="name-reveal" id="animated-name" data-name="{{ owner_name }}">{{ owner_name }}</h1>
<p style="font-size:20px;letter-spacing:8px;color:#f33;margin-top:10px;">FILE STORE</p>
<p style="margin-top:15px;">✦ PREMIUM VIDEO & FILE VAULT ✦</p></div>
{% if items %}<div class="grid">{% for item in items %}<div class="card">
{% if item.thumbnail %}<div class="card-thumb"><img src="/thumb/{{ item.id }}" alt="{{ item.title }}"></div>
{% else %}<div class="card-icon">🎬</div>{% endif %}
<h3>{{ item.title }}</h3>
<p>{{ item.description[:100] if item.description else 'Watch free — Download needs password' }}{% if item.description and item.description|length>100 %}...{% endif %}</p>
<div class="card-meta"><span>👁️ {{ item.views }}</span><span>🎬 {{ item.videos }}</span><span>📎 {{ item.attachments }}</span></div>
<div style="margin-top:15px;"><a href="/watch/{{ item.id }}" class="btn btn-block">▶️ Watch Now</a></div>
</div>{% endfor %}</div>{% else %}
<div class="empty-state"><div class="icon">📭</div><h3>No Content Yet</h3></div>{% endif %}
<div class="footer">🔴 FILE STORE 🔴<br>👑 {{ owner_name }} - TEAM X</div></div></body></html>"""

WATCH_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{{ item.title }}</title>""" + BASE_CSS + """</head><body>""" + BACKGROUND_HTML + """
<div class="container"><div class="navbar"><div class="logo">🔴 FILE<span>STORE</span></div>
<div class="nav-links"><a href="/">🏠 Home</a><a href="/admin">🔐 Admin</a></div></div>
{% if item.thumbnail %}<div class="hero-thumb"><img src="/thumb/{{ item.id }}" alt="{{ item.title }}"></div>{% endif %}
<div class="hero"><h1 style="font-size:28px;">{{ item.title }}</h1><p>{{ item.description or 'Free to watch — Password required to download' }}</p></div>
<div style="display:flex;gap:15px;flex-wrap:wrap;justify-content:center;margin:0 0 25px 0;">
<span class="badge">👁️ {{ item.views }} views</span>
<span class="badge">📅 {{ item.created_at[:10] }}</span>
<span class="badge">🎬 {{ videos|length }} videos</span>
<span class="badge">📎 {{ attachments|length }} files</span>
{% if unlocked %}<span class="badge badge-unlock">🔓 UNLOCKED</span>
{% else %}<span class="badge badge-lock">🔒 Download Locked</span>{% endif %}
</div>

{% if videos %}
{% if videos|length > 1 %}
<div class="video-tabs">{% for v in videos %}
<button class="video-tab {% if loop.first %}active{% endif %}" data-vid="{{ v.id }}" data-vname="{{ v.original_name }}" onclick="playVideo(this)">
🎬 {{ loop.index }}. {{ v.original_name[:30] }}{% if v.original_name|length > 30 %}...{% endif %}</button>{% endfor %}</div>
{% endif %}
<div class="video-container"><video id="mainVideo" controls autoplay playsinline preload="metadata">
<source id="videoSource" src="/stream-video/{{ videos[0].id }}" type="video/mp4"></video></div>
<div style="text-align:center;margin-bottom:20px;"><span class="badge" id="currentVidName">🎬 Now Playing: {{ videos[0].original_name }}</span></div>
<script>function playVideo(btn){const src=document.getElementById('videoSource');const vid=document.getElementById('mainVideo');
src.src='/stream-video/'+btn.dataset.vid;vid.load();vid.play().catch(()=>{});
document.getElementById('currentVidName').textContent='🎬 Now Playing: '+btn.dataset.vname;
document.querySelectorAll('.video-tab').forEach(b=>b.classList.remove('active'));btn.classList.add('active');}</script>
{% else %}<div class="empty-state"><div class="icon">🎬</div><h3>No Videos</h3></div>{% endif %}

{% if attachments %}
<div class="hero" style="padding:25px;">
<h2 style="font-family:'Orbitron';color:#f33;margin-bottom:20px;">📎 ATTACHED FILES ({{ attachments|length }})</h2>
{% if not unlocked %}
<div class="unlock-banner">
<p>🔒 ডাউনলোড করতে পাসওয়ার্ড দাও (ভিডিও ফ্রি দেখতে পারবে)</p>
{% if error %}<div class="alert alert-error" style="margin-bottom:15px;">❌ {{ error }}</div>{% endif %}
<form method="POST" style="max-width:400px;margin:0 auto;"><div class="input-group">
<input type="password" name="password" placeholder="● ● ● ● ● ●" required>
<button type="submit" class="btn">🔓 UNLOCK</button></div></form></div>
{% else %}
<div style="text-align:center;margin-bottom:15px;"><span class="badge badge-unlock">✅ Unlocked — Download Available</span></div>
{% endif %}
<div class="file-list">{% for f in attachments %}<div class="file-item"><div class="file-info">
<div class="file-icon">{% if f.file_type in ['zip','rar','7z'] %}🗜️{% elif f.file_type in ['png','jpg','jpeg','gif'] %}🖼️{% elif f.file_type=='pdf' %}📕{% elif f.file_type=='apk' %}📱{% elif f.file_type in ['mp3','wav'] %}🎵{% else %}📄{% endif %}</div>
<div class="file-details"><h4>{{ f.original_name }}</h4><small>{{ f.size_display }} • {{ f.downloads }} downloads</small></div></div>
{% if unlocked %}<a href="/download/{{ f.id }}" class="btn">⬇️ Download</a>
{% else %}<button class="btn btn-locked" onclick="scrollToPassword()">🔒 Locked</button>{% endif %}
</div>{% endfor %}</div></div>
<script>function scrollToPassword(){const el=document.querySelector('.unlock-banner');
if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.querySelector('input').focus();}
else{alert('পাসওয়ার্ড দাও ডাউনলোড আনলক করতে');}}</script>
{% endif %}
<div class="footer">🔴 FILE STORE 🔴<br>👑 {{ owner_name }} - TEAM X</div></div></body></html>"""

LOGIN_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Login</title>""" + BASE_CSS + """</head><body>""" + BACKGROUND_HTML + """
<div class="container"><div class="hero" style="margin-top:60px;">
<h1 class="name-reveal" id="animated-name" data-name="ADMIN">{{ owner_name }}</h1>
<p style="margin-top:10px;">🔐 ADMIN LOGIN 🔐</p></div>
<div class="lock-screen">{% if error %}<div class="alert alert-error">❌ {{ error }}</div>{% endif %}
<form method="POST"><div class="form-group"><label>👤 USERNAME</label>
<input type="text" name="username" placeholder="Username" required autofocus></div>
<div class="form-group"><label>🔑 PASSWORD</label>
<input type="password" name="password" placeholder="Password" required></div>
<button type="submit" class="btn btn-block">🔓 LOGIN</button></form></div>
<div class="footer">🔴 FILE STORE 🔴<br>👑 {{ owner_name }}</div></div></body></html>"""

ADMIN_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Admin</title>""" + BASE_CSS + """</head><body>""" + BACKGROUND_HTML + """
<div class="container"><div class="navbar"><div class="logo">🔴 ADMIN<span>PANEL</span></div>
<div class="nav-links"><a href="/">🏠 Home</a><a href="/admin/upload">📤 Upload</a>
<a href="/admin/bg">🎞️ BG</a><a href="/admin/logout">🚪 Logout</a></div></div>
{% with messages = get_flashed_messages(with_categories=true) %}
{% for cat, msg in messages %}<div class="alert alert-{{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}
<div class="hero"><h1 class="name-reveal" id="animated-name" data-name="{{ owner_name }}">{{ owner_name }}</h1>
<p style="margin-top:10px;">📊 DASHBOARD 📊</p></div>
<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr));">
<div class="card" style="text-align:center;"><div class="card-icon">🎬</div><h3>{{ total_videos }}</h3><p>Videos</p></div>
<div class="card" style="text-align:center;"><div class="card-icon">📎</div><h3>{{ total_files }}</h3><p>Files</p></div>
<div class="card" style="text-align:center;"><div class="card-icon">👁️</div><h3>{{ total_views }}</h3><p>Views</p></div>
<div class="card" style="text-align:center;"><div class="card-icon">💾</div><h3>{{ total_size }}</h3><p>Storage</p></div></div>
<div style="margin:25px 0;text-align:center;">
<a href="/admin/upload" class="btn" style="font-size:16px;padding:16px 40px;">📤 UPLOAD NEW</a>
<a href="/admin/bg" class="btn btn-ghost" style="font-size:16px;padding:16px 40px;margin-left:10px;">🎞️ BG</a></div>
<div class="hero" style="padding:25px;"><h2 style="font-family:'Orbitron';color:#f33;margin-bottom:20px;">🎬 ALL CONTENT</h2>
{% if items %}<div class="table-wrap"><table><thead><tr>
<th>ID</th><th>Thumb</th><th>Title</th><th>Videos</th><th>Files</th><th>Views</th><th>Size</th><th>Date</th><th>Actions</th>
</tr></thead><tbody>{% for item in items %}<tr>
<td><span class="badge">#{{ item.id }}</span></td>
<td>{% if item.thumbnail %}<img src="/thumb/{{ item.id }}" style="width:60px;height:40px;object-fit:cover;border-radius:5px;border:1px solid #f00;">{% else %}🎬{% endif %}</td>
<td>{{ item.title }}</td>
<td>🎬 {{ item.videos }}</td><td>📎 {{ item.attachments }}</td><td>{{ item.views }}</td>
<td>{{ item.size_display }}</td><td>{{ item.created_at[:10] }}</td>
<td>
<a href="/watch/{{ item.id }}" class="btn btn-ghost btn-sm">👁️ View</a>
<a href="/admin/manage/{{ item.id }}" class="btn btn-ghost btn-sm" style="background:rgba(255,150,0,.2);border-color:#fa0;color:#fc6;">⚙️ Manage</a>
<a href="/admin/delete/{{ item.id }}" class="btn btn-danger btn-sm" onclick="return confirm('আসলেই পুরো content মুছতে চাও?')">🗑️ Delete All</a>
</td></tr>{% endfor %}</tbody></table></div>
{% else %}<div class="empty-state"><div class="icon">📭</div><h3>No Content</h3></div>{% endif %}</div>
<div class="footer">🔴 FILE STORE 🔴<br>👑 {{ owner_name }}</div></div></body></html>"""

MANAGE_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Manage - {{ item.title }}</title>""" + BASE_CSS + """</head><body>""" + BACKGROUND_HTML + """
<div class="container"><div class="navbar"><div class="logo">⚙️ MANAGE<span>CONTENT</span></div>
<div class="nav-links"><a href="/">🏠 Home</a><a href="/admin">📊 Dashboard</a>
<a href="/admin/upload">📤 Upload</a><a href="/admin/logout">🚪 Logout</a></div></div>
{% with messages = get_flashed_messages(with_categories=true) %}
{% for cat, msg in messages %}<div class="alert alert-{{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}
<div class="hero"><h1 style="font-size:24px;">{{ item.title }}</h1>
<p style="font-size:14px;">Content ID #{{ item.id }} — Manage individual items</p></div>
<div class="warning-box">⚠️ নিচের যেকোনো item মুছলে সেটা permanently চলে যাবে — ব্যাকআপ রাখো!</div>

<div class="manage-section">
<h2>🖼️ THUMBNAIL</h2>
{% if item.thumbnail %}
<div class="manage-item">
<div class="manage-info"><img src="/thumb/{{ item.id }}" class="thumb-preview" alt="Thumbnail">
<div class="mi-text"><h5>Current Thumbnail</h5><small>{{ item.thumbnail }}</small></div></div>
<div class="manage-actions"><a href="/admin/delete-thumb/{{ item.id }}" class="btn btn-danger" onclick="return confirm('থাম্বনেইল মুছতে চাও?')">🗑️ Delete Thumbnail</a></div>
</div>
{% else %}<div class="empty-manage">📭 কোনো থাম্বনেইল নেই</div>{% endif %}
</div>

<div class="manage-section">
<h2>🎬 VIDEOS ({{ videos|length }})</h2>
{% if videos %}{% for v in videos %}
<div class="manage-item">
<div class="manage-info"><div class="mi-icon">🎬</div>
<div class="mi-text"><h5>{{ loop.index }}. {{ v.original_name }}</h5>
<small>{{ v.size_display }} • {{ v.created_at[:19] }}</small></div></div>
<div class="manage-actions">
<a href="/watch/{{ item.id }}" class="btn btn-ghost btn-sm">▶️ Play</a>
<a href="/admin/delete-video/{{ v.id }}" class="btn btn-danger btn-sm" onclick="return confirm('এই ভিডিওটা মুছতে চাও?')">🗑️ Delete</a>
</div></div>
{% endfor %}{% else %}<div class="empty-manage">📭 কোনো ভিডিও নেই</div>{% endif %}
</div>

<div class="manage-section">
<h2>📎 FILES ({{ attachments|length }})</h2>
{% if attachments %}{% for f in attachments %}
<div class="manage-item">
<div class="manage-info"><div class="mi-icon">
{% if f.file_type in ['zip','rar','7z'] %}🗜️{% elif f.file_type in ['png','jpg','jpeg','gif'] %}🖼️{% elif f.file_type == 'pdf' %}📕{% elif f.file_type == 'apk' %}📱{% elif f.file_type in ['mp3','wav'] %}🎵{% else %}📄{% endif %}
</div>
<div class="mi-text"><h5>{{ loop.index }}. {{ f.original_name }}</h5>
<small>{{ f.size_display }} • {{ f.downloads }} downloads</small></div></div>
<div class="manage-actions">
<a href="/download/{{ f.id }}" class="btn btn-ghost btn-sm">⬇️ Download</a>
<a href="/admin/delete-file/{{ f.id }}" class="btn btn-danger btn-sm" onclick="return confirm('এই ফাইলটা মুছতে চাও?')">🗑️ Delete</a>
</div></div>
{% endfor %}{% else %}<div class="empty-manage">📭 কোনো ফাইল নেই</div>{% endif %}
</div>

<div class="manage-section" style="border-color:#f00;background:linear-gradient(135deg,rgba(60,0,0,.95),rgba(30,0,0,.9));">
<h2 style="color:#f00;">☠️ DANGER ZONE</h2>
<p style="color:#f99;margin-bottom:20px;">পুরো content (সব ভিডিও + ফাইল + থাম্বনেইল) একসাথে মুছে ফেলবে।</p>
<a href="/admin/delete/{{ item.id }}" class="btn btn-danger" style="font-size:16px;padding:16px 40px;"
onclick="return confirm('সবকিছু মুছতে চাও? এটা undo হবে না!')">🗑️ DELETE ENTIRE CONTENT</a>
</div>

<div style="text-align:center;margin:30px 0;">
<a href="/admin" class="btn btn-ghost" style="font-size:15px;padding:14px 30px;">← Back to Dashboard</a>
</div>
<div class="footer">🔴 FILE STORE 🔴<br>👑 {{ owner_name }} - TEAM X</div></div></body></html>"""

UPLOAD_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Upload</title>""" + BASE_CSS + """</head><body>""" + BACKGROUND_HTML + """
<div class="container"><div class="navbar"><div class="logo">🔴 UPLOAD<span>CONTENT</span></div>
<div class="nav-links"><a href="/">🏠 Home</a><a href="/admin">📊 Dashboard</a>
<a href="/admin/bg">🎞️ BG</a><a href="/admin/logout">🚪 Logout</a></div></div>
{% with messages = get_flashed_messages(with_categories=true) %}
{% for cat, msg in messages %}<div class="alert alert-{{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}
<div class="hero"><h1 class="name-reveal" id="animated-name" data-name="UPLOAD">{{ owner_name }}</h1>
<p style="margin-top:10px;">📤 যত খুশি ভিডিও + ফাইল আপলোড করো 📤</p></div>
<form method="POST" enctype="multipart/form-data" id="uploadForm" style="max-width:900px;margin:0 auto;">
<div class="hero" style="padding:30px;text-align:left;">
<h2 style="font-family:'Orbitron';color:#f33;margin-bottom:20px;">📝 BASIC INFO</h2>
<div class="form-group"><label>📌 TITLE</label>
<input type="text" name="title" placeholder="Enter title" required></div>
<div class="form-group"><label>📝 DESCRIPTION</label>
<textarea name="description" placeholder="Description"></textarea></div>
<div class="form-group"><label>🔐 DOWNLOAD PASSWORD (ভিডিও ফ্রি, ফাইল ডাউনলোডে পাসওয়ার্ড লাগবে)</label>
<input type="text" name="password" placeholder="Download password" required></div></div>

<div class="hero" style="padding:30px;text-align:left;margin-top:25px;">
<h2 style="font-family:'Orbitron';color:#f33;margin-bottom:15px;">🖼️ THUMBNAIL IMAGE (optional)</h2>
<div class="hint">📱 একটা ছবি দাও — হোম পেজে কার্ডে দেখাবে। না দিলে 🎬 emoji দেখাবে।</div>
<div class="upload-zone" onclick="document.getElementById('thumbInput').click()">
<div class="icon">🖼️</div>
<p id="thumbLabel">Click to select thumbnail image</p>
<small>PNG / JPG / JPEG / WEBP / GIF</small></div>
<input type="file" id="thumbInput" name="thumbnail" accept="image/*" style="display:none"
onchange="document.getElementById('thumbLabel').innerText='✅ '+this.files[0].name">
</div>

<div class="hero" style="padding:30px;text-align:left;margin-top:25px;">
<h2 style="font-family:'Orbitron';color:#f33;margin-bottom:15px;">🎬 VIDEO FILES</h2>
<div class="hint">📱 যত খুশি ভিডিও — ➕ ADD MORE VIDEO</div>
<div id="videoSlots"><div class="slot-row"><span class="slot-num">1</span>
<input type="file" name="videos" accept="video/*"></div></div>
<button type="button" class="add-btn" onclick="addVideoSlot()">➕ ADD MORE VIDEO</button></div>

<div class="hero" style="padding:30px;text-align:left;margin-top:25px;">
<h2 style="font-family:'Orbitron';color:#f33;margin-bottom:15px;">📎 ATTACHED FILES</h2>
<div class="hint">📱 যত খুশি ফাইল — ➕ ADD MORE FILE</div>
<div id="fileSlots"><div class="slot-row"><span class="slot-num">1</span>
<input type="file" name="files"></div></div>
<button type="button" class="add-btn" onclick="addFileSlot()">➕ ADD MORE FILE</button></div>

<div style="text-align:center;margin-top:30px;">
<button type="submit" class="btn" style="font-size:18px;padding:20px 60px;" id="submitBtn">🚀 UPLOAD ALL</button></div>
</form>

<script>
var videoCount = 1, fileCount = 1;
function addVideoSlot() {
    videoCount++;
    var slots = document.getElementById('videoSlots');
    var row = document.createElement('div'); row.className = 'slot-row';
    row.innerHTML = '<span class="slot-num">' + videoCount + '</span>' +
        '<input type="file" name="videos" accept="video/*">' +
        '<button type="button" class="remove-btn" onclick="this.parentElement.remove()">✖</button>';
    slots.appendChild(row);
}
function addFileSlot() {
    fileCount++;
    var slots = document.getElementById('fileSlots');
    var row = document.createElement('div'); row.className = 'slot-row';
    row.innerHTML = '<span class="slot-num">' + fileCount + '</span>' +
        '<input type="file" name="files">' +
        '<button type="button" class="remove-btn" onclick="this.parentElement.remove()">✖</button>';
    slots.appendChild(row);
}
document.getElementById('uploadForm').addEventListener('submit', function(e) {
    var any = false;
    document.querySelectorAll('input[type="file"]').forEach(function(inp) {
        if (!inp.files || inp.files.length === 0) { inp.disabled = true; }
        else { any = true; }
    });
    if (!any) { e.preventDefault(); alert('❌ অন্তত ১টা ভিডিও বা ১টা ফাইল দিতে হবে!'); return false; }
    var btn = document.getElementById('submitBtn');
    btn.disabled = true; btn.textContent = '⏳ Uploading...';
});
</script>

<div class="footer">🔴 FILE STORE 🔴<br>👑 {{ owner_name }} - TEAM X</div></div></body></html>"""

BG_VIDEO_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>BG Video</title>""" + BASE_CSS + """</head><body>""" + BACKGROUND_HTML + """
<div class="container"><div class="navbar"><div class="logo">🔴 BG<span>VIDEO</span></div>
<div class="nav-links"><a href="/">🏠 Home</a><a href="/admin">📊 Dashboard</a>
<a href="/admin/upload">📤 Upload</a><a href="/admin/logout">🚪 Logout</a></div></div>
{% with messages = get_flashed_messages(with_categories=true) %}
{% for cat, msg in messages %}<div class="alert alert-{{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}
<div class="hero"><h1 class="name-reveal" id="animated-name" data-name="BACKGROUND">{{ owner_name }}</h1>
<p style="margin-top:10px;">🎞️ BACKGROUND VIDEO MANAGER 🎞️</p></div>
<div class="lock-screen" style="max-width:700px;">
{% if bg_video %}<p style="margin-bottom:20px;color:#6f6;font-weight:700;">✅ Active</p>
<div style="margin-bottom:25px;border-radius:12px;overflow:hidden;border:2px solid #f00;">
<video controls muted style="width:100%;display:block;" src="/bg-stream"></video></div>
<form method="POST" action="/admin/bg/delete" style="display:inline;">
<button type="submit" class="btn btn-danger" onclick="return confirm('BG ভিডিও মুছতে চাও?')">🗑️ REMOVE BG VIDEO</button></form>
{% else %}<p style="margin-bottom:25px;color:#fc6;">ℹ️ No background video set.</p>{% endif %}
<form method="POST" enctype="multipart/form-data" style="margin-top:25px;">
<div style="border:2px dashed rgba(255,0,0,.6);border-radius:15px;padding:30px;text-align:center;background:rgba(255,0,0,.04);cursor:pointer;" onclick="document.getElementById('bgInput').click()">
<div style="font-size:40px;margin-bottom:10px;">🎞️</div>
<p id="bgLabel" style="color:#f99;">Click to upload BG video</p></div>
<input type="file" id="bgInput" name="bgvideo" accept="video/*" required style="display:none"
onchange="document.getElementById('bgLabel').innerText='✅ '+this.files[0].name">
<button type="submit" class="btn btn-block" style="margin-top:20px;">⬆️ UPLOAD</button></form></div>
<div class="footer">🔴 FILE STORE 🔴<br>👑 {{ owner_name }}</div></div></body></html>"""

# ==================== ROUTES ====================
@app.route('/')
def home():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT i.*,
        (SELECT COUNT(*) FROM attachments WHERE item_id=i.id) as attachments,
        (SELECT COUNT(*) FROM videos WHERE item_id=i.id) as videos
        FROM items i ORDER BY i.created_at DESC""")
    items = [dict(r) for r in c.fetchall()]; conn.close()
    return render_template_string(HOME_TEMPLATE, items=items, owner_name=OWNER_NAME, bg_video=get_bg_video())

@app.route('/thumb/<int:item_id>')
def thumb(item_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT thumbnail FROM items WHERE id=?", (item_id,))
    row = c.fetchone(); conn.close()
    if not row or not row['thumbnail']: abort(404)
    return send_from_directory(os.path.join(UPLOAD_DIR, "thumbnails"), row['thumbnail'])

@app.route('/watch/<int:item_id>', methods=['GET', 'POST'])
def watch(item_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    if not row: conn.close(); abort(404)
    item = dict(row)
    unlocked = session.get(f'unlocked_{item_id}') is True
    error = None
    if request.method == 'POST':
        pw = request.form.get('password', '').strip()
        if hash_password(pw) == item['password_hash']:
            session[f'unlocked_{item_id}'] = True; unlocked = True
            c.execute("UPDATE items SET views = views + 1 WHERE id=?", (item_id,))
            c.execute("INSERT INTO unlock_log (item_id, ip) VALUES (?,?)", (item_id, request.remote_addr or ''))
            conn.commit()
            c.execute("SELECT views FROM items WHERE id=?", (item_id,))
            item['views'] = c.fetchone()['views']
            flash("✅ Unlocked!", "success")
        else:
            error = "Wrong password! Try again."
    videos = []
    c.execute("SELECT * FROM videos WHERE item_id=? ORDER BY sort_order, id", (item_id,))
    for v in c.fetchall():
        vd = dict(v); vd['size_display'] = format_size(vd['file_size']); videos.append(vd)
    attachments = []
    c.execute("SELECT * FROM attachments WHERE item_id=? ORDER BY id", (item_id,))
    for a in c.fetchall():
        ad = dict(a); ad['size_display'] = format_size(ad['file_size']); attachments.append(ad)
    conn.close()
    return render_template_string(WATCH_TEMPLATE, item=item, unlocked=unlocked,
        error=error, attachments=attachments, videos=videos,
        owner_name=OWNER_NAME, bg_video=get_bg_video())

@app.route('/stream-video/<int:video_id>')
def stream_video(video_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM videos WHERE id=?", (video_id,))
    row = c.fetchone(); conn.close()
    if not row: abort(404)
    vid = dict(row)
    return send_from_directory(os.path.join(UPLOAD_DIR, "videos"), vid['filename'])

@app.route('/stream/<int:item_id>')
def stream(item_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM videos WHERE item_id=? ORDER BY sort_order, id LIMIT 1", (item_id,))
    row = c.fetchone(); conn.close()
    if not row: abort(404)
    return redirect(url_for('stream_video', video_id=row['id']))

@app.route('/download/<int:file_id>')
def download(file_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM attachments WHERE id=?", (file_id,))
    row = c.fetchone()
    if not row: conn.close(); abort(404)
    att = dict(row)
    if not session.get(f'unlocked_{att["item_id"]}'):
        conn.close()
        flash("🔒 ডাউনলোড করতে পাসওয়ার্ড দাও!", "info")
        return redirect(url_for('watch', item_id=att['item_id']))
    c.execute("UPDATE attachments SET downloads=downloads+1 WHERE id=?", (file_id,))
    conn.commit(); conn.close()
    return send_from_directory(os.path.join(UPLOAD_DIR, "files"), att['filename'],
                               as_attachment=True, download_name=att['original_name'])

@app.route('/bg-stream')
def bg_stream():
    fname = get_bg_video()
    if not fname: abort(404)
    return send_from_directory(os.path.join(UPLOAD_DIR, "bg"), fname)

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT i.*,
        (SELECT COUNT(*) FROM attachments WHERE item_id=i.id) as attachments,
        (SELECT COUNT(*) FROM videos WHERE item_id=i.id) as videos
        FROM items i ORDER BY i.created_at DESC""")
    items, total_size, total_views = [], 0, 0
    for row in c.fetchall():
        d = dict(row)
        c2 = c.execute("SELECT COALESCE(SUM(file_size),0) AS s FROM videos WHERE item_id=?", (d['id'],)).fetchone()
        c3 = c.execute("SELECT COALESCE(SUM(file_size),0) AS s FROM attachments WHERE item_id=?", (d['id'],)).fetchone()
        item_size = (c2['s'] or 0) + (c3['s'] or 0)
        d['size_display'] = format_size(item_size)
        total_size += item_size; total_views += d['views']
        items.append(d)
    c.execute("SELECT COUNT(*) FROM attachments"); total_files = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM videos"); total_videos = c.fetchone()[0]
    conn.close()
    return render_template_string(ADMIN_TEMPLATE, items=items,
        total_files=total_files, total_videos=total_videos, total_views=total_views,
        total_size=format_size(total_size), owner_name=OWNER_NAME, bg_video=get_bg_video())

@app.route('/admin/manage/<int:item_id>')
@admin_required
def admin_manage(item_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    if not row: conn.close(); flash("❌ Not found!", "error"); return redirect(url_for('admin_dashboard'))
    item = dict(row)
    videos = []
    c.execute("SELECT * FROM videos WHERE item_id=? ORDER BY sort_order, id", (item_id,))
    for v in c.fetchall():
        vd = dict(v); vd['size_display'] = format_size(vd['file_size']); videos.append(vd)
    attachments = []
    c.execute("SELECT * FROM attachments WHERE item_id=? ORDER BY id", (item_id,))
    for a in c.fetchall():
        ad = dict(a); ad['size_display'] = format_size(ad['file_size']); attachments.append(ad)
    conn.close()
    return render_template_string(MANAGE_TEMPLATE, item=item,
        videos=videos, attachments=attachments,
        owner_name=OWNER_NAME, bg_video=get_bg_video())

@app.route('/admin/delete-thumb/<int:item_id>')
@admin_required
def admin_delete_thumb(item_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT thumbnail FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    if row and row['thumbnail']:
        try: os.remove(os.path.join(UPLOAD_DIR, "thumbnails", row['thumbnail']))
        except: pass
        c.execute("UPDATE items SET thumbnail='' WHERE id=?", (item_id,))
        conn.commit()
        flash("🗑️ Thumbnail deleted.", "success")
    else:
        flash("❌ No thumbnail found.", "error")
    conn.close()
    return redirect(url_for('admin_manage', item_id=item_id))

@app.route('/admin/delete-video/<int:video_id>')
@admin_required
def admin_delete_video(video_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM videos WHERE id=?", (video_id,))
    row = c.fetchone()
    if not row:
        conn.close(); flash("❌ Video not found.", "error")
        return redirect(url_for('admin_dashboard'))
    item_id = row['item_id']
    try: os.remove(os.path.join(UPLOAD_DIR, "videos", row['filename']))
    except: pass
    c.execute("DELETE FROM videos WHERE id=?", (video_id,))
    conn.commit(); conn.close()
    flash(f"🗑️ Video deleted: {row['original_name']}", "success")
    return redirect(url_for('admin_manage', item_id=item_id))

@app.route('/admin/delete-file/<int:file_id>')
@admin_required
def admin_delete_file(file_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM attachments WHERE id=?", (file_id,))
    row = c.fetchone()
    if not row:
        conn.close(); flash("❌ File not found.", "error")
        return redirect(url_for('admin_dashboard'))
    item_id = row['item_id']
    try: os.remove(os.path.join(UPLOAD_DIR, "files", row['filename']))
    except: pass
    c.execute("DELETE FROM attachments WHERE id=?", (file_id,))
    conn.commit(); conn.close()
    flash(f"🗑️ File deleted: {row['original_name']}", "success")
    return redirect(url_for('admin_manage', item_id=item_id))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if is_admin(): return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '').strip()
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash("✅ Welcome!", "success")
            return redirect(url_for('admin_dashboard'))
        error = "Invalid credentials!"
    return render_template_string(LOGIN_TEMPLATE, error=error, owner_name=OWNER_NAME, bg_video=get_bg_video())

@app.route('/admin/logout')
def admin_logout():
    session.clear(); flash("👋 Logged out.", "info")
    return redirect(url_for('home'))

@app.route('/admin/upload', methods=['GET', 'POST'])
@admin_required
def admin_upload():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        password = request.form.get('password', '').strip()
        if not title or not password:
            flash("❌ Title and password are required!", "error")
            return redirect(url_for('admin_upload'))
        video_files = request.files.getlist('videos')
        valid_videos = [f for f in video_files if f and f.filename]
        file_files = request.files.getlist('files')
        valid_files = [f for f in file_files if f and f.filename]
        if not valid_videos and not valid_files:
            flash("❌ অন্তত ১টা ভিডিও বা ১টা ফাইল দিতে হবে!", "error")
            return redirect(url_for('admin_upload'))

        conn = get_db(); c = conn.cursor()
        c.execute("""INSERT INTO items (title, description, video_filename, video_original,
                     video_size, password_hash) VALUES (?, ?, '', '', 0, ?)""",
                  (title, description, hash_password(password)))
        item_id = c.lastrowid

        thumb_file = request.files.get('thumbnail')
        if thumb_file and thumb_file.filename:
            t_orig = secure_filename(thumb_file.filename)
            t_ext = get_ext(t_orig)
            if t_ext in ALLOWED_IMG_EXT:
                thumb_name = f"thumb_{item_id}_{secrets.token_hex(6)}_{t_orig}"
                thumb_file.save(os.path.join(UPLOAD_DIR, "thumbnails", thumb_name))
                c.execute("UPDATE items SET thumbnail=? WHERE id=?", (thumb_name, item_id))
            else:
                flash(f"⚠️ Thumbnail format not allowed: {t_ext}", "info")

        saved_vids = 0; fv_name = fv_orig = ''; fv_size = 0
        for idx, vf in enumerate(valid_videos):
            v_orig = secure_filename(vf.filename)
            v_ext = get_ext(v_orig)
            if v_ext not in ALLOWED_VIDEO_EXT: continue
            v_name = f"{item_id}_{int(datetime.now().timestamp())}_{secrets.token_hex(6)}_{v_orig}"
            v_path = os.path.join(UPLOAD_DIR, "videos", v_name)
            vf.save(v_path)
            v_size = get_file_size(v_path)
            c.execute("""INSERT INTO videos (item_id, filename, original_name, file_size, file_type, sort_order)
                         VALUES (?,?,?,?,?,?)""", (item_id, v_name, v_orig, v_size, v_ext, idx))
            if idx == 0: fv_name, fv_orig, fv_size = v_name, v_orig, v_size
            saved_vids += 1

        if fv_name:
            c.execute("UPDATE items SET video_filename=?, video_original=?, video_size=? WHERE id=?",
                      (fv_name, fv_orig, fv_size, item_id))

        saved = 0
        for f in valid_files:
            orig = secure_filename(f.filename)
            ext = get_ext(orig)
            if ext not in ALLOWED_FILE_EXT: continue
            fname = f"{item_id}_{secrets.token_hex(6)}_{orig}"
            fpath = os.path.join(UPLOAD_DIR, "files", fname)
            f.save(fpath)
            fsize = get_file_size(fpath)
            c.execute("INSERT INTO attachments (item_id, filename, original_name, file_size, file_type) VALUES (?,?,?,?,?)",
                      (item_id, fname, orig, fsize, ext))
            saved += 1

        conn.commit(); conn.close()
        flash(f"✅ '{title}' — {saved_vids} video(s) + {saved} file(s)!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template_string(UPLOAD_TEMPLATE, owner_name=OWNER_NAME, bg_video=get_bg_video())

@app.route('/admin/delete/<int:item_id>')
@admin_required
def admin_delete(item_id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM items WHERE id=?", (item_id,))
    row = c.fetchone()
    if not row:
        conn.close(); flash("❌ Not found!", "error")
        return redirect(url_for('admin_dashboard'))
    if row['thumbnail']:
        try: os.remove(os.path.join(UPLOAD_DIR, "thumbnails", row['thumbnail']))
        except: pass
    c.execute("SELECT filename FROM videos WHERE item_id=?", (item_id,))
    for r in c.fetchall():
        try: os.remove(os.path.join(UPLOAD_DIR, "videos", r['filename']))
        except: pass
    c.execute("SELECT filename FROM attachments WHERE item_id=?", (item_id,))
    for r in c.fetchall():
        try: os.remove(os.path.join(UPLOAD_DIR, "files", r['filename']))
        except: pass
    c.execute("DELETE FROM videos WHERE item_id=?", (item_id,))
    c.execute("DELETE FROM attachments WHERE item_id=?", (item_id,))
    c.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit(); conn.close()
    flash(f"🗑️ Deleted entire content: {row['title']}", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bg', methods=['GET', 'POST'])
@admin_required
def admin_bg():
    if request.method == 'POST':
        f = request.files.get('bgvideo')
        if not f or not f.filename:
            flash("❌ No file!", "error"); return redirect(url_for('admin_bg'))
        orig = secure_filename(f.filename)
        ext = get_ext(orig)
        if ext not in ALLOWED_VIDEO_EXT:
            flash(f"❌ Format not allowed: {ext}", "error"); return redirect(url_for('admin_bg'))
        old = get_bg_video()
        if old:
            try: os.remove(os.path.join(UPLOAD_DIR, "bg", old))
            except: pass
        new_name = f"bg_{int(datetime.now().timestamp())}_{secrets.token_hex(6)}_{orig}"
        f.save(os.path.join(UPLOAD_DIR, "bg", new_name))
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO bg_video (id, filename) VALUES (1, ?)", (new_name,))
        conn.commit(); conn.close()
        flash("✅ BG updated!", "success")
        return redirect(url_for('admin_bg'))
    return render_template_string(BG_VIDEO_TEMPLATE, owner_name=OWNER_NAME, bg_video=get_bg_video())

@app.route('/admin/bg/delete', methods=['POST'])
@admin_required
def admin_bg_delete():
    old = get_bg_video()
    if old:
        try: os.remove(os.path.join(UPLOAD_DIR, "bg", old))
        except: pass
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM bg_video WHERE id=1")
    conn.commit(); conn.close()
    flash("🗑️ BG removed.", "success")
    return redirect(url_for('admin_bg'))

@app.errorhandler(404)
def nf(e):
    return render_template_string("""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>404</title>""" + BASE_CSS + """</head><body>""" + BACKGROUND_HTML + """
<div class="container"><div class="lock-screen" style="margin-top:100px;">
<div class="lock-icon">❓</div><h2>404</h2><p>Not found</p>
<a href="/" class="btn">🏠 Home</a></div></div></body></html>"""), 404

@app.errorhandler(413)
def ftl(e):
    return render_template_string("""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Too Large</title>""" + BASE_CSS + """</head><body>""" + BACKGROUND_HTML + """
<div class="container"><div class="lock-screen" style="margin-top:100px;">
<div class="lock-icon">📦</div><h2>FILE TOO LARGE</h2><p>Upload in smaller batches.</p>
<a href="/admin/upload" class="btn">← Back</a></div></div></body></html>"""), 413

# ==================== ENTRY ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║   🔴 FILE STORE - RENDER DEPLOYMENT 🔴                      ║
    ║   🌐 Running on port {port}                                  ║
    ║   📁 Data dir: {BASE_DIR}                                    ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
