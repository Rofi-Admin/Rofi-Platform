import streamlit as st
import asyncio
import sys
import sqlite3
import os
import json
import ast
import hashlib
from playwright.sync_api import sync_playwright
from google import genai

# 🌟 1. إعدادات الصفحة
st.set_page_config(page_title="منصة روفي للتحليل الذكي | Rofi", page_icon="🚀", layout="wide")

# ================= 🌟 2. الثيم البصري =================
def apply_custom_theme():
    st.markdown("""
        <style>
        .stApp { background-color: #0c1a3c; color: white; }
        [data-testid="stSidebar"] { background-color: #081228; border-right: 2px solid #f4c430; }
        [data-testid="stSidebar"] * { color: white !important; }
        .main-title { text-align: center; color: #f4c430; font-size: 2.5rem; font-weight: bold; margin-bottom: 30px; }
        div[data-testid="stTextInput"] input { background-color: #fff9e6 !important; color: #000 !important; border: 2px solid #f4c430 !important; border-radius: 8px; padding: 10px; font-size: 1.1rem; }
        div[data-testid="stTextInput"] label, div[data-testid="stRadio"] label p { color: #f4c430 !important; font-weight: bold; font-size: 1.1rem; }
        .stButton>button { background-color: #f4c430; color: #0c1a3c; font-weight: bold; border-radius: 8px; border: none; width: 100%; transition: 0.3s; }
        .stButton>button:hover { background-color: white; color: #0c1a3c; }
        .report-card { background-color: white; color: #333; padding: 20px; border-radius: 10px; border-right: 5px solid #f4c430; margin-top: 20px; margin-bottom: 20px; }
        .report-card h1, .report-card h2, .report-card h3, .report-card p, .report-card li { color: #333 !important; }
        </style>
    """, unsafe_allow_html=True)

apply_custom_theme()

# ================= 🌟 3. إعدادات السحابة والمحرك =================
@st.cache_resource
def install_browsers():
    os.system("playwright install chromium")
install_browsers()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# ================= 🌟 4. قواعد البيانات =================
def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, email TEXT, password TEXT)''')
    try: c.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except: pass
    c.execute('''CREATE TABLE IF NOT EXISTS user_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, platform TEXT, url TEXT, report TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def create_user(username, email, password):
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError: return False 
    finally: conn.close()

def authenticate_user(identifier, password):
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute("SELECT username, email, password FROM users WHERE username=? OR email=?", (identifier, identifier))
    result = c.fetchone()
    conn.close()
    if result and result[2] == hash_password(password): return {"username": result[0], "email": result[1]}
    return None

def save_report_to_db(username, platform, url, report):
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute("INSERT INTO user_reports (username, platform, url, report) VALUES (?, ?, ?, ?)", (username, platform, url, report))
    conn.commit()
    conn.close()

def get_all_reports(username):
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute("SELECT platform, url, report, date FROM user_reports WHERE username=? OR username IS NULL OR username='' ORDER BY date DESC", (username,))
    data = c.fetchall()
    conn.close()
    return data

init_db()

# ================= 🌟 5. محرك السحب والذكاء الاصطناعي =================
def scrape_amazon(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)", viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            if page.locator("text='تابع التسوق'").count() > 0: page.locator("text='تابع التسوق'").click(); page.wait_for_timeout(4000) 
            for _ in range(6): page.keyboard.press("PageDown"); page.wait_for_timeout(1500)
            reviews = page.locator("span[data-hook='review-body']").all_inner_texts()
            browser.close()
            return reviews if len(reviews) > 0 else "No_Reviews"
    except Exception as e: return f"Error: {e}"

def scrape_noon(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) 
            page = browser.new_page()
            try: page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except: pass 
            page.wait_for_timeout(5000) 
            for _ in range(8): page.keyboard.press("PageDown"); page.wait_for_timeout(1500)     
            raw_texts = page.locator("p, span").all_inner_texts()
            browser.close()
            cleaned = list(set([t.strip() for t in raw_texts if 15 < len(t) < 800 and not any(w in t for w in ["ر.س", "SAR", "إضافة"])]))
            return cleaned if len(cleaned) > 0 else "No_Reviews"
    except Exception as e: return f"Error: {e}"

def analyze_reviews(reviews_list, platform_name):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""أنت خبير استراتيجي في الأسواق العالمية. حلل تعليقات منتج من ({platform_name}). 
        أريدك أن ترد بصيغة JSON حصراً تحتوي على:
        1. score: تقييم من 100.
        2. pros: قائمة بأبرز المميزات.
        3. cons: قائمة بأخطر العيوب.
        4. expert_opinion: تحليل استراتيجي مفصل وعميق جداً للتاجر (رأي الخبير) يشمل نصائح للمنافسة وتطوير المنتج.
        التعليقات: {' '.join(reviews_list)}
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(raw_text)
    except Exception as e: return f"Error: {e}"

# ================= 🌟 6. واجهة التطبيق =================
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<h1 class="main-title">🔐 دخول منصة روفي</h1>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["تسجيل الدخول", "إنشاء حساب"])
        with tab1:
            log_id = st.text_input("اسم المستخدم:")
            log_pass = st.text_input("كلمة المرور:", type="password")
            if st.button("دخول"):
                user = authenticate_user(log_id, log_pass)
                if user: st.session_state.authenticated = True; st.session_state.username = user["username"]; st.rerun()
                else: st.error("بيانات خاطئة")
        with tab2:
            reg_user = st.text_input("اسم مستخدم جديد:")
            reg_email = st.text_input("البريد:")
            reg_pass = st.text_input("كلمة مرور:")
            if st.button("تسجيل"):
                if create_user(reg_user, reg_email, reg_pass): st.success("تم التسجيل! سجل دخولك الآن.")
    st.stop()

# --- القائمة الجانبية ---
st.sidebar.markdown(f"👤 مرحباً: **{st.session_state.username}**")
if st.sidebar.button("خروج 🚪"): st.session_state.authenticated = False; st.rerun()
st.sidebar.markdown("---")
page = st.sidebar.radio("انتقل إلى:", ["🚀 محرك التحليل", "📂 الأرشيف الفولاذي"])

if page == "🚀 محرك التحليل":
    st.markdown('<h1 class="main-title">🚀 رادار روفي الذكي</h1>', unsafe_allow_html=True)
    target = st.radio("المنصة:", ["أمازون السعودية 🔵", "نون السعودية 🟡"], horizontal=True)
    url = st.text_input("🔗 رابط المنتج:")
    
    if st.button("بدأ التحليل"):
        with st.status("📡 جاري العمل...") as status:
            data = scrape_amazon(url) if "أمازون" in target else scrape_noon(url)
            if isinstance(data, list):
                report = analyze_reviews(data, target)
                save_report_to_db(st.session_state.username, target, url, str(report))
                status.update(label="✅ اكتمل!", state="complete")
                
                if isinstance(report, dict):
                    st.metric("مؤشر الجودة", f"{report.get('score', 0)}%")
                    
                    c1, c2 = st.columns(2)
                    with c1: 
                        st.success("✅ المميزات")
                        # الطريقة الصحيحة الخالية من الأخطاء لعرض القوائم
                        for p in report.get("pros", []):
                            st.write(f"• {p}")
                            
                    with c2: 
                        st.error("❌ العيوب")
                        # الطريقة الصحيحة الخالية من الأخطاء لعرض القوائم
                        for c in report.get("cons", []):
                            st.write(f"• {c}")
                    
                    st.info("⚖️ رأي الخبير الاستراتيجي")
                    st.write(report.get("expert_opinion", report.get("advice", "لا يوجد تحليل إضافي")))
                else: 
                    st.write(report)
            else: 
                status.update(label="❌ خطأ", state="error")
                st.warning("لم نجد بيانات.")

elif page == "📂 الأرشيف الفولاذي":
    st.markdown('<h1 class="main-title">📂 خزينتك السرية</h1>', unsafe_allow_html=True)
    reports = get_all_reports(st.session_state.username)
    if reports:
        for idx, (plat, r_url, r_text, r_date) in enumerate(reports):
            with st.expander(f"📅 {r_date} | {plat}"):
                st.write(f"**الرابط:** {r_url}")
                try:
                    r_data = ast.literal_eval(r_text)
                    if isinstance(r_data, dict):
                        st.metric("مؤشر الجودة", f"{r_data.get('score', 0)}%")
                        
                        c1, c2 = st.columns(2)
                        with c1: 
                            st.success("✅ المميزات")
                            for p in r_data.get("pros", []):
                                st.write(f"• {p}")
                        with c2: 
                            st.error("❌ العيوب")
                            for c in r_data.get("cons", []):
                                st.write(f"• {c}")
                                
                        st.info("⚖️ رأي الخبير الاستراتيجي")
                        st.write(r_data.get("expert_opinion", r_data.get("advice", "")))
                    else:
                        st.write(r_text) # للتقارير النصية القديمة جداً
                except: 
                    st.write(r_text) # في حالة فشل التحويل يعرض النص القديم
    else: 
        st.write("الأرشيف فارغ.")
