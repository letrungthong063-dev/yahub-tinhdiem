// auth.js - Shared auth utilities

function getToken() { return localStorage.getItem("token"); }
function getUser() { const u = localStorage.getItem("user"); return u ? JSON.parse(u) : null; }
function requireAuth() { if (!getToken()) window.location.href = "/login"; }
function logout() { localStorage.removeItem("token"); localStorage.removeItem("user"); window.location.href = "/login"; }
function authHeaders() { return { "Content-Type": "application/json", "Authorization": `Bearer ${getToken()}` }; }

async function checkNotification() {
    try {
        const res = await fetch("/api/notification");
        const data = await res.json();
        if (data.active && data.message) {
            const div = document.createElement("div");
            div.style.cssText = "position:fixed;top:0;left:0;right:0;background:linear-gradient(135deg,#ffd700,#ff8c00);color:#000;text-align:center;padding:10px 16px;z-index:9999;font-family:Rajdhani,sans-serif;font-weight:700;font-size:15px;letter-spacing:1px;box-shadow:0 2px 20px rgba(255,215,0,0.4);";
            div.textContent = "⚡ " + data.message;
            document.body.prepend(div);
            setTimeout(() => div.remove(), (data.duration || 5) * 1000);
        }
    } catch {}
}

function renderNavbar(activePage) {
    const user = getUser();
    const isAdmin = user && user.role === "admin";
    const pages = [
        {href: "/dashboard", label: "Tạo BXH", icon: "⚡"},
        {href: "/backgrounds", label: "Backgrounds", icon: "🎨"},
        {href: "/history", label: "Lịch sử", icon: "📋"},
    ];
    if (isAdmin) pages.push({href: "/admin", label: "Admin", icon: "⚙️"});

    const desktopLinks = pages.map(p => `<a href="${p.href}" class="nav-link${activePage===p.href?' active':''}">${p.icon} ${p.label}</a>`).join("");
    const mobileLinks = pages.map(p => `<a href="${p.href}" class="mob-link${activePage===p.href?' active':''}">${p.icon} ${p.label}</a>`).join("");

    return `<nav class="yahub-nav">
        <div class="nav-inner">
            <a href="/dashboard" class="nav-brand"><span style="filter:drop-shadow(0 0 10px #00f5ff)">🏆</span><span class="brand-text">YAHUB</span></a>
            <div class="nav-links">${desktopLinks}</div>
            <div class="nav-right">
                <span class="nav-email">${user ? user.email : ""}</span>
                <button onclick="logout()" class="btn-logout">Đăng xuất</button>
            </div>
            <button onclick="toggleMobileMenu()" class="mob-toggle">☰</button>
        </div>
        <div id="mobileMenu" class="mob-menu hidden">${mobileLinks}<div class="mob-sep"></div><span class="nav-email" style="padding:8px 16px;display:block">${user?user.email:""}</span><button onclick="logout()" class="btn-logout" style="margin:8px 16px;width:calc(100%-32px)">Đăng xuất</button></div>
    </nav>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500&display=swap');
        .yahub-nav{background:rgba(5,8,15,0.95);border-bottom:1px solid rgba(0,245,255,0.12);backdrop-filter:blur(20px);position:sticky;top:0;z-index:100;box-shadow:0 4px 30px rgba(0,0,0,0.4);}
        .nav-inner{max-width:1200px;margin:0 auto;padding:0 20px;display:flex;align-items:center;gap:8px;height:60px;}
        .nav-brand{display:flex;align-items:center;gap:10px;text-decoration:none;margin-right:16px;font-size:20px;}
        .brand-text{font-family:'Orbitron',monospace;font-size:18px;font-weight:900;background:linear-gradient(135deg,#00f5ff,#fff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:3px;}
        .nav-links{display:flex;align-items:center;gap:4px;flex:1;}
        .nav-link{display:flex;align-items:center;gap:6px;padding:7px 13px;border-radius:8px;text-decoration:none;color:rgba(255,255,255,0.5);font-family:'Rajdhani',sans-serif;font-size:15px;font-weight:600;letter-spacing:0.5px;transition:all 0.2s;white-space:nowrap;border:1px solid transparent;}
        .nav-link:hover{color:#00f5ff;background:rgba(0,245,255,0.06);}
        .nav-link.active{color:#00f5ff;background:rgba(0,245,255,0.1);border-color:rgba(0,245,255,0.2);}
        .nav-right{display:flex;align-items:center;gap:12px;}
        .nav-email{font-size:12px;color:rgba(255,255,255,0.25);font-family:'Inter',sans-serif;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
        .btn-logout{padding:7px 16px;border-radius:6px;border:1px solid rgba(255,77,109,0.35);background:rgba(255,77,109,0.08);color:#ff6b85;cursor:pointer;font-family:'Rajdhani',sans-serif;font-size:13px;font-weight:600;letter-spacing:1px;transition:all 0.2s;}
        .btn-logout:hover{background:rgba(255,77,109,0.2);border-color:#ff4d6d;}
        .mob-toggle{display:none;background:none;border:none;color:#00f5ff;font-size:24px;cursor:pointer;margin-left:auto;padding:4px;}
        .mob-menu{padding:8px 0 16px;border-top:1px solid rgba(0,245,255,0.08);}
        .mob-menu.hidden{display:none;}
        .mob-link{display:block;padding:12px 20px;text-decoration:none;color:rgba(255,255,255,0.5);font-family:'Rajdhani',sans-serif;font-size:16px;font-weight:600;transition:all 0.2s;}
        .mob-link:hover,.mob-link.active{color:#00f5ff;background:rgba(0,245,255,0.06);}
        .mob-sep{height:1px;background:rgba(255,255,255,0.06);margin:8px 0;}
        @media(max-width:768px){.nav-links,.nav-right{display:none!important;}.mob-toggle{display:block;}}
    </style>`;
}

function toggleMobileMenu() {
    document.getElementById("mobileMenu").classList.toggle("hidden");
}
