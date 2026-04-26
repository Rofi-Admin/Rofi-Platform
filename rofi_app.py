import streamlit as st
import asyncio
import sys
import sqlite3
import os
import json
from playwright.sync_api import sync_playwright
from google import genai

# 🌟 1. إعدادات الصفحة (يجب أن تكون في السطر الأول)
st.set_page_config(page_title="منصة روفي للتحليل الذكي | Rofi", page_icon="🚀", layout="wide")

# ================= 🌟 2. الثيم البصري (نسخة نظيفة وخفيفة) =================
def apply_custom_theme():
    st.markdown("""
        <style>
        /* الخلفية الزرقاء الداكنة */
        .stApp {
            background-color: #0c1a3c;
            color: white;
        }

        /* القائمة الجانبية */
        [data-testid="stSidebar"] {
            background-color: #081228;
            border-right: 2px solid #f4c430;
        }
        
        /* تلوين نصوص القائمة الجانبية باللون الأبيض */
        [data-testid="stSidebar"] * {
            color: white !important;
        }

        /* العنوان الرئيسي */
        .main-title {
            text-align: center;
            color: #f4c430;
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 30px;
        }

        /* صندوق إدخال الرابط */
        div[data-testid="stTextInput"] input {
            background-color: #fff9e6 !important;
            color: #000 !important;
            border: 2px solid #f4c430 !important;
            border-radius: 8px;
            padding: 10px;
            font-size: 1.1rem;
        }
        
        /* تلوين عناوين الإدخال (اختر المنصة، الصق الرابط) باللون الأصفر */
        div[data-testid="stTextInput"] label, div[data-testid="stRadio"] label p {
            color: #f4c430 !important;
            font-weight: bold;
            font-size: 1.1rem;
        }

        /* الأزرار */
        .stButton>button {
            background-color: #f4c430;
            color: #0c1a3c;
            font-weight: bold;
            border-radius: 8px;
            border: none;
            width: 100%;
            transition: 0.3s;
        }
        .stButton>button:hover {
            background-color: white;
            color: #0c1a3c;
        }

        /* كروت التقارير الذكية */
        .report-card {
            background-color: white;
            color: #333;
            padding: 20px;
            border-radius: 10px;
            border-right: 5px solid #f4c430;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        
        /* ضبط نصوص التقارير لتكون داكنة وواضحة */
        .report-card h1, .report-card h2, .report-card h3, .report-card p, .report-card li {
            color: #333 !important;
        }
        </style>
    """, unsafe_allow_html=True)

apply_custom_theme()
# =====================================================================

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

# --- محركات السحب ---
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
        # 🌟 ترقية احترافية: إجبار الذكاء الاصطناعي على الرد بصيغة JSON برمجية
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
        ملاحظة: score هو تقييم لجودة المنتج من 0 إلى 100 بناءً على التعليقات.
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        
        # تنظيف الرد لتحويله إلى قاموس بايثون
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(raw_text)
    except Exception as e: return f"Error: {e}"

# --- الواجهة الرئيسية ---

# وضع الشعار في القائمة الجانبية بشكل نظيف ومرة واحدة فقط
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", width=120)
else:
    st.sidebar.markdown("🚀")

st.sidebar.title("رادار روفي")
page = st.sidebar.radio("انتقل إلى:", ["🚀 محرك التحليل السحابي", "📂 أرشيف التقارير"])

if not st.session_state.get("authenticated", False):
    st.markdown('<h1 class="main-title">🔐 دخول الإدارة | روفي</h1>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        pass_input = st.text_input("أدخل كلمة المرور السرية:", type="password")
        if st.button("فتح محرك روفي"):
            if pass_input == ACCESS_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة")
    st.stop()

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
                        st.write(f"✅ نجح الاختراق وجاري قراءة التعليقات وتوليد الذكاء البشري المساعد...")
                        # نغير اسم المتغير إلى report_data لأنه سيحتوي على معلومات مفصلة وليس مجرد نص
                        report_data = analyze_reviews(data, target_platform)
                        
                        # حفظ التقرير في الأرشيف
                        save_report_to_db(target_platform, url, str(report_data))
                        status.update(label="✅ اكتملت المهمة! إليك لوحة التحليل", state="complete")
                        
                        # 🌟 لوحة التحكم الاحترافية (Dashboard) 🌟
                        if isinstance(report_data, dict):
                            st.markdown("---")
                            st.markdown('<h2 style="text-align: center; color: #f4c430;">📊 لوحة التحليل الاستراتيجية</h2>', unsafe_allow_html=True)
                            
                            # 1. عرض مؤشر الجودة بشكل بصري
                            score = report_data.get("score", 0)
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                st.metric(label="مؤشر جودة المنتج (AI Score)", value=f"{score}%")
                                st.progress(score / 100.0)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            # 2. عرض المميزات والعيوب في أعمدة منفصلة ومنظمة
                            col_pros, col_cons = st.columns(2)
                            with col_pros:
                                st.success("✅ أبرز المميزات")
                                for p in report_data.get("pros", []):
                                    st.write(f"• {p}")
                                    
                            with col_cons:
                                st.error("❌ أبرز العيوب")
                                for c in report_data.get("cons", []):
                                    st.write(f"• {c}")
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            # 3. عرض النصيحة الذهبية للتاجر
                            st.info("💡 نصيحة روفي الاستراتيجية للمنافسة")
                            st.write(report_data.get("advice", ""))
                            
                        else:
                            # في حال فشل الذكاء الاصطناعي في التنسيق، يظهر كتقرير بسيط
                            st.markdown(f'<div class="report-card">{report_data}</div>', unsafe_allow_html=True)

                    elif data == "No_Reviews":
                        status.update(label="⚠️ عائق تقني", state="error")
                        st.warning("أمازون/نون أظهرت صفحة حماية. انظر للصورة أدناه لما واجهه الروبوت:")
                        if os.path.exists("debug.png"):
                            st.image("debug.png", caption="📸 لقطة استخباراتية حية")
                    else:
                        status.update(label="❌ فشل الرادار", state="error")
                        st.error(data)
elif page == "📂 أرشيف التقارير":
    st.markdown('<h1 class="main-title">📂 الأرشيف</h1>', unsafe_allow_html=True)
    saved_reports = get_all_reports()
    if saved_reports:
        for idx, (rep_platform, rep_url, rep_text, rep_date) in enumerate(saved_reports):
            with st.expander(f"📅 {rep_date} | {rep_platform}"):
                st.write(f"**الرابط:** {rep_url}")
                st.markdown(f'<div class="report-card">{rep_text}</div>', unsafe_allow_html=True)
    else:
        st.write("الأرشيف فارغ.")

# الفوتر السري النظيف
st.sidebar.markdown("---")
st.sidebar.markdown('<p style="text-align: center; color: rgba(255,255,255,0.5);">منصة روفي © 2026</p>', unsafe_allow_html=True)
