"""
╔══════════════════════════════════════════════╗
║       🌸 SKINCARE ROUTINE BOT 🌸             ║
║   Bot nhắc skincare đúng theo routine        ║
╚══════════════════════════════════════════════╝

CÀI ĐẶT:
  pip install python-telegram-bot apscheduler pytz

CHẠY:
  python skincare_bot.py

ĐIỀN VÀO:
  BOT_TOKEN  = token lấy từ @BotFather
  CHAT_ID    = chat_id của bạn (nhắn /start để xem)
"""

import os
import asyncio
import logging
from datetime import datetime
import pytz

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ══════════════════════════════════════════════
#  ⚙️  CẤU HÌNH
# ══════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "DIEN_TOKEN_CUA_BAN_VAO_DAY")
CHAT_ID   = os.getenv("CHAT_ID",   "DIEN_CHAT_ID_CUA_BAN_VAO_DAY")
TIMEZONE  = "Asia/Ho_Chi_Minh"

# Thứ 3, 5, 7 → Python weekday: 1, 3, 5
TRETINOIN_DAYS = {1, 3, 5}
# Thứ 2, 4, 6, CN → Python weekday: 0, 2, 4, 6
APAD_DAYS = {0, 2, 4, 6}

# ══════════════════════════════════════════════
#  🌅  ROUTINE SÁNG (mọi ngày – 7:00)
#  Đúng theo ảnh: SRM → Toner → B-Bomb → AzeMIX
# ══════════════════════════════════════════════
MORNING_STEPS = [
    {
        "step": 1,
        "emoji": "🧼",
        "name": "Sữa rửa mặt (SRM)",
        "detail": "Rửa mặt nhẹ nhàng, massage 60 giây rồi xả sạch với nước ấm.",
        "wait_min": 2,
        "wait_msg": "⏳ Thấm khô mặt bằng khăn sạch, chờ mặt ráo (~2 phút)..."
    },
    {
        "step": 2,
        "emoji": "💧",
        "name": "Toner Caryophy",
        "detail": "Thấm toner ra bông cotton hoặc vỗ nhẹ bằng tay lên toàn mặt.",
        "wait_min": 2,
        "wait_msg": "⏳ Chờ toner thấm vào da (~2 phút)..."
    },
    {
        "step": 3,
        "emoji": "✨",
        "name": "B-Bomb Serum (IOI)",
        "detail": "Lấy 3–4 giọt, vỗ nhẹ lên toàn mặt.",
        "wait_min": 3,
        "wait_msg": "⏳ Chờ serum thấm (~3 phút)..."
    },
    {
        "step": 4,
        "emoji": "🌿",
        "name": "AzeMIX Gel",
        "detail": "Lấy lượng bằng hạt đậu, trải đều lên toàn mặt. Xong rồi ra ngoài thôi! ☀️",
        "wait_min": 0,
        "wait_msg": ""
    },
]

# ══════════════════════════════════════════════
#  🌙  ROUTINE TỐI – NGÀY TRETINOIN (3, 5, 7) – 21:30
#  Đúng theo ảnh: Tẩy trang → SRM → Toner → B5 → Tretinoin
# ══════════════════════════════════════════════
TRETINOIN_STEPS = [
    {
        "step": 1,
        "emoji": "🧴",
        "name": "Tẩy trang",
        "detail": "Dùng tẩy trang dạng dầu hoặc micellar water, lau nhẹ nhàng toàn mặt đến sạch.",
        "wait_min": 1,
        "wait_msg": "⏳ Rửa lại mặt với nước sạch, thấm khô..."
    },
    {
        "step": 2,
        "emoji": "🧼",
        "name": "Sữa rửa mặt (SRM)",
        "detail": "Làm sạch lần 2, massage nhẹ 60 giây. Xả sạch với nước mát.",
        "wait_min": 20,
        "wait_msg": "⏳ QUAN TRỌNG: Thấm khô và chờ mặt khô hoàn toàn 20 phút trước khi bôi Tretinoin!\nDa ướt hấp thụ mạnh hơn → dễ kích ứng!"
    },
    {
        "step": 3,
        "emoji": "💧",
        "name": "Toner Caryophy",
        "detail": "Vỗ nhẹ toner lên mặt.",
        "wait_min": 3,
        "wait_msg": "⏳ Chờ toner thấm (~3 phút)..."
    },
    {
        "step": 4,
        "emoji": "💊",
        "name": "Panthenol B5 Ampoule",
        "detail": "Vỗ nhẹ B5 ampoule lên toàn mặt. B5 giúp phục hồi và làm dịu da.",
        "wait_min": 3,
        "wait_msg": "⏳ Chờ B5 thấm (~3 phút)..."
    },
    {
        "step": 5,
        "emoji": "⭐",
        "name": "Tretinoin (Micro-RET)",
        "detail": (
            "Lấy lượng bằng HẠT ĐẬU (~0.5cm) cho toàn mặt.\n"
            "• Trải mỏng đều, tránh khóe mắt, khóe miệng, cánh mũi\n"
            "• Bôi nhiều KHÔNG hiệu quả hơn, chỉ kích ứng thêm\n"
            "• Xong rồi đi ngủ thôi 🌙"
        ),
        "wait_min": 0,
        "wait_msg": ""
    },
]

# ══════════════════════════════════════════════
#  🌙  ROUTINE TỐI – NGÀY APAD (2, 4, 6, CN) – 21:30
#  Đúng theo ảnh: Tẩy trang → SRM → Toner → aPAD → AzeMIX
# ══════════════════════════════════════════════
APAD_STEPS = [
    {
        "step": 1,
        "emoji": "🧴",
        "name": "Tẩy trang",
        "detail": "Dùng tẩy trang dạng dầu hoặc micellar water, lau nhẹ nhàng toàn mặt.",
        "wait_min": 1,
        "wait_msg": "⏳ Rửa lại mặt với nước sạch, thấm khô..."
    },
    {
        "step": 2,
        "emoji": "🧼",
        "name": "Sữa rửa mặt (SRM)",
        "detail": "Làm sạch lần 2, massage nhẹ 60 giây. Xả sạch.",
        "wait_min": 2,
        "wait_msg": "⏳ Thấm khô mặt (~2 phút)..."
    },
    {
        "step": 3,
        "emoji": "💧",
        "name": "Toner Caryophy",
        "detail": "Vỗ nhẹ toner lên mặt.",
        "wait_min": 3,
        "wait_msg": "⏳ Chờ toner thấm (~3 phút)..."
    },
    {
        "step": 4,
        "emoji": "🔬",
        "name": "aPAD Serum (Azelaic 20%)",
        "detail": "Lấy 3–4 giọt, vỗ nhẹ lên toàn mặt.",
        "wait_min": 5,
        "wait_msg": "⏳ Chờ aPAD thấm (~5 phút)..."
    },
    {
        "step": 5,
        "emoji": "🌿",
        "name": "AzeMIX Gel",
        "detail": (
            "Lấy lượng bằng hạt đậu, trải đều lên toàn mặt.\n"
            "Xong rồi đi ngủ thôi 🌙"
        ),
        "wait_min": 0,
        "wait_msg": ""
    },
]

# ══════════════════════════════════════════════
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
user_sessions: dict = {}


def get_day_name(weekday: int) -> str:
    names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    return names[weekday]


def get_tonight_routine() -> tuple[str, list]:
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).weekday()
    if today in TRETINOIN_DAYS:
        return "tretinoin", TRETINOIN_STEPS
    else:
        return "apad", APAD_STEPS


def build_step_message(step_data: dict, step_idx: int, total: int) -> str:
    progress = "".join(["🟢" if i <= step_idx else "⚪" for i in range(total)])
    return (
        f"{progress}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Bước {step_data['step']}/{total}  {step_data['emoji']} *{step_data['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{step_data['detail']}\n"
    )


# ──────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text(
        f"🌸 *SKINCARE ROUTINE BOT* 🌸\n\n"
        f"Chat ID của bạn: `{chat_id}`\n\n"
        f"📌 *Lệnh:*\n"
        f"• /sang – Routine sáng ngay\n"
        f"• /toi – Routine tối ngay\n"
        f"• /lichhomnay – Hôm nay dùng gì\n\n"
        f"⏰ Bot tự nhắc:\n"
        f"• *7:00* – Routine sáng\n"
        f"• *21:30* – Routine tối\n\n"
        f"_Dán chat\\_id này vào CHAT\\_ID trong code nhé!_",
        parse_mode="Markdown"
    )


async def cmd_lich_hom_nay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).weekday()
    day_name = get_day_name(today)
    routine_type, _ = get_tonight_routine()

    if routine_type == "tretinoin":
        icon, ten = "⭐", "Tretinoin"
        buoc_toi = "Tẩy trang → SRM → Toner → B5 → Tretinoin"
    else:
        icon, ten = "🔬", "aPAD + AzeMIX"
        buoc_toi = "Tẩy trang → SRM → Toner → aPAD → AzeMIX"

    await update.message.reply_text(
        f"📅 Hôm nay *{day_name}*\n\n"
        f"🌅 *Sáng:*\n"
        f"SRM → Toner → B\\-Bomb → AzeMIX\n\n"
        f"🌙 *Tối:* {icon} *{ten}*\n"
        f"_{buoc_toi}_\n\n"
        f"Dùng /sang hoặc /toi để bắt đầu!",
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────────
async def start_routine(chat_id: str, steps: list, title: str, bot: Bot):
    user_sessions[chat_id] = {"steps": steps, "current": 0, "title": title}
    total = len(steps)
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%H:%M")

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"{'🌅' if 'SÁNG' in title else '🌙'} *{title}*\n"
            f"🕐 Bắt đầu lúc {now}\n"
            f"📋 Tổng cộng {total} bước\n\n"
            f"_Bấm ✅ sau mỗi bước để tiến lên nhé!_"
        ),
        parse_mode="Markdown"
    )
    await asyncio.sleep(1)
    await send_step(chat_id, 0, bot)


async def send_step(chat_id: str, step_idx: int, bot: Bot):
    session = user_sessions.get(chat_id)
    if not session:
        return

    steps = session["steps"]
    total = len(steps)

    if step_idx >= total:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🎉 *HOÀN TẤT ROUTINE!* 🎉\n\n"
                "✨ Da bạn đã được chăm sóc đầy đủ!\n"
                "💤 Ngủ ngon nha~\n\n"
                "🌸 _Kiên trì là chìa khoá!_"
            ),
            parse_mode="Markdown"
        )
        user_sessions.pop(chat_id, None)
        return

    step = steps[step_idx]
    msg = build_step_message(step, step_idx, total)
    keyboard = [[InlineKeyboardButton("✅ Xong rồi!", callback_data=f"done_{step_idx}")]]

    await bot.send_message(
        chat_id=chat_id,
        text=msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def callback_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat_id)
    step_idx = int(query.data.split("_")[1])

    session = user_sessions.get(chat_id)
    if not session:
        await query.edit_message_reply_markup(reply_markup=None)
        return

    step = session["steps"][step_idx]

    await query.edit_message_reply_markup(reply_markup=None)
    await query.edit_message_text(
        text=query.message.text + "\n\n✅ *Đã hoàn thành!*",
        parse_mode="Markdown"
    )

    wait_min = step.get("wait_min", 0)
    if wait_min > 0 and step.get("wait_msg"):
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=step["wait_msg"],
            parse_mode="Markdown"
        )
        await asyncio.sleep(wait_min * 60)
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ *{wait_min} phút đã qua!* Tiếp tục bước tiếp theo nào~ 👇",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)

    await send_step(chat_id, step_idx + 1, ctx.bot)


# ──────────────────────────────────────────────
async def cmd_sang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    tz = pytz.timezone(TIMEZONE)
    day_name = get_day_name(datetime.now(tz).weekday())
    await start_routine(chat_id, MORNING_STEPS, f"ROUTINE SÁNG – {day_name}", ctx.bot)


async def cmd_toi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    tz = pytz.timezone(TIMEZONE)
    day_name = get_day_name(datetime.now(tz).weekday())
    routine_type, steps = get_tonight_routine()
    label = "TRETINOIN" if routine_type == "tretinoin" else "aPAD + AzeMIX"
    await start_routine(chat_id, steps, f"ROUTINE TỐI {label} – {day_name}", ctx.bot)


# ──────────────────────────────────────────────
#  ⏰  TỰ ĐỘNG NHẮC ĐÚNG GIỜ
# ──────────────────────────────────────────────
async def scheduled_morning(bot: Bot):
    tz = pytz.timezone(TIMEZONE)
    day_name = get_day_name(datetime.now(tz).weekday())
    await bot.send_message(
        chat_id=CHAT_ID,
        text=(
            f"☀️ *Chào buổi sáng {day_name}!*\n\n"
            f"🌅 Hôm nay: SRM → Toner → B\\-Bomb → AzeMIX\n\n"
            f"Dùng /sang để bắt đầu nhé 🌸"
        ),
        parse_mode="Markdown"
    )


async def scheduled_evening(bot: Bot):
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).weekday()
    day_name = get_day_name(today)
    routine_type, _ = get_tonight_routine()

    if routine_type == "tretinoin":
        icon = "⭐"
        buoc = "Tẩy trang → SRM → Toner → B5 → Tretinoin"
    else:
        icon = "🔬"
        buoc = "Tẩy trang → SRM → Toner → aPAD → AzeMIX"

    await bot.send_message(
        chat_id=CHAT_ID,
        text=(
            f"🌙 *Tối {day_name} rồi!*\n\n"
            f"{icon} Hôm nay:\n"
            f"_{buoc}_\n\n"
            f"Dùng /toi để bắt đầu nhé 💆"
        ),
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("sang",       cmd_sang))
    app.add_handler(CommandHandler("toi",        cmd_toi))
    app.add_handler(CommandHandler("lichhomnay", cmd_lich_hom_nay))
    app.add_handler(CallbackQueryHandler(callback_done, pattern=r"^done_\d+$"))

    tz = pytz.timezone(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(scheduled_morning, "cron", hour=7,  minute=0,  args=[app.bot])
    scheduler.add_job(scheduled_evening, "cron", hour=21, minute=30, args=[app.bot])
    scheduler.start()

    logger.info("🌸 Skincare Bot đang chạy...")
    app.run_polling()


if __name__ == "__main__":
    main()
