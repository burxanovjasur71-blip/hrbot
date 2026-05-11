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
from reportlab.pdfbase import pdfmetrics
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

# ============ SHRIFTNI SOZLASH (TAKMILASHTIRILGAN) ============
def register_unicode_fonts():
    """Unicode (kirill, lotin) ni qo'llab-quvvatlaydigan shriftlarni ro'yxatdan o'tkazish"""
    
    # Mumkin bo'lgan shrift yo'llari (ko'proq variantlar qo'shildi)
    fonts_to_try = []
    
    if platform.system() == "Windows":
        fonts_to_try = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/ariali.ttf",      # Arial Italic
            "C:/Windows/Fonts/arialbd.ttf",     # Arial Bold
            "C:/Windows/Fonts/times.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/verdana.ttf",
            "C:/Windows/Fonts/arialuni.ttf",    # Arial Unicode MS (eng yaxshi variant)
            "C:/Windows/Fonts/segoeui.ttf",     # Segoe UI
            "C:/Windows/Fonts/tahoma.ttf",      # Tahoma
            "C:/Windows/Fonts/consola.ttf",     # Consolas
        ]
    elif platform.system() == "Linux":
        fonts_to_try = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
    elif platform.system() == "Darwin":  # macOS
        fonts_to_try = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/SFNSText.ttf",
        ]
    
    # Qo'shimcha: Python paketlar bilan keladigan shriftlarni tekshirish
    try:
        import matplotlib
        matplotlib_font = matplotlib.font_manager.findfont('DejaVu Sans')
        if matplotlib_font and os.path.exists(matplotlib_font):
            fonts_to_try.insert(0, matplotlib_font)
            logging.info(f"✅ Matplotlib shrifti topildi: {matplotlib_font}")
    except:
        pass
    
    # Har bir yo'lni tekshirish
    for font_path in fonts_to_try:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('UnicodeFont', font_path))
                logging.info(f"✅ Shrift muvaffaqiyatli yuklandi: {font_path}")
                return 'UnicodeFont'
            except Exception as e:
                logging.warning(f"Shriftni yuklashda xatolik {font_path}: {e}")
                continue
    
    # Agar hech qanday shrift topilmasa, fallback sifatida helvetica
    logging.warning("⚠️ Hech qanday Unicode shrift topilmadi. Kirill harflari PDFda ko'rinmasligi mumkin!")
    logging.warning("   Yechim: 'pip install reportlab matplotlib' qiling va shriftlarni o'rnating")
    
    # Linux uchun: fallback sifatida FreeSans ni yuklashga urinib ko'rish
    if platform.system() == "Linux":
        try:
            # Apt orqali o'rnatishni tavsiya qilish
            logging.info("💡 Tavsiya: 'sudo apt-get install fonts-freefont-ttf' yoki 'sudo apt-get install fonts-dejavu-core'")
        except:
            pass
    
    return 'Helvetica'

# Shriftni ro'yxatdan o'tkazish
FONT_NAME = register_unicode_fonts()
# ==========================================

# Transliteratsiya jadvali (kirill -> lotin)
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
    
    # Faqat kirill harflarini transliteratsiya qilish
    result = []
    for char in text:
        if char in TRANSLIT_MAP:
            result.append(TRANSLIT_MAP[char])
        else:
            result.append(char)
    return ''.join(result)

def sanitize_filename(filename: str) -> str:
    """Fayl nomini xavfsiz qiladi (faqat lotin harflari)"""
    # Avval transliteratsiya, keyin tozalash
    filename = transliterate(filename)
    # Faqat lotin harflari, raqamlar va ba'zi belgilarni qoldirish
    filename = re.sub(r'[^a-zA-Z0-9\s\-_\.]', '', filename)
    filename = filename.strip().replace(' ', '_')
    if not filename or filename == '_':
        filename = "unknown"
    if len(filename) > 50:
        filename = filename[:50]
    return filename

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

# Savollar
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
    "Taqdim etilgan oylik maosh sizga ma'qulmi (6 000 000 dan boshlanadi)?"
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
        # Matnni saqlash (original holatda)
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

# PDF yaratish (takomillashtirilgan)
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
    
    # Shriftni tekshirish
    try:
        c.setFont(FONT_NAME, 18)
        logging.info(f"PDF yaratishda shrift ishlatilmoqda: {FONT_NAME}")
    except Exception as e:
        logging.error(f"Shriftni o'rnatishda xatolik: {e}")
        c.setFont('Helvetica', 18)
    
    # Sarlavha
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
        
        # Savol matnini chiqarish
        c.setFont(FONT_NAME, 11)
        question_text = f"{i}. {question}"
        
        # UTF-8 matnni to'g'ri ko'rsatish
        try:
            # Matnni UTF-8 da kodlash
            if isinstance(question_text, str):
                question_text = question_text.encode('utf-8', 'ignore').decode('utf-8')
        except:
            pass
        
        c.drawString(50, y, question_text)
        y -= 25
        
        # Javobni chiqarish
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
            text = str(answer)
            
            # UTF-8 matnni tayyorlash
            try:
                text = text.encode('utf-8', 'ignore').decode('utf-8')
            except:
                pass
            
            # Matnni o'rash
            lines = []
            line = ""
            for word in text.split():
                try:
                    if c.stringWidth(line + word + " ") > 480:
                        lines.append(line)
                        line = word + " "
                    else:
                        line += word + " "
                except:
                    lines.append(word)
                    line = ""
                    continue
            if line:
                lines.append(line)
            
            if not lines:
                lines = [text[:100]]
            
            for line in lines:
                if y < 50:
                    c.showPage()
                    y = height - 50
                    c.setFont(FONT_NAME, 11)
                try:
                    c.drawString(70, y, line)
                except:
                    # Agar xatolik bo'lsa, lotin harflariga o'tkazish
                    latin_line = transliterate(line)
                    c.drawString(70, y, latin_line)
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
        except Exception as e:
            logging.warning(f"Faylni o'chirishda xatolik: {e}")
        
    except Exception as e:
        logging.error(f"PDF tayyorlash yoki yuborishda xatolik: {e}", exc_info=True)
        await message.answer(f"❌ Xatolik yuz berdi. Iltimos, administrator bilan bog'lanishingiz mumkin.")
    
    await state.clear()

async def main():
    logging.info(f"Ishlatilayotgan shrift: {FONT_NAME}")
    logging.info(f"Operatsion tizim: {platform.system()}")
    if FONT_NAME == 'Helvetica':
        logging.warning("⚠️ Diqqat! Unicode shrift topilmadi. Kirill harflari PDFda ko'rinmasligi mumkin!")
        logging.warning("Yechimlar:")
        logging.warning("1. Windows: Arial Unicode MS o'rnatilganligini tekshiring")
        logging.warning("2. Linux: sudo apt-get install fonts-dejavu-core fonts-freefont-ttf")
        logging.warning("3. macOS: Shriftlar mavjudligini tekshiring")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())