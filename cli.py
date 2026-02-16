#!/usr/bin/env python3
"""
CLI Tool for managing account checker sites
"""
import sys
import os
import shutil
from pathlib import Path
import importlib.util

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.site_manager import SiteManager
import config

def print_banner():
    """Print CLI banner"""
    banner = """
    ┌─────────────────────────────────────┐
    │    Account Checker Site Manager     │
    └─────────────────────────────────────┘
    """
    print(banner)

def add_site():
    """Add a new site via CLI"""
    print("\n➕ Add New Site")
    print("-" * 40)
    
    site_name = input("Site name (e.g., 'example'): ").strip().lower()
    
    if not site_name:
        print("❌ Site name is required")
        return
    
    # Check if site already exists
    manager = SiteManager()
    if site_name in manager.list_sites():
        print(f"❌ Site '{site_name}' already exists")
        return
    
    # Get site URLs
    print("\n🌐 Enter site URLs:")
    login_url = input("Login URL: ").strip()
    profile_url = input("Profile URL (optional): ").strip()
    wallet_url = input("Wallet/Balance URL (optional): ").strip()
    
    # Get headers
    print("\n📋 Enter headers (JSON format, leave empty for default):")
    headers_input = input("Headers: ").strip()
    
    # Get saving conditions
    print("\n💾 Saving conditions:")
    print("Available variables: kyc_status, balance, deposited_before, etc.")
    condition = input("Save if (e.g., 'kyc_status and deposited_before'): ").strip()
    
    # Create site file
    template_path = config.SITES_DIR / "template.py"
    new_site_path = config.SITES_DIR / f"{site_name}.py"
    
    # Read template
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Replace placeholders
    content = template_content.replace('TemplateChecker', f'{site_name.title()}Checker')
    content = content.replace('"https://example.com/api/login"', f'"{login_url}"')
    
    if profile_url:
        content = content.replace('"https://example.com/api/profile"', f'"{profile_url}"')
    
    if wallet_url:
        content = content.replace('"https://example.com/api/wallet"', f'"{wallet_url}"')
    
    # Update should_save method
    if condition:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'def should_save' in line:
                # Find the next return statement
                for j in range(i, len(lines)):
                    if 'return' in lines[j]:
                        lines[j] = f'        return {condition}'
                        break
                break
        content = '\n'.join(lines)
    
    # Write new site file
    with open(new_site_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ Site '{site_name}' added successfully!")
    print(f"📁 File created: {new_site_path}")
    print("\n⚠️  You need to edit the check_account() method to implement the actual checking logic.")

def list_sites():
    """List all available sites"""
    manager = SiteManager()
    sites = manager.list_sites()
    
    print("\n📋 Available Sites:")
    print("-" * 40)
    
    if not sites:
        print("No sites available. Use 'add' to create one.")
        return
    
    for i, site in enumerate(sites, 1):
        checker = manager.get_checker(site)
        if checker:
            print(f"{i}. {site.title()} - {checker.__name__}")
        else:
            print(f"{i}. {site.title()}")

def remove_site():
    """Remove a site"""
    manager = SiteManager()
    sites = manager.list_sites()
    
    if not sites:
        print("❌ No sites available to remove")
        return
    
    print("\n🗑️  Remove Site")
    print("-" * 40)
    
    for i, site in enumerate(sites, 1):
        print(f"{i}. {site}")
    
    try:
        choice = int(input("\nSelect site number to remove: ")) - 1
        if 0 <= choice < len(sites):
            site_name = sites[choice]
            site_path = config.SITES_DIR / f"{site_name}.py"
            
            if site_path.exists():
                os.remove(site_path)
                print(f"✅ Site '{site_name}' removed successfully!")
            else:
                print(f"❌ Site file not found: {site_path}")
        else:
            print("❌ Invalid choice")
    except ValueError:
        print("❌ Please enter a valid number")

def test_site():
    """Test a site checker"""
    manager = SiteManager()
    sites = manager.list_sites()
    
    if not sites:
        print("❌ No sites available to test")
        return
    
    print("\n🧪 Test Site Checker")
    print("-" * 40)
    
    for i, site in enumerate(sites, 1):
        print(f"{i}. {site}")
    
    try:
        choice = int(input("\nSelect site number to test: ")) - 1
        if 0 <= choice < len(sites):
            site_name = sites[choice]
            checker_class = manager.get_checker(site_name)
            
            if checker_class:
                print(f"\nTesting {site_name.title()}Checker...")
                
                # Test with dummy account
                username = input("Test username (or press Enter for dummy): ").strip() or "test@example.com"
                password = input("Test password (or press Enter for dummy): ").strip() or "password123"
                
                checker = checker_class()
                result = checker.check_account(username, password)
                
                print(f"\n📊 Test Result:")
                print(f"Status: {result.get('status')}")
                print(f"Should Save: {result.get('should_save', False)}")
                
                if 'account_data' in result:
                    print(f"\nAccount Data:")
                    for key, value in result['account_data'].items():
                        print(f"  {key}: {value}")
            else:
                print(f"❌ Checker not found for {site_name}")
        else:
            print("❌ Invalid choice")
    except ValueError:
        print("❌ Please enter a valid number")
    except Exception as e:
        print(f"❌ Error during test: {e}")

def show_help():
    """Show CLI help"""
    help_text = """
📖 CLI Commands:
    
    add     - Add a new site checker
    list    - List all available sites
    remove  - Remove a site checker
    test    - Test a site checker
    help    - Show this help message
    exit    - Exit the CLI
    
Examples:
    python cli.py add      # Interactive site creation
    python cli.py list     # Show all sites
    python cli.py test     # Test a site checker
    """
    print(help_text)

def main():
    """Main CLI entry point"""
    print_banner()
    
    commands = {
        'add': add_site,
        'list': list_sites,
        'remove': remove_site,
        'test': test_site,
        'help': show_help,
    }
    
    while True:
        try:
            print("\n" + "═" * 40)
            command = input("\nEnter command (add/list/remove/test/help/exit): ").strip().lower()
            
            if command == 'exit':
                print("\n👋 Goodbye!")
                break
            
            if command in commands:
                commands[command]()
            else:
                print(f"❌ Unknown command: {command}")
                print("Type 'help' for available commands")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Command line arguments
        command = sys.argv[1].lower()
        if command in ['add', 'list', 'remove', 'test']:
            # Direct command execution
            print_banner()
            if command == 'add':
                add_site()
            elif command == 'list':
                list_sites()
            elif command == 'remove':
                remove_site()
            elif command == 'test':
                test_site()
        elif command == 'help':
            show_help()
        else:
            print(f"❌ Unknown command: {command}")
            show_help()
    else:
        # Interactive mode
        main()