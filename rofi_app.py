import streamlit as st
import asyncio
import sys
import sqlite3
import os
import base64 # مضاف لقراءة الصورة
from playwright.sync_api import sync_playwright
from google import genai

# ================= 🌟 1. إعدادات الثيم الاحترافي (CSS) =================
def apply_custom_theme():
    # دالة لتحويل الصورة المحلية إلى Base64 لعرضها
    def get_base64_of_bin_file(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()

    # محاولة تحميل اللوغو إذا وجد
    logo_html = ""
    if os.path.exists("logo.png"):
        try:
            bin_str = get_base64_of_bin_file('logo.png')
            logo_html = f'<img src="data:image/png;base64,{bin_str}" class="sidebar-logo">'
        except:
            pass

    st.markdown(f"""
        <style>
        /* 1. الخلفية الزرقاء الليلي العميق (Main Background) */
        .stApp {{
            background-color: #0c1a3c;
            color: white;
        }}

        /* 2. تزيين Sidebar (القائمة الجانبية) */
        [data-testid="stSidebar"] {{
            background-color: #081228;
            border-right: 2px solid #f4c430; /* خط ذهبي فاصل */
        }}
        [data-testid="stSidebar"] .sidebar-content {{
            color: white;
        }}
        
        /* تصميم اللوغو داخل Sidebar */
        .sidebar-logo {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            display: block;
            margin-left: auto;
            margin-right: auto;
            margin-top: -30px;
            margin-bottom: 20px;
            border: 3px solid #f4c430;
            box-shadow: 0 4px 8px rgba(244, 196, 48, 0.3);
        }}

        /* 3. العنوان الرئيسي في المنتصف */
        .main-title {{
            text-align: center;
            color: #f4c430; /* أصفر ذهبي */
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}

        /* 4. تزيين صندوق مدخلات الرابط (Yellow Input) */
        div[data-testid="stTextInput"] input {{
            background-color: #fff9e6 !important; /* أصفر فاتح جداً للخلفية */
            color: #333 !important; /* خط غامق للقراءة */
            border: 2px solid #f4c430 !important; /* حدود صفراء */
            border-radius: 10px;
            padding: 10px;
            font-size: 1.1rem;
        }}
        div[data-testid="stTextInput"] label {{
            color: white !important;
            font-weight: bold;
        }}

        /* 5. تزيين الأزرار */
        .stButton>button {{
            background-color: #f4c430;
            color: #0c1a3c;
            font-weight: bold;
            border-radius: 20px;
            border: none;
            width: 100%;
            transition: all 0.3s;
        }}
        .stButton>button:hover {{
            background-color: white;
            color: #0c1a3c;
            transform: scale(1.03);
        }}

        /* 6. كروت التقارير (Reports Cards) */
        .report-card {{
            background-color: rgba(255, 255, 255, 0.95);
            color: #333;
            padding: 20px;
            border-radius: 15px;
            border-left: 5px solid #f4c430;
            box-shadow: 0 6px 12px rgba(0,0,0,0.3);
            margin-bottom: 20px;
        }}
        .report-card h1, .report-card h2, .report-card h3 {{
            color: #0c1a3c !important;
        }}
        
        /* 7. تزيين الراديو والألوان */
        div[data-testid="stRadio"] label p {{
            color: white !important;
        }}
        div[data-testid="stMarkdownContainer"] p {{
            color: white;
        }}

        /* 8. تزيين الاستاتوس والفشل */
        [data-testid="stStatusWidget"] {{
            background-color: rgba(244, 196, 48, 0.1);
            border: 1px solid #f4c430;
            border-radius: 10px;
        }}
        
        /* إظهار اللوغو برمجياً في Sidebar */
        [data-testid="stSidebarNav"]::before {{
            content: "";
            display: block;
            margin-top: 10px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # وضع اللوغو فوق النفيجيشن في السايد بار
    if logo_html:
        st.sidebar.markdown(logo_html, unsafe_allow_html=True)

# 🌟 تطبيق الثيم فوراً
apply_custom_theme()

# ================= ================= ================= =================

# --- تثبيت المتصفح السحابي ---
@st.cache_resource
def install_browsers():
    os.system("playwright install chromium")

install_browsers()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
ACCESS_PASSWORD = "Rofi2026"

def init_db():
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, url TEXT, report TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_report_to_db(platform, url, report):
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute("INSERT INTO reports (platform, url, report) VALUES (?, ?, ?)", (platform, url, report))
    conn.commit()
    conn.close()

def get_all_reports():
    conn = sqlite3.connect('rofi_database.db')
    c = conn.cursor()
    c.execute("SELECT platform, url, report, date FROM reports ORDER BY date DESC")
    data = c.fetchall()
    conn.close()
    return data

init_db()

# محركات السحب (كما هي)
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
        prompt = f"أنت خبير أسواق. حلل تعليقات منتج من منصة ({platform_name}) السعودية لاستخراج بذكاء: 1. العيوب 2. المميزات 3. نصيحة للتاجر للمنافسة (يفضل باللغة العربية الفصحى وبشكل نقاط واضحة): {' '.join(reviews_list)}"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e: return f"Error: {e}"

# --- الواجهة الرئيسية (المُزينة) ---
st.set_page_config(page_title="منصة روفي للتحليل الذكي | Rofi", page_icon="logo.png", layout="wide")

# إعادة تطبيق الثيم لأن st.set_page_config تمسح الحقن الكلاسيكي
apply_custom_theme()

if not st.session_state.get("authenticated", False):
    st.markdown('<h1 class="main-title">🔐 دخول الإدارة | روفي</h1>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            pass_input = st.text_input("أدخل كلمة المرور السرية:", type="password")
            if st.button("فتح محرك روفي"):
                if pass_input == ACCESS_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ كلمة المرور غير صحيحة")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

st.sidebar.title("🗂️ رادار شركة نفطي")
page = st.sidebar.radio("انتقل إلى:", ["🚀 محرك التحليل السحابي", "📂 أرشيف تقاريرك الفولاذية"])

if page == "🚀 محرك التحليل السحابي":
    st.markdown('<h1 class="main-title">🚀 محرك روفي للتحليل الذكي</h1>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
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
                        st.write(f"✅ نجح الاختراق وجاري قراءة التعليقات وتوليد الذكاء البشري المساعد...")
                        report = analyze_reviews(data, target_platform)
                        save_report_to_db(target_platform, url, report)
                        status.update(label="✅ اكتملت المهمة! انظر للتقرير أدناه", state="complete")
                        
                        st.markdown('<div class="report-card">', unsafe_allow_html=True)
                        st.markdown("### 📝 التقرير الذكي النهائي")
                        st.markdown(report)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    elif data == "No_Reviews":
                        status.update(label="⚠️ عائق تقني", state="error")
                        st.warning("أمازون/نون أظهرت صفحة حماية. انظر للصورة الفنية أدناه لما واجهه الروبوت:")
                        if os.path.exists("debug.png"):
                            st.image("debug.png", caption="📸 لقطة استخباراتية حية لما يراه الروبوت")
                    else:
                        status.update(label="❌ فشل الرادار", state="error")
                        st.error(data)
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "📂 أرشيف تقاريرك الفولاذية":
    st.markdown('<h1 class="main-title">📂 أرشيف شركة نفطي الدائم</h1>', unsafe_allow_html=True)
    saved_reports = get_all_reports()
    if saved_reports:
        for idx, (rep_platform, rep_url, rep_text, rep_date) in enumerate(saved_reports):
            with st.expander(f"📅 {rep_date} | {rep_platform}"):
                st.write(f"**الرابط:** {rep_url}")
                st.markdown('<div class="report-card">', unsafe_allow_html=True)
                st.markdown(rep_text)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.write("الأرشيف فارغ.")

# تزيين الفوتر (Footer)
st.sidebar.markdown("---")
st.sidebar.markdown('<p style="text-align: center; color: rgba(255,255,255,0.5);">منصة روفي © 2024<br>إمبراطورية نفطي القابضة 🇸🇦</p>', unsafe_allow_html=True)
