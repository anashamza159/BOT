import os
import json
from datetime import datetime
from typing import List, Tuple, Dict, Any  # أضف الأنواع المطلوبة
from core.base_checker import BaseChecker

def load_accounts(file_path: str) -> List[Tuple[str, str]]:
    """Load accounts from file"""
    accounts = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if ':' in line:
                    # Handle username:password format
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        username, password = parts
                        accounts.append((username.strip(), password.strip()))
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return accounts

def save_accounts(accounts_data: List[Dict[str, Any]], checker: BaseChecker, user_id: int) -> str:
    """Save accounts to file"""
    try:
        # Create results directory
        os.makedirs("results", exist_ok=True)
        output_dir = f"results/{checker.name}_results_{user_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"{checker.name}_results_{timestamp}.txt")
        
        # Save accounts using checker's format
        with open(output_file, "w", encoding="utf-8") as f:
            for account in accounts_data:
                f.write(checker.save_format(account))
        
        print(f"📁 Saved {len(accounts_data)} accounts to {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Error saving accounts: {e}")
        return None

def create_site_template(site_name: str, config: Dict[str, Any]) -> str:
    """Create a new site checker template"""
    template = f'''
from core.base_checker import BaseChecker
from typing import Dict, Any
import requests

class {site_name.title()}Checker(BaseChecker):
    """{site_name.title()} site checker"""
    
    LOGIN_URL = "{config.get('login_url', '')}"
    PROFILE_URL = "{config.get('profile_url', '')}"
    WALLET_URL = "{config.get('wallet_url', '')}"
    
    HEADERS = {json.dumps(config.get('headers', {{}}), indent=4)}
    
    def check_account(self, username: str, password: str) -> Dict[str, Any]:
        """Check single account"""
        try:
            # TODO: Implement account checking logic
            # Example:
            payload = {{
                "username": username,
                "password": password
            }}
            
            response = self.session.post(
                self.LOGIN_URL,
                json=payload,
                headers=self.HEADERS,
                timeout=30
            )
            
            if response.status_code != 200:
                return {{"status": "bad", "username": username}}
            
            data = response.json()
            
            # TODO: Add your validation logic here
            account_data = {{
                "login": username,
                "password": password,
                "balance": 0,
                # Add more fields as needed
            }}
            
            return {{
                "status": "valid",
                "account_data": account_data,
                "should_save": self.should_save(account_data)
            }}
            
        except Exception as e:
            return {{"status": "error", "username": username, "error": str(e)}}
    
    def should_save(self, account_data: Dict[str, Any]) -> bool:
        """Define saving conditions"""
        # TODO: Define when to save accounts
        # Example: return account_data.get("balance", 0) > 0
        return False
    
    def save_format(self, account_data: Dict[str, Any]) -> str:
        """Format for saving accounts"""
        return f"{{account_data['login']}}:{{account_data['password']}}\\n"
'''
    return template