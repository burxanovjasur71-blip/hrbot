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
    """Unicode (kirill, lotin) ni qo'llab-quvvatlaydigan shriftlarni ro'yxatdan o'tkazish"""
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
            ]
        elif platform.system() == "Linux":
            fonts_to_try = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            ]
        elif platform.system() == "Darwin":  # macOS
            fonts_to_try = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Arial.ttf",
                "/Library/Fonts/Arial Unicode.ttf",
            ]
        
        # Qo'shimcha: O'zbek tilidagi shriftlar
        additional_fonts = [
            "DejaVuSans.ttf",
            "LiberationSans-Regular.ttf",
            "NotoSans-Regular.ttf"
        ]
        
        # Tizim yo'llariga qarab qidirish
        for font_path in fonts_to_try:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('UnicodeFont', font_path))
                logging.info(f"✅ Shrift muvaffaqiyatli yuklandi: {font_path}")
                return 'UnicodeFont'
        
        # 2. Usul: Agar tizim shrifti topilmasa, o'rnatilgan kutubxona shriftlaridan foydalanish
        try:
            # ReportLab bilan birga keladigan shriftlar
            from reportlab.lib.fonts import addMapping
            pdfmetrics.registerFont(TTFont('FreeSans', 'FreeSans.ttf'))
            return 'FreeSans'
        except:
            pass
        
        # 3. Usul: Standart shrift (faqat lotincha)
        logging.warning("⚠️ Unicode shrift topilmadi, standart shrift ishlatiladi (kirillcha ko'rinmasligi mumkin)")
        return 'Helvetica'
        
    except Exception as e:
        logging.error(f"Shriftni yuklashda xatolik: {e}")
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
    
    kirill_chars = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯўғқҳЎҒҚҲ')
    text_chars = set(text)
    
    # Agar matnda kirill harflari bo'lsa, transliteratsiya qilamiz
    if text_chars & kirill_chars:
        result = []
        for char in text:
            result.append(TRANSLIT_MAP.get(char, char))
        return ''.join(result)
    return text

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

# States
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
    q10_certificates = State()
    q11_last_job = State()
    q12_position = State()
    q13_duration = State()
    q14_skills = State()
    q15_programs = State()
    q16_languages = State()
    q17_schedule = State()
    q18_salary = State()

questions = [
    "Ismingiz va familiyangiz?",
    "Tug'ilgan sanangiz?",
    "Telefon raqamingiz?",
    "Qaysi shaharda/tumanda yashaysiz?",
    "Telegram username'ingiz?",
    "Selfi rasmingizni yuboring (foto):",
    "Nega aynan shu ish sizga qiziq?",
    "Qachondan ish boshlay olasiz?",
    "Mutaxassisligingiz?",
    "Qo'shimcha kurslar yoki sertifikatlaringiz bormi?",
    "Oxirgi ish joyingiz qayer edi?",
    "Qaysi lavozimda ishlagansiz?",
    "Qancha vaqt ishlagansiz?",
    "Qanday professional ko'nikmalaringiz bor?",
    "Qaysi kompyuter dasturlarini bilasiz?",
    "Qaysi tillarni bilasiz?",
    "Qanday ish grafigi sizga mos?",
    "Kutilayotgan oylik maoshingiz (taxminan)?"
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
        answers[f"q{question_index+1}"] = message.text
    
    await state.update_data(answers=answers)
    
    if question_index + 1 < len(questions):
        await state.set_state(next_state)
        await message.answer(questions[question_index + 1])
    else:
        await finish_questionnaire(message, state)

# Savol handlerlari (qisqartirilgan holda)
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
    await process_answer(message, state, Questionnaire.q10_certificates, 8)

@router.message(Questionnaire.q10_certificates)
async def q10(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q11_last_job, 9)

@router.message(Questionnaire.q11_last_job)
async def q11(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q12_position, 10)

@router.message(Questionnaire.q12_position)
async def q12(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q13_duration, 11)

@router.message(Questionnaire.q13_duration)
async def q13(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q14_skills, 12)

@router.message(Questionnaire.q14_skills)
async def q14(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q15_programs, 13)

@router.message(Questionnaire.q15_programs)
async def q15(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q16_languages, 14)

@router.message(Questionnaire.q16_languages)
async def q16(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q17_schedule, 15)

@router.message(Questionnaire.q17_schedule)
async def q17(message: Message, state: FSMContext):
    await process_answer(message, state, Questionnaire.q18_salary, 16)

@router.message(Questionnaire.q18_salary)
async def q18(message: Message, state: FSMContext):
    await process_answer(message, state, None, 17)

# PDF yaratish (Unicode qo'llab-quvvatlashi bilan)
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

    # Unicode shriftni qo'llash
    c.setFont(FONT_NAME, 18)
    c.drawString(140, y, "SMART+ — HR Anketa")
    y -= 50

    c.setFont(FONT_NAME, 12)
    c.drawString(50, y, f"Foydalanuvchi: @{username or 'No username'}")
    c.drawString(50, y - 20, f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 50

    for i in range(1, 19):
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
            text = str(answer)
            
            # Matnni UTF-8 da saqlaymiz
            try:
                text = text.encode('utf-8', 'ignore').decode('utf-8')
            except:
                pass
            
            lines = []
            line = ""
            for word in text.split():
                # Har bir so'zning kengligini tekshirish
                if c.stringWidth(line + word + " ") > 480:
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
        
    except Exception as e:
        logging.error(f"PDF tayyorlash yoki yuborishda xatolik: {e}", exc_info=True)
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())