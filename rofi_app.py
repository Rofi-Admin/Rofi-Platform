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
    # 🌟 الإصلاح: جلب التقارير الخاصة بك + التقارير القديمة التي لم يكن لها مستخدم
    c.execute("SELECT platform, url, report, date FROM user_reports WHERE username=? OR username IS NULL ORDER BY date DESC", (username,))
    data = c.fetchall()
    conn.close()
    return data

init_db()

# ================= 🌟 5. توليد الإكسل =================
def generate_csv_data(report_data):
    csv_content = "التصنيف,التفاصيل\n"
    for p in report_data.get("pros", []): csv_content += f"ميزة,{p.replace(',', ' ')}\n"
    for c in report_data.get("cons", []): csv_content += f"عيب,{c.replace(',', ' ')}\n"
    csv_content += f"نصيحة,{report_data.get('advice', '').replace(',', ' ')}\n"
    return csv_content.encode('utf-8-sig') 

# ================= 🌟 6. السحب والذكاء الاصطناعي =================
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
            if len(reviews) > 0: return reviews
            return "No_Reviews"
    except Exception as e: return f"Error: {e}"

def scrape_noon(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)", viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            try: page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except: pass 
            page.wait_for_timeout(5000) 
            for _ in range(8): page.keyboard.press("PageDown"); page.wait_for_timeout(1500)     
            raw_texts = page.locator("p, span").all_inner_texts()
            browser.close()
            cleaned_reviews = list(set([t.strip().replace('\n', ' ') for t in raw_texts if 15 < len(t) < 800 and not any(word in t for word in ["ر.س", "SAR", "إضافة"])]))
            if len(cleaned_reviews) > 0: return cleaned_reviews
            return "No_Reviews"
    except Exception as e: return f"Error: {e}"

def analyze_reviews(reviews_list, platform_name):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""أنت خبير أسواق. حلل تعليقات هذا المنتج من منصة ({platform_name}). التعليقات: {' '.join(reviews_list)}
        أريدك أن ترد عليّ *فقط* بصيغة JSON صحيحة، بدون أي نصوص إضافية:
        {{"score": 85, "pros": ["ميزة 1"], "cons": ["عيب 1"], "advice": "نصيحة"}}"""
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(raw_text)
    except Exception as e: return f"Error Formatting: {e}"

# ================= 🌟 7. واجهة التطبيق =================
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "username" not in st.session_state: st.session_state.username = None

if not st.session_state.authenticated:
    st.markdown('<h1 class="main-title">🔐 بوابة منصة روفي</h1>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["تسجيل الدخول", "إنشاء حساب جديد"])
        with tab1:
            log_id = st.text_input("اسم المستخدم أو الإيميل:")
            log_pass = st.text_input("كلمة المرور:", type="password")
            if st.button("دخول للمحرك"):
                user_data = authenticate_user(log_id, log_pass)
                if user_data:
                    st.session_state.authenticated = True; st.session_state.username = user_data["username"]; st.rerun()
                else: st.error("❌ بيانات الدخول غير صحيحة")
        with tab2:
            reg_user = st.text_input("اختر اسم مستخدم:")
            reg_email = st.text_input("البريد الإلكتروني:")
            reg_pass = st.text_input("اختر كلمة مرور:", type="password")
            if st.button("تسجيل الحساب"):
                if reg_user and reg_email and reg_pass:
                    if create_user(reg_user, reg_email, reg_pass): st.success("✅ تم إنشاء حسابك بنجاح!")
                    else: st.error("⚠️ اسم المستخدم مسجل مسبقاً.")
                else: st.warning("⚠️ يرجى تعبئة جميع الحقول.")
    st.stop()

# --- القائمة الجانبية ---
st.sidebar.markdown(f"👤 مرحباً: **{st.session_state.username}**")
if st.sidebar.button("خروج 🚪"): st.session_state.authenticated = False; st.rerun()
st.sidebar.markdown("---")
page = st.sidebar.radio("انتقل إلى:", ["🚀 محرك التحليل السحابي", "📂 الأرشيف الفولاذي"])

if page == "🚀 محرك التحليل السحابي":
    st.markdown('<h1 class="main-title">🚀 محرك روفي للتحليل الذكي</h1>', unsafe_allow_html=True)
    target_platform = st.radio("اختر المنصة:", ["أمازون السعودية 🔵", "نون السعودية 🟡"], horizontal=True)
    url = st.text_input(f"🔗 الصق رابط منتج {target_platform}:")
    
    if st.button("ابدأ تشغيل الرادار"):
        if not url: st.warning("⚠️ أرجوك، ضع رابطاً!")
        else:
            if not url.startswith("http"): url = "https://" + url
            with st.status(f"📡 جاري الاختراق...") as status:
                data = scrape_amazon(url) if "أمازون" in target_platform else scrape_noon(url)
                if isinstance(data, list):
                    report_data = analyze_reviews(data, target_platform)
                    save_report_to_db(st.session_state.username, target_platform, url, str(report_data))
                    status.update(label="✅ اكتملت المهمة!", state="complete")
                    
                    if isinstance(report_data, dict):
                        st.markdown('<h2 style="text-align: center; color: #f4c430;">📊 لوحة التحليل</h2>', unsafe_allow_html=True)
                        score = report_data.get("score", 0)
                        
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2: st.metric(label="مؤشر الجودة", value=f"{score}%"); st.progress(score / 100.0)
                        
                        col_pros, col_cons = st.columns(2)
                        with col_pros:
                            st.success("✅ المميزات")
                            # 🌟 الإصلاح الجذري لمشكلة الـ NULL هنا
                            for p in report_data.get("pros", []): 
                                st.write(f"• {p}")
                        with col_cons:
                            st.error("❌ العيوب")
                            # 🌟 والإصلاح هنا أيضاً
                            for c in report_data.get("cons", []): 
                                st.write(f"• {c}")
                                
                        st.info("💡 نصيحة روفي")
                        st.write(report_data.get("advice", ""))
                        
                        # زر تحميل الإكسل
                        st.download_button(label="📊 تحميل كإكسل (CSV)", data=generate_csv_data(report_data), file_name="Rofi_Report.csv", mime="text/csv")
                    else: st.write(report_data)
                elif data == "No_Reviews": status.update(label="⚠️ عائق تقني", state="error"); st.warning("لم نجد تعليقات.")
                else: status.update(label="❌ فشل الرادار", state="error"); st.error(data)

elif page == "📂 الأرشيف الفولاذي":
    st.markdown('<h1 class="main-title">📂 خزينتك السرية</h1>', unsafe_allow_html=True)
    saved_reports = get_all_reports(st.session_state.username)
    
    if saved_reports:
        # شريط بحث نظيف وبسيط
        search_query = st.text_input("🔍 ابحث في أرشيفك:", placeholder="ابحث بالرابط...")
        filtered = [r for r in saved_reports if search_query.lower() in r[1].lower() or search_query.lower() in r[0].lower()]
        
        for idx, (rep_platform, rep_url, rep_text, rep_date) in enumerate(filtered):
            with st.expander(f"📅 {rep_date} | {rep_platform}"):
                st.write(f"**الرابط:** {rep_url}")
                try:
                    report_data = ast.literal_eval(rep_text)
                    if isinstance(report_data, dict):
                        score = report_data.get("score", 0)
                        st.metric("مؤشر الجودة", f"{score}%")
                        
                        col_p, col_c = st.columns(2)
                        with col_p:
                            st.success("✅ المميزات")
                            for p in report_data.get("pros", []): st.write(f"• {p}")
                        with col_c:
                            st.error("❌ العيوب")
                            for c in report_data.get("cons", []): st.write(f"• {c}")
                        
                        st.download_button("📊 تحميل كإكسل (CSV)", data=generate_csv_data(report_data), file_name=f"Rofi_{idx}.csv", key=f"csv_{idx}")
                except: 
                    # عرض التقرير القديم جداً (النصي) كما كان
                    st.write(rep_text)
    else: st.write("أرشيفك فارغ.")
