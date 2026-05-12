import asyncio
import logging
import os
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, FSInputFile, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery
)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# ==================== SOZLAMALAR ====================
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8653151262:AAGl4mNfcA2Qvd8zpn8d79IOhlDLohh1XfQ"
GROUP_ID = -1003918988982

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ==================== TRANSLITERATSIYA ====================
TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
    'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    'ў': "o'", 'ғ': "g'", 'қ': 'q', 'ҳ': 'h',
    'Ў': "O'", 'Ғ': "G'", 'Қ': 'Q', 'Ҳ': 'H'
}

def transliterate(text: str) -> str:
    """Kirill harflarini lotin harflariga o'giradi"""
    return ''.join(TRANSLIT_MAP.get(c, c) for c in str(text))

def safe(text) -> str:
    """PDF uchun xavfsiz matn"""
    return transliterate(str(text)) if text else "---"

def sanitize_filename(filename: str) -> str:
    """Fayl nomini xavfsiz qiladi"""
    filename = transliterate(filename)
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = filename.strip().replace(' ', '_')
    if not filename:
        filename = "unknown"
    return filename[:50]

# ==================== SAVOLLAR ====================
questions = [
    "Ismingiz va familiyangiz?",
    "Tug'ilgan yilingiz?",
    "Telefon raqamingiz va Telegram usernameingiz?",
    "Qaysi shaharda/tumanda yashaysiz?",
    "Ma'lumotingiz va oilangiz haqida ma'lumot?",
    "Selfi rasmingizni yuboring (foto):",
    "Biz taklif qilgan ishda qancha vaqt ishlay olasiz?",
    "Qachondan ish boshlay olasiz?",
    "Mutaxassisligingiz?",
    "Qayerlarda ishlagansiz va qanday lavozimlarda?",
    "Qancha vaqt ishlagansiz va ishdan bo'shashingiz sababi?",
    "Ota-onangizning kasbi va faoliyati haqida ma'lumot bering?",
    "Qaysi tillarni bilasiz?",
    "Ko'rsatilgan ish vaqti sizga mos keladimi (10:00 dan 20:00)?",
    "Taqdim etilgan oylik maosh sizga maqulmi (6 000 000 dan boshlanadi)?"
]

# ==================== STATES ====================
class Questionnaire(StatesGroup):
    q1  = State()
    q2  = State()
    q3  = State()
    q4  = State()
    q5  = State()
    q6  = State()
    q7  = State()
    q8  = State()
    q9  = State()
    q10 = State()
    q11 = State()
    q12 = State()
    q13 = State()
    q14 = State()
    q15 = State()

STATES = [
    Questionnaire.q1,  Questionnaire.q2,  Questionnaire.q3,
    Questionnaire.q4,  Questionnaire.q5,  Questionnaire.q6,
    Questionnaire.q7,  Questionnaire.q8,  Questionnaire.q9,
    Questionnaire.q10, Questionnaire.q11, Questionnaire.q12,
    Questionnaire.q13, Questionnaire.q14, Questionnaire.q15,
]

# ==================== PDF YARATISH ====================
def draw_wrapped_text(c, text, x, y, max_width, font, size, line_height=15):
    """Uzun matnni qatorlarga bo'lib chizadi, yangi y qaytaradi"""
    c.setFont(font, size)
    words = text.split()
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if c.stringWidth(test, font, size) <= max_width:
            line = test
        else:
            c.drawString(x, y, line)
            y -= line_height
            line = word
    if line:
        c.drawString(x, y, line)
        y -= line_height
    return y

def create_pdf(answers: dict, username: str, user_id: int) -> str:
    raw_name = answers.get("q1", "unknown")
    safe_name = sanitize_filename(raw_name)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_name}_{timestamp}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    margin = 45
    max_width = width - margin * 2 - 15

    def new_page():
        c.showPage()
        return height - 50

    # --- HEADER ---
    c.setFillColor(colors.HexColor("#1a1a2e"))
    c.rect(0, height - 75, width, 75, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 40, "SMART+ ANKETA")

    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 58,
                        f"Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  ID: {user_id}  |  @{username}")

    y = height - 100

    for i, question in enumerate(questions):
        key = f"q{i + 1}"
        answer_raw = answers.get(key, "---")

        # Selfie uchun maxsus
        if key == "q6" and str(answer_raw).startswith("Photo:"):
            answer_text = "[Selfi yuborilgan]"
        else:
            answer_text = safe(answer_raw)

        question_text = safe(question)

        # Sahifa tugasa yangi sahifa
        if y < 100:
            y = new_page()

        # Savol
        c.setFillColor(colors.HexColor("#1a1a2e"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, f"{i + 1}. {question_text}")
        y -= 18

        # Javob
        c.setFillColor(colors.HexColor("#333333"))
        y = draw_wrapped_text(c, answer_text, margin + 10, y, max_width,
                              "Helvetica", 10, line_height=15)

        # Chiziq
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.line(margin, y, width - margin, y)
        y -= 12

    # --- FOOTER ---
    c.setFillColor(colors.HexColor("#1a1a2e"))
    c.rect(0, 0, width, 35, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, 12, "SMART+  |  Halollik foydadan ustun")

    c.save()
    return filename

# ==================== ANKETA TUGASH ====================
async def finish_questionnaire(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", {})
    username = message.from_user.username or "noname"
    user_id = message.from_user.id

    await message.answer("✅ Anketa qabul qilindi! PDF tayyorlanmoqda...")

    try:
        filename = create_pdf(answers, username, user_id)

        # Foydalanuvchiga yuborish
        pdf_file = FSInputFile(filename)
        await message.answer_document(pdf_file, caption="📄 Sizning anketangiz PDF ko'rinishida.")

        # Guruhga yuborish (selfie bilan)
        selfie_id = None
        for key, val in answers.items():
            if str(val).startswith("Photo:"):
                selfie_id = str(val).replace("Photo: ", "").strip()
                break

        caption = (
            f"📋 Yangi anketa!\n"
            f"👤 @{username} (ID: {user_id})\n"
            f"👤 Ism: {answers.get('q1', '---')}\n"
            f"📞 Tel: {answers.get('q3', '---')}"
        )

        if selfie_id:
            await bot.send_photo(GROUP_ID, photo=selfie_id, caption=caption)

        pdf_file2 = FSInputFile(filename)
        await bot.send_document(GROUP_ID, document=pdf_file2, caption="📄 To'liq anketa PDF")

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("❌ PDF yaratishda xato yuz berdi. Admin bilan bog'laning.")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
        await state.clear()

# ==================== UMUMIY JAVOB QAYTA ISHLASH ====================
async def process_answer(message: Message, state: FSMContext, index: int):
    data = await state.get_data()
    answers = data.get("answers", {})

    if message.photo:
        answers[f"q{index + 1}"] = f"Photo: {message.photo[-1].file_id}"
    else:
        answers[f"q{index + 1}"] = message.text or "---"

    await state.update_data(answers=answers)

    next_index = index + 1
    if next_index < len(questions):
        await state.set_state(STATES[next_index])
        await message.answer(questions[next_index])
    else:
        await finish_questionnaire(message, state)

# ==================== START ====================
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    text = (
        "SMART+ — telefonlar, telefon aksessuarlari va ehtiyot qismlarining "
        "ulgurji savdosi bilan shug'ullanuvchi ishonchli kompaniya hisoblanadi.\n\n"
        "Biz bozorda sifatli mahsulotlar va barqaror hamkorlik orqali o'z o'rnimizni "
        "mustahkamlab kelmoqdamiz. Bugungi kunda kompaniyamizning 9 ta filiali faoliyat "
        "yuritib, mijozlarimizga tezkor va qulay xizmat ko'rsatishni ta'minlamoqda.\n\n"
        "Kompaniyamiz asoschisi — Samanov Bobur.\n\n"
        "Bizning asosiy maqsadlarimiz:\n"
        "— Yangi ish o'rinlari yaratish\n"
        "— Mijozlarga yuqori sifatli xizmat ko'rsatish\n"
        "— O'zbekiston rivojiga o'z hissamizni qo'shish\n\n"
        "SMART+ shiori: \"Halollik foydadan ustun\""
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 ANKETANI TO'LDIRISH", callback_data="start_questionnaire")]
    ])

    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "logo.png")

    if os.path.exists(logo_path):
        try:
            await message.answer_photo(FSInputFile(logo_path), caption=text, reply_markup=keyboard)
            return
        except Exception as e:
            logging.warning(f"Logo yuborishda xato: {e}")

    await message.answer(text, reply_markup=keyboard)

# ==================== ANKETA BOSHLASH ====================
@router.callback_query(F.data == "start_questionnaire")
async def start_questionnaire(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(answers={})

    try:
        await callback.message.edit_caption(caption="Anketa boshlandi!", reply_markup=None)
    except Exception:
        try:
            await callback.message.edit_text("Anketa boshlandi!", reply_markup=None)
        except Exception:
            pass

    await state.set_state(STATES[0])
    await callback.message.answer(questions[0])
    await callback.answer()

# ==================== SAVOLLAR HANDLERLARI ====================
@router.message(Questionnaire.q1)
async def q1(message: Message, state: FSMContext):
    await process_answer(message, state, 0)

@router.message(Questionnaire.q2)
async def q2(message: Message, state: FSMContext):
    await process_answer(message, state, 1)

@router.message(Questionnaire.q3)
async def q3(message: Message, state: FSMContext):
    await process_answer(message, state, 2)

@router.message(Questionnaire.q4)
async def q4(message: Message, state: FSMContext):
    await process_answer(message, state, 3)

@router.message(Questionnaire.q5)
async def q5(message: Message, state: FSMContext):
    await process_answer(message, state, 4)

@router.message(Questionnaire.q6, F.photo)
async def q6_photo(message: Message, state: FSMContext):
    await process_answer(message, state, 5)

@router.message(Questionnaire.q6)
async def q6_not_photo(message: Message, state: FSMContext):
    await message.answer("⚠️ Iltimos, selfi rasmingizni yuboring (matn emas, foto).")

@router.message(Questionnaire.q7)
async def q7(message: Message, state: FSMContext):
    await process_answer(message, state, 6)

@router.message(Questionnaire.q8)
async def q8(message: Message, state: FSMContext):
    await process_answer(message, state, 7)

@router.message(Questionnaire.q9)
async def q9(message: Message, state: FSMContext):
    await process_answer(message, state, 8)

@router.message(Questionnaire.q10)
async def q10(message: Message, state: FSMContext):
    await process_answer(message, state, 9)

@router.message(Questionnaire.q11)
async def q11(message: Message, state: FSMContext):
    await process_answer(message, state, 10)

@router.message(Questionnaire.q12)
async def q12(message: Message, state: FSMContext):
    await process_answer(message, state, 11)

@router.message(Questionnaire.q13)
async def q13(message: Message, state: FSMContext):
    await process_answer(message, state, 12)

@router.message(Questionnaire.q14)
async def q14(message: Message, state: FSMContext):
    await process_answer(message, state, 13)

@router.message(Questionnaire.q15)
async def q15(message: Message, state: FSMContext):
    await process_answer(message, state, 14)

# ==================== MAIN ====================
async def main():
    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
