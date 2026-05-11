import asyncio
import logging
from datetime import datetime
import os
import re
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import platform

# Logging
logging.basicConfig(level=logging.INFO)

# Bot token
BOT_TOKEN = "8653151262:AAGl4mNfcA2Qvd8zpn8d79IOhlDLohh1XfQ"

# Guruh ID
GROUP_ID = -1003918988982

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ============ SHRIFTNI SOZLASH ============
def register_unicode_fonts():
    """Unicode (kirill, lotin, rus, o'zbek) ni qo'llab-quvvatlaydigan shriftlarni ro'yxatdan o'tkazish"""
    try:
        # 1. Usul: Tizimda mavjud shriftlarni topish
        fonts_to_try = []
        
        if platform.system() == "Windows":
            fonts_to_try = [
                "C:/Windows/Fonts/arial.ttf",           # Arial
                "C:/Windows/Fonts/times.ttf",           # Times New Roman
                "C:/Windows/Fonts/calibri.ttf",         # Calibri
                "C:/Windows/Fonts/verdana.ttf",         # Verdana
                "C:/Windows/Fonts/arialuni.ttf",        # Arial Unicode MS
                "C:/Windows/Fonts/tahoma.ttf",          # Tahoma
                "C:/Windows/Fonts/msgothic.ttc",        # MS Gothic
            ]
        elif platform.system() == "Linux":
            fonts_to_try = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
            ]
        elif platform.system() == "Darwin":  # macOS
            fonts_to_try = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Arial.ttf",
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/AppleGothic.ttf",
            ]
        
        # Tizim yo'llariga qarab qidirish
        for font_path in fonts_to_try:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('UnicodeFont', font_path))
                logging.info(f"✅ Shrift muvaffaqiyatli yuklandi: {font_path}")
                return 'UnicodeFont'
        
        # 2. Usul: Agar tizim shrifti topilmasa, o'rnatilgan kutubxona shriftlaridan foydalanish
        try:
            # ReportLab bilan birga keladigan shrift fayllarini tekshirish
            from reportlab.lib import fonts
            pdfmetrics.registerFont(TTFont('FreeSans', 'FreeSans.ttf'))
            logging.info("✅ FreeSans shrifti yuklandi")
            return 'FreeSans'
        except:
            pass
        
        # 3. Usul: Standart shrift (lekin UTF-8 qo'llab-quvvatlamasligi mumkin)
        logging.warning("⚠️ Unicode shrift topilmadi, standart shrift ishlatiladi")
        return 'Helvetica'
        
    except Exception as e:
        logging.error(f"Shriftni yuklashda xatolik: {e}")
        return 'Helvetica'

# Shriftni ro'yxatdan o'tkazish
FONT_NAME = register_unicode_fonts()
# ==========================================

# ===== TRANSLITERATSIYA O'CHIRILDI (asl matn saqlanadi) =====
def sanitize_filename(filename: str) -> str:
    """Fayl nomini xavfsiz qiladi (faqat fayl nomi uchun transliteratsiya)"""
    # Faqat fayl nomi uchun xavfsiz belgilar
    filename = re.sub(r'[^\w\s.-]', '_', filename)
    filename = filename.strip().replace(' ', '_')
    if not filename or filename == "_":
        filename = "unknown"
    if len(filename) > 50:
        filename = filename[:50]
    return filename
# ============================================================

# States (15 ta state)
class Questionnaire(StatesGroup):
    q1_name = State()
    q2_birth = State()
    q3_phone = State()
    q4_city = State()
    q5_username = State()
    q6_selfie = State()
    q7_why = State()
    q8_start_date = State()
    q9_specialty = State()
    q10_job_history = State()
    q11_duration = State()
    q12_programs = State()
    q13_languages = State()
    q14_schedule = State()
    q15_salary = State()

# Savollar (15 ta savol)
questions = [
    "Ismingiz va familiyangiz?",
    "Tug'ilgan yilingiz?",
    "Telefon raqamingiz va Telegarm username ingiz?",
    "Qaysi shaharda/tumanda yashaysiz?",
    "Malumotingiz va oilangiz haqida malumot?",
    "Selfi rasmingizni yuboring (foto):",
    "Biz taklif qilgan ishda qancha vaqt ishlay olasiz?",
    "Qachondan ish boshlay olasiz?",
    "Mutaxassisligingiz?",
    "Qayerlarda ishlagansiz va qanday lavozimlarda?",
    "Qancha vaqt ishlagansiz va ishdan bo'shashingiz sababi?",
    "Ota-onangizning kasbi va faoliyati haqida ma’lumot bering?",
    "Qaysi tillarni bilasiz?",
    "Ko'rsatilgan ish vaqti sizga mos keladimi(10:00 dan 20:00)?",
    "Taqdim etilgan oylik maosh sizga maqulmi(6 000 000 dan boshlanadi)?"
]

# Start komandasi
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    text = """SMART+ — telefonlar, telefon aksessuarlari va ehtiyot qismlarining ulgurji savdosi bilan shug'ullanuvchi ishonchli kompaniya hisoblanadi. 

Biz bozorda sifatli mahsulotlar va barqaror hamkorlik orqali o'z o'rnimizni mustahkamlab kelmoqdamiz. Bugungi kunda kompaniyamizning 9 ta filiali faoliyat yuritib, mijozlarimizga tezkor va qulay xizmat ko'rsatishni ta'minlamoqda. 

Kompaniyamiz asoschisi — Samanov Bobur. 

Bizning asosiy maqsadlarimiz:
— Yangi ish o'rinlari yaratish
— Mijozlarga yuqori sifatli xizmat ko'rsatish
— O'zbekiston rivojiga o'z hissamizni qo'shish

Biz har bir hamkorlikda ishonch va sifatni ustuvor deb bilamiz. 

SMART+ shiori: "Halollik foydadan ustun"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 ANKETANI TO'LDIRISH", callback_data="start_questionnaire")]
    ])

    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "logo.png")

    if os.path.exists(logo_path):
        try:
            photo = FSInputFile(logo_path)
            await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
            logging.info("Logo rasm muvaffaqiyatli yuborildi")
        except Exception as e:
            logging.error(f"Rasm yuborishda xato: {e}")
            await message.answer(text, reply_markup=keyboard)
    else:
        logging.warning(f"Logo fayli topilmadi: {logo_path}")
        await message.answer(text, reply_markup=keyboard)

    await state.clear()

@router.callback_query(F.data == "start_questionnaire")
async def start_questionnaire(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_caption(
        caption="Anketa boshlandi! Javobingizni yozing yoki yuboring.",
        reply_markup=None
    )
    await state.set_state(Questionnaire.q1_name)
    await callback.message.answer(questions[0])
    await callback.answer()

async def process_answer(message: Message, state: FSMContext, next_state, question_index: int):
    data = await state.get_data()
    answers = data.get("answers", {})
    
    if message.photo:
        photo_id = message.photo[-1].file_id
        answers[f"q{question_index+1}"] = f"Photo: {photo_id}"
    else:
        # Matnni transliteratsiya QILMAYMIZ, asl holatida saqlaymiz
        answers[f"q{question_index+1}"] = message.text
    
    await state.update_data(answers=answers)
    
    if question_index + 1 < len(questions):
        await state.set_state(next_state)
        await message.answer(questions[question_index + 1])
    else:
        await finish_questionnaire(message, state)

# Savol handlerlari
@router.message(Questionnaire.q1_name)
async def q1(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q2_birth, 0)

@router.message(Questionnaire.q2_birth)
async def q2(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q3_phone, 1)

@router.message(Questionnaire.q3_phone)
async def q3(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q4_city, 2)

@router.message(Questionnaire.q4_city)
async def q4(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q5_username, 3)

@router.message(Questionnaire.q5_username)
async def q5(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q6_selfie, 4)

@router.message(Questionnaire.q6_selfie, F.photo)
async def q6(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q7_why, 5)

@router.message(Questionnaire.q7_why)
async def q7(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q8_start_date, 6)

@router.message(Questionnaire.q8_start_date)
async def q8(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q9_specialty, 7)

@router.message(Questionnaire.q9_specialty)
async def q9(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q10_job_history, 8)

@router.message(Questionnaire.q10_job_history)
async def q10(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q11_duration, 9)

@router.message(Questionnaire.q11_duration)
async def q11(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q12_programs, 10)

@router.message(Questionnaire.q12_programs)
async def q12(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q13_languages, 11)

@router.message(Questionnaire.q13_languages)
async def q13(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q14_schedule, 12)

@router.message(Questionnaire.q14_schedule)
async def q14(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q15_salary, 13)

@router.message(Questionnaire.q15_salary)
async def q15(message: Message, state: FSMContext):
    await process_answer(message, state, None, 14)

# PDF yaratish (asl matn saqlanadi)
async def create_pdf(bot, user_id: int, answers: dict, username: str):
    raw_name = answers.get("q1", "unknown")
    safe_name = sanitize_filename(raw_name)
    
    if not safe_name or safe_name == "unknown":
        safe_name = f"user_{user_id}"
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_name}_{timestamp}.pdf"
    
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont(FONT_NAME, 18)
    c.drawString(140, y, "SMART+ — HR Anketa")
    y -= 50

    c.setFont(FONT_NAME, 12)
    c.drawString(50, y, f"Foydalanuvchi: @{username or 'No username'}")
    c.drawString(50, y - 20, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 50

    # 15 ta savol uchun aylanish
    for i in range(1, 16):
        if y < 120:
            c.showPage()
            y = height - 50
            c.setFont(FONT_NAME, 12)

        key = f"q{i}"
        question = questions[i-1]
        answer = answers.get(key, "Javob berilmagan")

        c.setFont(FONT_NAME, 11)
        c.drawString(50, y, f"{i}. {question}")
        y -= 25

        if i == 6 and str(answer).startswith("Photo:"):
            try:
                file_id = answer.split(": ")[1]
                file = await bot.get_file(file_id)
                file_bytes = await bot.download_file(file.file_path)
                if hasattr(file_bytes, "read"):
                    data = file_bytes.read()
                else:
                    data = file_bytes
                bio = BytesIO(data)
                bio.seek(0)

                img_reader = ImageReader(bio)
                orig_w, orig_h = img_reader.getSize()
                img_width = 300
                img_height = img_width * (orig_h / orig_w) if orig_w else img_width

                if y - img_height < 50:
                    c.showPage()
                    y = height - 50

                c.drawImage(img_reader, 50, y - img_height, width=img_width, height=img_height)
                y -= (img_height + 30)
                c.setFont(FONT_NAME, 10)
                c.drawString(50, y, "↑ Selfi rasmi")
                y -= 20

            except Exception as e:
                c.setFont(FONT_NAME, 10)
                c.drawString(70, y, f"Rasm yuklashda xatolik: {e}")
                y -= 30
        else:
            c.setFont(FONT_NAME, 11)
            # Matnni asl holatida qoldiramiz - transliteratsiya QILINMAYDI
            text = str(answer)
            
            # PDF uchun UTF-8 ni to'g'ri kodlash
            try:
                # Uni to'g'ri kodlash va dekodlash
                text = text.encode('utf-8', 'ignore').decode('utf-8')
            except:
                pass
            
            # Matnni o'rash (wrap)
            lines = []
            line = ""
            for word in text.split():
                # stringWidth shriftga bog'liq, to'g'ri ishlashi uchun
                try:
                    test_line = line + word + " "
                    if c.stringWidth(test_line) > 480:
                        lines.append(line)
                        line = word + " "
                    else:
                        line += word + " "
                except:
                    # Agar stringWidth xatolik bersa, 50 belgidan keyin chiziqni uz
                    if len(line) + len(word) > 50:
                        lines.append(line)
                        line = word + " "
                    else:
                        line += word + " "
            if line:
                lines.append(line)

            for line in lines:
                if y < 50:
                    c.showPage()
                    y = height - 50
                    c.setFont(FONT_NAME, 11)
                c.drawString(70, y, line)
                y -= 20
            y -= 15

    c.save()
    return filename

# Yakunlash
async def finish_questionnaire(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", {})
    
    await message.answer("✅ Anketangiz muvaffaqiyatli tugatildi! Rahmat.")
    
    try:
        pdf_file = await create_pdf(bot, message.from_user.id, answers, message.from_user.username)
        doc = FSInputFile(pdf_file)
        
        # 1. PDF faylni foydalanuvchining o'ziga yuborish
        await bot.send_document(
            chat_id=message.from_user.id,
            document=doc,
            caption=f"📄 Sizning anketa PDF faylingiz: {os.path.basename(pdf_file)}"
        )
        
        # 2. PDF faylni guruhga yuborish
        group_caption = (
            f"🆕 Yangi anketa!\n"
            f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n"
            f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"📄 Fayl: {os.path.basename(pdf_file)}"
        )
        await bot.send_document(
            chat_id=GROUP_ID,
            document=doc,
            caption=group_caption
        )
        logging.info(f"PDF foydalanuvchiga va guruhga (ID: {GROUP_ID}) yuborildi. Fayl: {pdf_file}")
        
        # Vaqtinchalik faylni o'chirish
        try:
            os.remove(pdf_file)
            logging.info(f"Vaqtinchalik fayl o'chirildi: {pdf_file}")
        except:
            pass
        
    except Exception as e:
        logging.error(f"PDF tayyorlash yoki yuborishda xatolik: {e}", exc_info=True)
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())