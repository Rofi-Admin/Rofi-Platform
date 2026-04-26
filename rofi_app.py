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

# ================= 🌟 3. إعدادات المتصفح وقاعدة البيانات والأمان =================
@st.cache_resource
def install_browsers():
    os.system("playwright install chromium")

install_browsers()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    # جدول المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    # جدول التقارير الجديد (مربوط باسم المستخدم)
    c.execute('''CREATE TABLE IF NOT EXISTS user_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, platform TEXT, url TEXT, report TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def create_user(username, password):
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # اسم المستخدم موجود مسبقاً
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hash_password(password):
        return True
    return False

def save_report_to_db(username, platform, url, report):
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute("INSERT INTO user_reports (username, platform, url, report) VALUES (?, ?, ?, ?)", (username, platform, url, report))
    conn.commit()
    conn.close()

def get_all_reports(username):
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute("SELECT platform, url, report, date FROM user_reports WHERE username=? ORDER BY date DESC", (username,))
    data = c.fetchall()
    conn.close()
    return data

init_db()

# ================= 🌟 4. محركات السحب والذكاء الاصطناعي =================
def scrape_amazon(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", viewport={'width': 1280, 'height': 800}, extra_http_headers={"Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7"})
            page = context.new_page()
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            if page.locator("text='تابع التسوق'").count() > 0:
                page.locator("text='تابع التسوق'").click()
                page.wait_for_timeout(4000) 
            for _ in range(6):
                page.keyboard.press("PageDown")
                page.wait_for_timeout(1500)
            page.screenshot(path="debug.png")
            reviews = page.locator("span[data-hook='review-body']").all_inner_texts()
            browser.close()
            if len(reviews) > 0: return reviews
            return "No_Reviews"
    except Exception as e: return f"Error: {e}"

def scrape_noon(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", viewport={'width': 1280, 'height': 800}, extra_http_headers={"Accept-Language": "ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7"})
            page = context.new_page()
            try: page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception: pass 
            page.wait_for_timeout(5000) 
            for _ in range(8):
                page.keyboard.press("PageDown") 
                page.wait_for_timeout(1500)     
            page.screenshot(path="debug.png")
            raw_texts = page.locator("p, span").all_inner_texts()
            browser.close()
            cleaned_reviews = []
            for text in raw_texts:
                t = text.strip().replace('\n', ' ')
                if 15 < len(t) < 800 and not any(word in t for word in ["ر.س", "SAR", "إضافة", "ريال", "خصم", "تسوق"]): cleaned_reviews.append(t)
            cleaned_reviews = list(set(cleaned_reviews))
            if len(cleaned_reviews) > 0: return cleaned_reviews
            return "No_Reviews"
    except Exception as e: return f"Error: {e}"

def analyze_reviews(reviews_list, platform_name):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
        أنت خبير أسواق. حلل تعليقات هذا المنتج من منصة ({platform_name}).
        التعليقات: {' '.join(reviews_list)}
        
        أريدك أن ترد عليّ *فقط* بصيغة JSON صحيحة، بدون أي نصوص إضافية، بهذا الشكل بالضبط:
        {{
            "score": 85, 
            "pros": ["ميزة 1", "ميزة 2"],
            "cons": ["عيب 1", "عيب 2"],
            "advice": "نصيحة استراتيجية للتاجر"
        }}
        ملاحظة: score هو تقييم لجودة المنتج من 0 إلى 100.
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(raw_text)
    except Exception as e: 
        return f"Error Formatting: {e}"

# ================= 🌟 5. واجهة تسجيل الدخول والتطبيق =================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None

# إذا لم يكن مسجلاً للدخول، نعرض بوابة الحماية
if not st.session_state.authenticated:
    if os.path.exists("logo.png"):
        col_logo1, col_logo2, col_logo3 = st.columns([2,1,2])
        with col_logo2: st.image("logo.png", use_container_width=True)
        
    st.markdown('<h1 class="main-title">🔐 بوابة منصة روفي</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["تسجيل الدخول", "إنشاء حساب جديد"])
        
        with tab1:
            log_user = st.text_input("اسم المستخدم:")
            log_pass = st.text_input("كلمة المرور:", type="password")
            if st.button("دخول للمحرك"):
                if authenticate_user(log_user, log_pass):
                    st.session_state.authenticated = True
                    st.session_state.username = log_user
                    st.rerun()
                else:
                    st.error("❌ بيانات الدخول غير صحيحة")
                    
        with tab2:
            reg_user = st.text_input("اختر اسم مستخدم:")
            reg_pass = st.text_input("اختر كلمة مرور:", type="password")
            if st.button("تسجيل الحساب"):
                if reg_user and reg_pass:
                    if create_user(reg_user, reg_pass):
                        st.success("✅ تم إنشاء حسابك بنجاح! اذهب إلى (تسجيل الدخول) للدخول للمنصة.")
                    else:
                        st.error("⚠️ اسم المستخدم هذا مستخدم مسبقاً، اختر اسماً آخر.")
                else:
                    st.warning("⚠️ يرجى تعبئة جميع الحقول.")
    st.stop()

# --- واجهة المنصة بعد تسجيل الدخول ---
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", width=100)
else:
    st.sidebar.markdown("🚀")

# بيانات المستخدم في القائمة الجانبية
st.sidebar.markdown(f"👤 مرحباً: **{st.session_state.username}**")
if st.sidebar.button("خروج 🚪"):
    st.session_state.authenticated = False
    st.session_state.username = None
    st.rerun()
    
st.sidebar.markdown("---")
st.sidebar.title("رادار روفي")
page = st.sidebar.radio("انتقل إلى:", ["🚀 محرك التحليل السحابي", "📂 أرشيف التقارير (الخاص بك)"])

if page == "🚀 محرك التحليل السحابي":
    st.markdown('<h1 class="main-title">🚀 محرك روفي للتحليل الذكي</h1>', unsafe_allow_html=True)
    
    target_platform = st.radio("اختر المنصة المستهدفة:", ["أمازون السعودية 🔵", "نون السعودية 🟡"], horizontal=True)
    url = st.text_input(f"🔗 الصق رابط منتج {target_platform} هنا:")
    
    if st.button("ابدأ تشغيل الرادار"):
        if not url:
            st.warning("⚠️ أرجوك، ضع رابطاً ليعمل المحرك!")
        else:
            if url and not url.startswith("http"):
                url = "https://" + url
                
            with st.status(f"📡 جاري اختراق جدار {target_platform}...") as status:
                if "أمازون" in target_platform:
                    data = scrape_amazon(url)
                else:
                    data = scrape_noon(url)
                    
                if isinstance(data, list):
                    st.write("✅ نجح الاختراق وجاري قراءة التعليقات...")
                    report_data = analyze_reviews(data, target_platform)
                    
                    # حفظ التقرير باسم المستخدم الحالي
                    save_report_to_db(st.session_state.username, target_platform, url, str(report_data))
                    status.update(label="✅ اكتملت المهمة!", state="complete")
                    
                    if isinstance(report_data, dict):
                        st.markdown("---")
                        st.markdown('<h2 style="text-align: center; color: #f4c430;">📊 لوحة التحليل الاستراتيجية</h2>', unsafe_allow_html=True)
                        
                        score = report_data.get("score", 0)
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.metric(label="مؤشر جودة المنتج", value=f"{score}%")
                            st.progress(score / 100.0)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        col_pros, col_cons = st.columns(2)
                        with col_pros:
                            st.success("✅ أبرز المميزات")
                            for p in report_data.get("pros", []): st.write(f"• {p}")
                        with col_cons:
                            st.error("❌ أبرز العيوب")
                            for c in report_data.get("cons", []): st.write(f"• {c}")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.info("💡 نصيحة روفي الاستراتيجية للمنافسة")
                        st.write(report_data.get("advice", ""))
                    else:
                        st.markdown(f'<div class="report-card">{report_data}</div>', unsafe_allow_html=True)

                elif data == "No_Reviews":
                    status.update(label="⚠️ عائق تقني", state="error")
                    st.warning("لم نجد تعليقات. انظر للصورة أدناه:")
                    if os.path.exists("debug.png"): st.image("debug.png")
                else:
                    status.update(label="❌ فشل الرادار", state="error")
                    st.error(data)

elif page == "📂 أرشيف التقارير (الخاص بك)":
    st.markdown('<h1 class="main-title">📂 خزينتك السرية</h1>', unsafe_allow_html=True)
    # جلب التقارير الخاصة بالمستخدم المسجل فقط
    saved_reports = get_all_reports(st.session_state.username)
    
    if saved_reports:
        for idx, (rep_platform, rep_url, rep_text, rep_date) in enumerate(saved_reports):
            with st.expander(f"📅 {rep_date} | {rep_platform}"):
                st.write(f"**الرابط:** {rep_url}")
                try:
                    report_data = ast.literal_eval(rep_text)
                    if isinstance(report_data, dict):
                        score = report_data.get("score", 0)
                        st.metric(label="مؤشر جودة المنتج", value=f"{score}%")
                        col_pros, col_cons = st.columns(2)
                        with col_pros:
                            st.success("✅ المميزات")
                            for p in report_data.get("pros", []): st.write(f"• {p}")
                        with col_cons:
                            st.error("❌ العيوب")
                            for c in report_data.get("cons", []): st.write(f"• {c}")
                            
                        st.info("💡 نصيحة روفي")
                        st.write(report_data.get("advice", ""))
                        
                        download_content = f"تقرير منصة روفي\nبواسطة: {st.session_state.username}\nالمنصة: {rep_platform}\nالتاريخ: {rep_date}\nمؤشر الجودة: {score}%\n\nالمميزات:\n"
                        download_content += "\n".join([f"- {p}" for p in report_data.get("pros", [])])
                        download_content += "\n\nالعيوب:\n"
                        download_content += "\n".join([f"- {c}" for c in report_data.get("cons", [])])
                        download_content += f"\n\nالنصيحة:\n{report_data.get('advice', '')}"
                        
                        st.download_button(label="📥 تحميل التقرير (Text)", data=download_content, file_name=f"Rofi_Report_{idx}.txt", mime="text/plain")
                except:
                    st.markdown(f'<div class="report-card">{rep_text}</div>', unsafe_allow_html=True)
    else:
        st.write("أرشيفك فارغ حالياً. ابدأ بتحليل المنتجات لتعبئته!")

st.sidebar.markdown("---")
st.sidebar.markdown('<p style="text-align: center; color: rgba(255,255,255,0.5);">منصة روفي © 2026</p>', unsafe_allow_html=True)
