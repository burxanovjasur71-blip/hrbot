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
from reportlab.lib.fonts import addMapping
from io import BytesIO
import platform
import sys

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

# ============ WINDA WSL UCHUN KENGAYTIRILGAN SHRIFT SOZLASH ============
def find_windows_fonts():
    """Windows tizimida mavjud shriftlarni qidirish"""
    font_paths = []
    
    # Windows shrift papkalari
    windows_drives = ['C:', 'D:', 'E:']
    font_folders = [
        '/Windows/Fonts/',
        '/WINNT/Fonts/',
        '/WINDOWS/Fonts/'
    ]
    
    # Qidiriladigan shrift nomlari
    font_names = [
        'arial.ttf',
        'arialuni.ttf',
        'times.ttf',
        'calibri.ttf',
        'verdana.ttf',
        'tahoma.ttf',
        'msgothic.ttc',
        'msmincho.ttc',
        'segoeui.ttf',
        'consola.ttf'
    ]
    
    for drive in windows_drives:
        for folder in font_folders:
            for font in font_names:
                path = f"{drive}{folder}{font}"
                if os.path.exists(path):
                    font_paths.append(path)
    
    return font_paths

def register_unicode_fonts():
    """Ruscha va barcha tillarni qo'llab-quvvatlaydigan shriftlarni ro'yxatdan o'tkazish"""
    
    # 1. USUL: Windows shriftlarini topish
    windows_fonts = find_windows_fonts()
    
    for font_path in windows_fonts:
        try:
            # Shriftni ro'yxatdan o'tkazish
            pdfmetrics.registerFont(TTFont('UnicodeFont', font_path))
            logging.info(f"✅ Shrift muvaffaqiyatli yuklandi: {font_path}")
            logging.info(f"✅ Ruscha, O'zbekcha, Inglizcha harflar to'liq qo'llab-quvvatlanadi")
            return 'UnicodeFont'
        except Exception as e:
            logging.warning(f"Shrift yuklanmadi {font_path}: {e}")
            continue
    
    # 2. USUL: Reportlab kutubxonasining o'z shriftlari
    try:
        # reportlab bilan birga keladigan shriftlar
        from reportlab.lib.fonts import addMapping
        import reportlab.rl_config
        reportlab.rl_config.warnOnMissingFontGlyph = 0
        
        # FreeSans shrifti (ko'pincha kirillni qo'llab-quvvatlaydi)
        pdfmetrics.registerFont(TTFont('FreeSans', 'FreeSans.ttf'))
        logging.info("✅ FreeSans shrifti yuklandi")
        return 'FreeSans'
    except:
        pass
    
    # 3. USUL: Standart shrift (faqat lotin)
    logging.error("❌ Hech qanday Unicode shrift topilmadi!")
    logging.error("❌ Ruscha harflar PDF da ko'rinmaydi!")
    logging.error("❌ Yechim: C:/Windows/Fonts/arial.ttf fayli borligini tekshiring")
    return 'Helvetica'

# Shriftni ro'yxatdan o'tkazish
FONT_NAME = register_unicode_fonts()
# ==========================================

# Transliteratsiya jadvali
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
    'ў': "o'", 'ғ': "g'", 'қ': "q", 'ҳ': 'h', 'Ў': "O'", 'Ғ': "G'", 'Қ': 'Q', 'Ҳ': 'H'
}

def transliterate(text: str) -> str:
    """Matnni kirill alifbosidan lotin alifbosiga o'giradi"""
    if not text:
        return ""
    result = []
    for char in text:
        result.append(TRANSLIT_MAP.get(char, char))
    return ''.join(result)

def sanitize_filename(filename: str) -> str:
    """Fayl nomini xavfsiz qiladi"""
    filename = transliterate(filename)
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = filename.strip().replace(' ', '_')
    if not filename:
        filename = "unknown"
    if len(filename) > 50:
        filename = filename[:50]
    return filename

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

questions = [
    "Ismingiz va familiyangiz?",
    "Tug'ilgan yilingiz?",
    "Telefon raqamingiz va Telegram username ingiz?",
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
        except Exception as e:
            logging.error(f"Rasm yuborishda xato: {e}")
            await message.answer(text, reply_markup=keyboard)
    else:
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
        answers[f"q{question_index+1}"] = message.text
    
    await state.update_data(answers=answers)
    
    if question_index + 1 < len(questions):
        await state.set_state(next_state)
        await message.answer(questions[question_index + 1])
    else:
        await finish_questionnaire(message, state)

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

# PDF yaratish (MUAMMO HAL QILINGAN)
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

    # PDF ga UTF-8 kodlashni qo'llash
    c._doc.info.producer = "SMART+ Bot"
    c._doc.info.creator = "SMART+ HR System"
    
    # Sarlavha
    c.setFont(FONT_NAME, 18)
    c.drawString(140, y, "SMART+ — HR Anketa")
    y -= 50

    # Foydalanuvchi ma'lumotlari
    c.setFont(FONT_NAME, 12)
    c.drawString(50, y, f"Foydalanuvchi: @{username or 'No username'}")
    c.drawString(50, y - 20, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 50

    # 15 ta savol
    for i in range(1, 16):
        if y < 120:
            c.showPage()
            y = height - 50
            c.setFont(FONT_NAME, 12)

        key = f"q{i}"
        question = questions[i-1]
        answer = answers.get(key, "Javob berilmagan")

        # Savol
        c.setFont(FONT_NAME, 11)
        c.drawString(50, y, f"{i}. {question}")
        y -= 25

        # Rasm (selfi)
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
            # MATNNI TO'G'RI YOZISH (RUSCHA UCHUN)
            c.setFont(FONT_NAME, 11)
            text = str(answer)
            
            # MUHIM: Matnni UTF-8 da to'g'rilash
            try:
                # Agar text bytes bo'lsa, decode
                if isinstance(text, bytes):
                    text = text.decode('utf-8', 'ignore')
                # Unicode belgilarni saqlash
                text = text.encode('utf-8', 'ignore').decode('utf-8')
            except:
                text = str(answer)
            
            # Matnni o'rash (har bir qator 80 belgidan oshmasligi kerak)
            import textwrap
            wrapped_lines = textwrap.wrap(text, width=85)
            
            if not wrapped_lines:
                wrapped_lines = [text]
            
            for line in wrapped_lines:
                if y < 50:
                    c.showPage()
                    y = height - 50
                    c.setFont(FONT_NAME, 11)
                
                try:
                    # To'g'ridan-to'g'ri chizish
                    c.drawString(70, y, line)
                except Exception as e:
                    logging.warning(f"Matn yozishda xato: {e}")
                    # Agar xato bo'lsa, transliteratsiya qil
                    try:
                        latin_line = transliterate(line)
                        c.drawString(70, y, latin_line)
                    except:
                        c.drawString(70, y, "Matn o'qib bo'lmaydi")
                y -= 20
            y -= 15

    c.save()
    logging.info(f"✅ PDF yaratildi: {filename}")
    return filename

async def finish_questionnaire(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", {})
    
    await message.answer("✅ Anketangiz muvaffaqiyatli tugatildi! Rahmat.")
    
    try:
        pdf_file = await create_pdf(bot, message.from_user.id, answers, message.from_user.username)
        doc = FSInputFile(pdf_file)
        
        # Foydalanuvchiga yuborish
        await bot.send_document(
            chat_id=message.from_user.id,
            document=doc,
            caption=f"📄 Sizning anketa PDF faylingiz"
        )
        
        # Guruhga yuborish
        group_caption = (
            f"🆕 Yangi anketa!\n"
            f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        await bot.send_document(
            chat_id=GROUP_ID,
            document=doc,
            caption=group_caption
        )
        
        # Faylni o'chirish
        try:
            os.remove(pdf_file)
        except:
            pass
        
    except Exception as e:
        logging.error(f"Xatolik: {e}", exc_info=True)
        await message.answer(f"❌ Xatolik: {str(e)}")
    
    await state.clear()

async def main():
    print("=" * 50)
    print("🤖 SMART+ HR Bot ishga tushdi")
    print("=" * 50)
    print(f"📝 Shrift holati: {FONT_NAME}")
    
    if FONT_NAME == 'Helvetica':
        print("❌ XATO: Unicode shrift topilmadi!")
        print("🔧 Yechim: Quyidagi buyruqni VSCode terminalida ishga tushiring:")
        print("   python check_fonts.py")
        print("\n📌 Yoki qo'lda tekshiring:")
        print("   C:/Windows/Fonts/arial.ttf fayli bormi?")
    else:
        print("✅ Ruscha harflar PDF da to'g'ri ko'rinadi")
    
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())