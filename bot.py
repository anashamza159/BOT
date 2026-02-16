#!/usr/bin/env python3
import os
import time
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

import config
from core.site_manager import SiteManager
from utils.helpers import load_accounts, save_accounts

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
user_sessions = {}
user_site_selection = {}
active_users = set()
site_manager = SiteManager()

# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    active_users.add(user_id)

    # Create buttons for all available sites
    sites = site_manager.list_sites()
    keyboard = []
    
    # Create buttons in rows of 2
    for i in range(0, len(sites), 2):
        row = []
        for site in sites[i:i+2]:
            row.append(InlineKeyboardButton(site.title(), callback_data=f"site_{site}"))
        keyboard.append(row)

    if not keyboard:
        await update.message.reply_text("❌ No sites available. Please add sites first.")
        return

    await update.message.reply_text(
        f"Hello {user_name}! 👋\n\nChoose a site and send a txt file (username:password).",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    user_sessions[user_id] = {"state": "choosing_site"}
    logger.info(f"User {user_id} started bot")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    site = query.data.split("_")[1]
    user_site_selection[user_id] = site
    user_sessions[user_id] = {"state": "waiting_file", "site": site}

    # Get checker for site info
    checker_class = site_manager.get_checker(site)
    checker = checker_class() if checker_class else None

    msg = f"✅ Selected {site.title()}.\n\n"
    msg += "Please send txt file with accounts (username:password format).\n\n"
    
    if checker:
        # Add site-specific info
        msg += f"💾 Saving criteria: {checker.__class__.__name__}\n"
        # You can add more specific info here
    
    await query.edit_message_text(msg)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions or user_sessions[user_id].get("state") != "waiting_file":
        await update.message.reply_text("❌ Please send /start first.")
        return

    site = user_sessions[user_id]["site"]
    document = update.message.document
    
    if not document.file_name.endswith(".txt"):
        await update.message.reply_text("❌ File must be .txt")
        return

    await update.message.reply_text("⏳ Downloading file...")
    
    # Download file
    file = await document.get_file()
    temp_file = f"accounts_{user_id}_{int(time.time())}.txt"
    await file.download_to_drive(temp_file)

    # Load accounts
    accounts = load_accounts(temp_file)
    if not accounts:
        await update.message.reply_text("❌ File empty or invalid")
        os.remove(temp_file)
        return

    # Get checker for this site
    checker_class = site_manager.get_checker(site)
    if not checker_class:
        await update.message.reply_text(f"❌ Checker not found for {site}")
        os.remove(temp_file)
        return

    # Process accounts
    await process_accounts(update, context, user_id, accounts, checker_class, temp_file)

async def process_accounts(update, context, user_id, accounts, checker_class, temp_file):
    """Generic account processing function"""
    total = len(accounts)
    stats = {"checked": 0, "valid": 0, "bad": 0, "error": 0, "saved": 0, "total": total}
    saved_accounts = []

    checker = checker_class()
    
    # Create initial message
    msg = await update.message.reply_text(
        f"🔍 Checking {total} {checker.name.title()} accounts...",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton("🔄 Starting...", callback_data="progress")
        )
    )

    # Process accounts
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        futures = []
        for acc in accounts:
            future = loop.run_in_executor(
                executor, 
                checker.check_account, 
                acc[0],  # username
                acc[1]   # password
            )
            futures.append(future)

        for i, future in enumerate(asyncio.as_completed(futures)):
            res = await future
            stats["checked"] += 1
            status = res.get("status", "bad")

            if status == "valid":
                stats["valid"] += 1
                if res.get("should_save", False):
                    stats["saved"] += 1
                    saved_accounts.append(res["account_data"])
            elif status == "bad":
                stats["bad"] += 1
            else:
                stats["error"] += 1

            # Update progress every 5 accounts or when done
            if stats["checked"] % 5 == 0 or stats["checked"] == total:
                try:
                    # Get keyboard from checker if available
                    if hasattr(checker, 'get_stats_keyboard'):
                        keyboard_data = checker.get_stats_keyboard(stats)
                        # Convert to InlineKeyboardMarkup
                        buttons = []
                        for row in keyboard_data.get("buttons", []):
                            btn_row = []
                            for btn in row:
                                btn_row.append(
                                    InlineKeyboardButton(
                                        btn["text"],
                                        callback_data=btn["callback_data"]
                                    )
                                )
                            buttons.append(btn_row)
                        reply_markup = InlineKeyboardMarkup(buttons)
                    else:
                        # Default keyboard
                        reply_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton(f"🔄 Checked: {stats['checked']}/{total}", callback_data="progress")],
                            [
                                InlineKeyboardButton(f"✅ Valid: {stats['valid']}", callback_data="valid"),
                                InlineKeyboardButton(f"❌ Bad: {stats['bad']}", callback_data="bad")
                            ],
                            [
                                InlineKeyboardButton(f"⚠️ Error: {stats['error']}", callback_data="error"),
                                InlineKeyboardButton(f"💾 Saved: {stats['saved']}", callback_data="saved")
                            ]
                        ])

                    progress_text = f"<b>Checking {checker.name.title()} accounts...</b>"
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=msg.message_id,
                        text=progress_text,
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error updating progress: {e}")

    # Save results
    if saved_accounts:
        output_file = save_accounts(saved_accounts, checker, user_id)
        
        if output_file:
            with open(output_file, "rb") as f:
                caption = f"🎉 <b>{checker.name.title()} Check Completed!</b>\n\n"
                caption += f"📊 Results:\n"
                caption += f"✅ Valid: {stats['valid']}\n"
                caption += f"❌ Bad: {stats['bad']}\n"
                caption += f"⚠️ Error: {stats['error']}\n"
                caption += f"💾 Saved: {len(saved_accounts)}\n\n"
                caption += f"📁 File contains {len(saved_accounts)} saved accounts."
                
                await update.message.reply_document(
                    document=f,
                    filename=f"{checker.name}_results_{user_id}_{int(time.time())}.txt",
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
            
            # Cleanup
            try:
                os.remove(output_file)
                folder = f"{checker.name}_results_{user_id}"
                if os.path.exists(folder) and not os.listdir(folder):
                    os.rmdir(folder)
            except:
                pass
    else:
        await update.message.reply_text(
            f"⚠️ No accounts saved.\n\n"
            f"📊 Results:\n"
            f"✅ Valid: {stats['valid']}\n"
            f"❌ Bad: {stats['bad']}\n"
            f"⚠️ Error: {stats['error']}\n\n"
            f"Note: Only accounts meeting the criteria are saved."
        )

    # Cleanup temp file
    os.remove(temp_file)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != config.ADMIN_ID:
        await update.message.reply_text("❌ Admin only command")
        return
    
    sites = site_manager.list_sites()
    text = f"📊 Bot Statistics\n\n"
    text += f"Active Users: {len(active_users)}\n"
    text += f"Sessions: {len(user_sessions)}\n"
    text += f"Available Sites: {len(sites)}\n\n"
    text += f"Sites:\n"
    
    for site in sites:
        text += f"• {site.title()}\n"
    
    await update.message.reply_text(text)

async def list_sites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to list all available sites"""
    sites = site_manager.list_sites()
    
    if not sites:
        await update.message.reply_text("❌ No sites available.")
        return
    
    text = "📋 Available Sites:\n\n"
    for site in sites:
        text += f"• {site.title()}\n"
    
    await update.message.reply_text(text)

def main():
    """Start the bot"""
    # Initialize site manager
    global site_manager
    site_manager = SiteManager()
    
    print("✅ Account Checker Bot")
    print(f"🌐 Loaded {len(site_manager.list_sites())} sites")
    
    for site in site_manager.list_sites():
        print(f"   • {site.title()}")
    
    # Create bot application
    app = Application.builder().token(config.TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sites", list_sites_command))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    print("\n🤖 Bot is running...")
    print("📝 Commands: /start, /sites, /stats")
    
    # Start polling
    app.run_polling()

if __name__ == "__main__":
    main()