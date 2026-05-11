import asyncio
import logging
from datetime import datetime
import os
import re
import sys
import platform
from io import BytesIO
import textwrap
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

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

# ============ YAXSHILANGAN SHRIFT SOZLASH ============
class FontManager:
    """Shriftlarni boshqarish va yuklash klassi"""
    
    def __init__(self):
        self.font_name = None
        self.font_loaded = False
        
    def find_windows_fonts(self):
        """Windows tizimida mavjud shriftlarni topish"""
        font_paths = []
        
        # Windows shrift papkalari
        possible_paths = []
        
        # Windows drive harflari
        for drive in ['C:', 'D:', 'E:']:
            # Har xil versiyalar uchun papkalar
            font_dirs = [
                f'{drive}/Windows/Fonts/',
                f'{drive}/WINNT/Fonts/',
                f'{drive}/WINDOWS/Fonts/',
                f'{drive}/Windows/Fonts/',
            ]
            
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    possible_paths.append(font_dir)
        
        # WSL uchun maxsus yo'llar
        if 'microsoft' in platform.uname().release.lower():
            wsl_paths = [
                '/mnt/c/Windows/Fonts/',
                '/mnt/c/WINDOWS/Fonts/',
                '/usr/share/fonts/truetype/',
                '/usr/local/share/fonts/',
            ]
            possible_paths.extend(wsl_paths)
        
        # Qidiriladigan shrift nomlari
        font_files = [
            'arial.ttf', 'arialuni.ttf', 'arialbd.ttf',
            'times.ttf', 'timesbd.ttf',
            'calibri.ttf', 'calibrib.ttf',
            'verdana.ttf', 'verdanab.ttf',
            'tahoma.ttf', 'tahomabd.ttf',
            'segoeui.ttf', 'segoeuib.ttf',
            'DejaVuSans.ttf', 'FreeSans.ttf'
        ]
        
        # Shriftlarni qidirish
        for font_dir in possible_paths:
            for font_file in font_files:
                font_path = os.path.join(font_dir, font_file)
                if os.path.exists(font_path):
                    font_paths.append(font_path)
                    logging.info(f"🔍 Shrift topildi: {font_path}")
        
        return font_paths
    
    def register_fonts(self):
        """Turli tillarni qo'llab-quvvatlaydigan shriftlarni ro'yxatdan o'tkazish"""
        
        # 1. Windows shriftlarini yuklash
        windows_fonts = self.find_windows_fonts()
        
        for font_path in windows_fonts:
            try:
                # Shrift nomini fayl nomidan olish
                font_base_name = os.path.basename(font_path).split('.')[0]
                font_registry_name = f"CustomFont_{font_base_name}"
                
                # Shriftni ro'yxatdan o'tkazish
                pdfmetrics.registerFont(TTFont(font_registry_name, font_path))
                logging.info(f"✅ Shrift muvaffaqiyatli yuklandi: {font_path}")
                logging.info(f"✅ {font_registry_name} shrifti ro'yxatdan o'tkazildi")
                
                self.font_name = font_registry_name
                self.font_loaded = True
                return self.font_name
                
            except Exception as e:
                logging.warning(f"⚠️ Shrift yuklanmadi {font_path}: {e}")
                continue
        
        # 2. Linux shriftlari (WSL uchun)
        try:
            # WSL da o'rnatilgan shriftlarni tekshirish
            linux_fonts = [
                ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'DejaVuSans'),
                ('/usr/share/fonts/truetype/freefont/FreeSans.ttf', 'FreeSans'),
                ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', 'LiberationSans'),
            ]
            
            for font_path, font_name in linux_fonts:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    logging.info(f"✅ Linux shrifti yuklandi: {font_name}")
                    self.font_name = font_name
                    self.font_loaded = True
                    return self.font_name
                    
        except Exception as e:
            logging.warning(f"⚠️ Linux shriftlarini yuklashda xato: {e}")
        
        # 3. Standart shrift (faqat lotin)
        logging.error("❌ Hech qanday Unicode shrift topilmadi!")
        logging.error("❌ Iltimos, quyidagi buyruq bilan shriftlarni o'rnating:")
        logging.error("   sudo apt-get install fonts-dejavu fonts-freefont-ttf")
        self.font_name = 'Helvetica'
        self.font_loaded = False
        return self.font_name
    
    def get_font(self):
        """Yuklangan shrift nomini qaytarish"""
        if not self.font_loaded:
            self.register_fonts()
        return self.font_name

# Font manager yaratish
font_manager = FontManager()
FONT_NAME = font_manager.get_font()

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
    """Matnni kirill alifbosidan lotin alifbosiga o'giradi (zaxira uchun)"""
    if not text:
        return ""
    result = []
    for char in text:
        result.append(TRANSLIT_MAP.get(char, char))
    return ''.join(result)

def sanitize_filename(filename: str) -> str:
    """Fayl nomini xavfsiz qiladi"""
    # Kirilldan lotinga o'tkazish
    filename = transliterate(filename)
    # Faqat xavfsiz belgilarni qoldirish
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = filename.strip().replace(' ', '_')
    if not filename:
        filename = "unknown"
    if len(filename) > 50:
        filename = filename[:50]
    return filename

def safe_encode_text(text: str) -> str:
    """Matnni xavfsiz kodlash va tozalash"""
    if not text:
        return ""
    
    try:
        # Agar bytes bo'lsa, decode qilish
        if isinstance(text, bytes):
            text = text.decode('utf-8', 'ignore')
        
        # UTF-8 da tozalash
        text = str(text).encode('utf-8', 'ignore').decode('utf-8')
        
        # Null va boshqa maxsus belgilarni olib tashlash
        text = text.replace('\x00', '').replace('\r', ' ').replace('\n', ' ')
        
        return text.strip()
        
    except Exception as e:
        logging.error(f"Matn kodlashda xato: {e}")
        return str(text)

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
        # Matnni xavfsiz kodlash
        clean_text = safe_encode_text(message.text)
        answers[f"q{question_index+1}"] = clean_text
    
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

# PDF yaratish (RUSCHA HARFLAR UCHUN TO'LIQ QO'LLAB-QUVVATLASH)
async def create_pdf(bot, user_id: int, answers: dict, username: str):
    raw_name = answers.get("q1", "unknown")
    safe_name = sanitize_filename(raw_name)
    
    if not safe_name or safe_name == "unknown":
        safe_name = f"user_{user_id}"
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_name}_{timestamp}.pdf"
    
    # PDF yaratish
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    y = height - 50
    
    # Sarlavha
    try:
        c.setFont(FONT_NAME, 18)
        c.drawString(140, y, "SMART+ — HR Anketa")
    except:
        # Agar shrift ishlamasa, Helvetica ishlatamiz
        c.setFont('Helvetica', 18)
        c.drawString(140, y, "SMART+ HR Anketa")
    y -= 50
    
    # Foydalanuvchi ma'lumotlari
    try:
        c.setFont(FONT_NAME, 12)
    except:
        c.setFont('Helvetica', 12)
    
    c.drawString(50, y, f"Foydalanuvchi: @{username or 'No username'}")
    c.drawString(50, y - 20, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.drawString(50, y - 40, f"User ID: {user_id}")
    y -= 70
    
    # 15 ta savol va javoblar
    for i in range(1, 16):
        if y < 100:
            c.showPage()
            y = height - 50
            try:
                c.setFont(FONT_NAME, 12)
            except:
                c.setFont('Helvetica', 12)
        
        key = f"q{i}"
        question = questions[i-1]
        answer = answers.get(key, "Javob berilmagan")
        
        # Savolni yozish
        try:
            c.setFont(FONT_NAME, 11)
            c.drawString(50, y, f"{i}. {question}")
        except:
            c.setFont('Helvetica', 11)
            c.drawString(50, y, f"{i}. {question}")
        y -= 25
        
        # Rasm (selfi)
        if i == 6 and str(answer).startswith("Photo:"):
            try:
                file_id = answer.split(": ")[1]
                file = await bot.get_file(file_id)
                file_bytes = await bot.download_file(file.file_path)
                
                # BytesIO yaratish
                if hasattr(file_bytes, "read"):
                    data = file_bytes.read()
                else:
                    data = file_bytes
                
                bio = BytesIO(data)
                bio.seek(0)
                
                img_reader = ImageReader(bio)
                orig_w, orig_h = img_reader.getSize()
                img_width = 250
                img_height = img_width * (orig_h / orig_w) if orig_w else img_width
                
                if y - img_height < 50:
                    c.showPage()
                    y = height - 50
                
                c.drawImage(img_reader, 50, y - img_height, width=img_width, height=img_height)
                y -= (img_height + 20)
                
                try:
                    c.setFont(FONT_NAME, 10)
                except:
                    c.setFont('Helvetica', 10)
                c.drawString(50, y, "↑ Selfi rasmi")
                y -= 20
                
            except Exception as e:
                try:
                    c.setFont(FONT_NAME, 10)
                except:
                    c.setFont('Helvetica', 10)
                c.drawString(70, y, f"[Rasm yuklashda xatolik: {str(e)[:50]}]")
                y -= 30
        else:
            # MATNNI TO'G'RI KO'RSATISH (RUSCHA UCHUN)
            try:
                # Shriftni o'rnatish
                try:
                    c.setFont(FONT_NAME, 11)
                except:
                    c.setFont('Helvetica', 11)
                
                # Matnni tozalash va kodlash
                text = safe_encode_text(str(answer))
                
                # Agar shrift Unicode ni qo'llab-quvvatlamasa, transliteratsiya qilish
                if FONT_NAME == 'Helvetica' or not font_manager.font_loaded:
                    # Zaxira: Transliteratsiya qilish
                    text = transliterate(text)
                    logging.info(f"Transliteratsiya qilindi: {text[:50]}...")
                
                # Matnni o'rash
                wrapped_lines = textwrap.wrap(text, width=85)
                
                if not wrapped_lines:
                    wrapped_lines = [text if text else "Javob berilmagan"]
                
                for line in wrapped_lines:
                    if y < 50:
                        c.showPage()
                        y = height - 50
                        try:
                            c.setFont(FONT_NAME, 11)
                        except:
                            c.setFont('Helvetica', 11)
                    
                    try:
                        c.drawString(70, y, line)
                    except Exception as e:
                        # Agar xato bo'lsa, lotin alifbosiga o'tkazish
                        logging.warning(f"Matn yozishda xato: {e}")
                        latin_line = transliterate(line)
                        try:
                            c.drawString(70, y, latin_line)
                        except:
                            c.drawString(70, y, "Matn o'qib bo'lmaydi")
                    
                    y -= 20
                y -= 15
                
            except Exception as e:
                logging.error(f"Javob {i} ni yozishda xato: {e}")
                try:
                    c.drawString(70, y, f"Xatolik: {str(e)[:50]}")
                except:
                    pass
                y -= 30
    
    c.save()
    logging.info(f"✅ PDF yaratildi: {filename}")
    return filename

async def finish_questionnaire(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", {})
    
    await message.answer("✅ Anketangiz muvaffaqiyatli tugatildi! Rahmat.")
    
    try:
        pdf_file = await create_pdf(bot, message.from_user.id, answers, message.from_user.username)
        
        # PDF fayl mavjudligini tekshirish
        if os.path.exists(pdf_file):
            doc = FSInputFile(pdf_file)
            
            # Foydalanuvchiga yuborish
            await bot.send_document(
                chat_id=message.from_user.id,
                document=doc,
                caption="📄 Sizning anketa PDF faylingiz"
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
                logging.info(f"🗑️ Fayl o'chirildi: {pdf_file}")
            except Exception as e:
                logging.warning(f"Faylni o'chirishda xato: {e}")
        else:
            await message.answer("❌ PDF fayl yaratilmadi!")
            
    except Exception as e:
        logging.error(f"Xatolik: {e}", exc_info=True)
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}\nIltimos, qaytadan urinib ko'ring.")
    
    await state.clear()

async def main():
    print("=" * 50)
    print("🤖 SMART+ HR Bot ishga tushdi")
    print("=" * 50)
    print(f"📝 Shrift holati: {FONT_NAME}")
    print(f"✅ Unicode qo'llab-quvvatlash: {font_manager.font_loaded}")
    
    if not font_manager.font_loaded or FONT_NAME == 'Helvetica':
        print("\n⚠️ Ogohlantirish: Ruscha harflar ko'rinmasligi mumkin!")
        print("\n🔧 Yechim usullari:")
        print("   1. Windows shriftlarini o'rnatish:")
        print("      sudo apt-get install fonts-liberation fonts-dejavu")
        print("\n   2. Yoki quyidagi shriftlarni yuklab oling:")
        print("      wget https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf")
        print("      mv DejaVuSans.ttf /usr/share/fonts/truetype/")
    else:
        print("✅ Ruscha, O'zbekcha va Inglizcha harflar to'liq qo'llab-quvvatlanadi")
    
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())