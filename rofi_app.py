import streamlit as st
import asyncio
import sys
import sqlite3
import os
from playwright.sync_api import sync_playwright
from google import genai

# 🌟 1. أمر عسكري للخادم: قم بتثبيت المتصفح فوراً قبل تشغيل الموقع 🌟
@st.cache_resource
def install_browsers():
    os.system("playwright install chromium")

install_browsers()

# 🛡️ حل مشكلة ويندوز (باقي هنا احتياطاً)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ================= الإعدادات السرية =================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
ACCESS_PASSWORD = "Rofi2026"
# ==================================================

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
            # 🌟 2. غيرناه إلى True لأن السحابة ليس بها شاشة عرض 🌟
            browser = p.chromium.launch(headless=True) 
            page = browser.new_page()
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.evaluate("window.scrollBy(0, 3000)")
            page.wait_for_timeout(3000)
            reviews = page.locator("span[data-hook='review-body']").all_inner_texts()
            browser.close()
            return reviews if reviews else "No_Reviews"
    except Exception as e: return f"Error: {e}"

def scrape_noon(url):
    try:
        with sync_playwright() as p:
            # 🌟 3. غيرناه إلى True هنا أيضاً 🌟
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception:
                pass
            page.wait_for_timeout(5000) 
            for _ in range(8):
                page.keyboard.press("PageDown") 
                page.wait_for_timeout(1500)     
            raw_texts = page.locator("p, span").all_inner_texts()
            browser.close()
            
            cleaned_reviews = []
            for text in raw_texts:
                t = text.strip().replace('\n', ' ')
                if 15 < len(t) < 800 and not any(word in t for word in ["ر.س", "SAR", "إضافة", "ريال", "خصم", "تسوق"]):
                    cleaned_reviews.append(t)
            
            cleaned_reviews = list(set(cleaned_reviews))
            if len(cleaned_reviews) > 0:
                return cleaned_reviews
            return "No_Reviews"
    except Exception as e: return f"Error: {e}"

def analyze_reviews(reviews_list, platform_name):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"أنت خبير أسواق. حلل تعليقات منتج من منصة ({platform_name}) السعودية لاستخراج: 1. العيوب 2. المميزات 3. نصيحة للتاجر للمنافسة: {' '.join(reviews_list)}"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e: return f"Error: {e}"

# --- الواجهة الرئيسية ---
st.set_page_config(page_title="منصة روفي | Rofi", page_icon="🚀", layout="wide")

if not st.session_state.get("authenticated", False):
    st.title("🔐 الدخول لمنصة روفي")
    if st.button("دخول") if st.text_input("أدخل كلمة المرور:", type="password") == ACCESS_PASSWORD else False:
        st.session_state.authenticated = True
        st.rerun()
    st.stop()

st.sidebar.title("🗂️ قائمة التحكم")
page = st.sidebar.radio("انتقل إلى:", ["الرئيسية (المحلل)", "تاريخ التقارير", "اتصل بنا"])

if page == "الرئيسية (المحلل)":
    st.title("🚀 محرك روفي للتحليل الذكي")
    
    target_platform = st.radio("اختر المنصة المستهدفة:", ["أمازون السعودية 🔵", "نون السعودية 🟡"], horizontal=True)
    url = st.text_input(f"🔗 رابط المنتج من {target_platform}:")
    
    if st.button("بدء التحليل"):
        with st.status(f"جاري إرسال رادار {target_platform}...") as status:
            if "أمازون" in target_platform:
                data = scrape_amazon(url)
            else:
                data = scrape_noon(url)
                
            if isinstance(data, list):
                st.write(f"✅ تم السحب من {target_platform}! جاري التحليل...")
                report = analyze_reviews(data, target_platform)
                save_report_to_db(target_platform, url, report)
                status.update(label="✅ اكتملت المهمة!", state="complete")
                st.markdown(report)
            elif data == "No_Reviews":
                status.update(label="⚠️ لم نجد تعليقات", state="error")
                st.warning("المتصفح فتح الصفحة، لكن لم يعثر على التعليقات. قد تكون مخفية أو أن المنتج بلا تقييمات.")
            else:
                status.update(label="❌ فشل السحب", state="error")
                st.error(data)

elif page == "تاريخ التقارير":
    st.title("📂 أرشيف تقاريرك الدائم")
    saved_reports = get_all_reports()
    if saved_reports:
        for idx, (rep_platform, rep_url, rep_text, rep_date) in enumerate(saved_reports):
            with st.expander(f"📅 {rep_date} | {rep_platform}"):
                st.write(f"**الرابط:** {rep_url}")
                st.markdown(rep_text)
    else:
        st.write("الأرشيف فارغ.")
