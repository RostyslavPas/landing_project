import io
import uuid
import qrcode
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import logging
from django.urls import reverse
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.conf import settings
import os
from PIL import Image
from .models import BotAccessToken

logger = logging.getLogger(__name__)

# Шлях до шрифту в static
font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
bold_font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans-Bold.ttf")

# Реєструємо шрифти
pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', bold_font_path))

FONT_NORMAL = 'DejaVuSans'
FONT_BOLD = 'DejaVuSans-Bold'


def generate_ticket_qr(order):
    """Генерує QR-код для сторінки перевірки квитка"""
    # Генеруємо URL на сторінку verify_ticket з унікальним order_reference
    verification_path = reverse('verify_ticket', args=[order.id])
    verification_url = f"{settings.SITE_URL}{verification_path}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(verification_url)  # тут саме URL
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img


def generate_ticket_pdf(order, qr_img):
    """Генерує PDF з QR-кодом на готовому шаблоні"""

    # Шлях до шаблону
    template_path = 'static/images/grand_opening_party_ticket.png'

    if not os.path.exists(template_path):
        logger.error(f"Template not found: {template_path}")
        raise FileNotFoundError(f"Ticket template not found at {template_path}")

    # Відкриваємо шаблон
    template_img = Image.open(template_path)
    template_width, template_height = template_img.size

    # Створюємо білий фон якщо шаблон має прозорість
    if template_img.mode in ('RGBA', 'LA') or (template_img.mode == 'P' and 'transparency' in template_img.info):
        white_bg = Image.new('RGB', (template_width, template_height), 'white')
        if template_img.mode != 'RGBA':
            template_img = template_img.convert('RGBA')
        white_bg.paste(template_img, (0, 0), template_img)
        template_img = white_bg
    else:
        template_img = template_img.convert('RGB')

    # Конвертуємо QR в PIL Image
    qr_pil = qr_img.convert('RGBA')

    # Розмір QR-коду
    qr_size = int(template_height * 0.15)
    qr_pil = qr_pil.resize((qr_size, qr_size), Image.Resampling.LANCZOS)

    # Позиція QR-коду (центр QR)
    qr_center_x = int(template_width * 0.82)
    qr_center_y = int(template_height * 0.20)

    # Розраховуємо верхній лівий кут
    qr_x = qr_center_x - (qr_size // 2)
    qr_y = qr_center_y - (qr_size // 2)

    # Накладаємо QR на шаблон
    # Перевіряємо чи template має alpha канал
    if template_img.mode != 'RGBA':
        template_img = template_img.convert('RGBA')

    template_img.paste(qr_pil, (qr_x, qr_y), qr_pil)

    # Конвертуємо в RGB для PDF (без прозорості)
    if template_img.mode == 'RGBA':
        white_bg = Image.new('RGB', template_img.size, 'white')
        white_bg.paste(template_img, (0, 0), template_img)
        template_img = white_bg
    else:
        template_img = template_img.convert('RGB')

    # Створюємо PDF
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    # Зберігаємо комбіноване зображення в буфер
    img_buffer = io.BytesIO()
    template_img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    img_reader = ImageReader(img_buffer)

    # Вставляємо зображення по центру A4 з відступами
    margin = 50
    pdf_width = width - 2 * margin
    pdf_height = height - 2 * margin

    # Зберігаємо пропорції
    aspect_ratio = template_width / template_height

    if pdf_width / aspect_ratio <= pdf_height:
        # Підганяємо по ширині
        final_width = pdf_width
        final_height = pdf_width / aspect_ratio
    else:
        # Підганяємо по висоті
        final_height = pdf_height
        final_width = pdf_height * aspect_ratio

    x = (width - final_width) / 2
    y = (height - final_height) / 2

    # Вставляємо зображення в PDF
    c.drawImage(img_reader, x, y, width=final_width, height=final_height)

    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    return pdf_buffer


def send_ticket_email_with_pdf(order, funnel_tag="night-29-11"):
    """Відправка email з PDF і QR + посилання на Telegram-бота"""
    # === 1. Генеруємо QR для перевірки ===
    qr_img = generate_ticket_qr(order)

    # === 2. Генеруємо PDF з QR ===
    pdf_buffer = generate_ticket_pdf(order, qr_img)

    # === 3. Формуємо посилання на бот ===
    if order.keycrm_lead_id:
        # --- Генеруємо або отримуємо токен ---
        token_obj, _ = BotAccessToken.objects.get_or_create(
            order=order,
            funnel_tag=funnel_tag,
            defaults={"token": uuid.uuid4().hex[:12]}
        )
        bot_url = f"https://t.me/Pasue_club_bot?start={token_obj.token}"
    else:
        bot_url = "https://t.me/Pasue_club_bot"

    # === 4. Формуємо HTML контент листа ===
    html_content = render_to_string('emails/ticket.html', {
        'order': order,
        'bot_url': bot_url
    })

    # Plain text
    text_content = f"Ваш квиток на {order.event_name}\nНомер замовлення: {order.id}"

    # === 5. Формуємо та надсилаємо лист ===
    email = EmailMultiAlternatives(
        subject='Вітаємо у PASUE Club - Твій квиток на атмосферний вечір',
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email]
    )

    email.attach_alternative(html_content, "text/html")
    email.attach(f'ticket_{order.id}.pdf', pdf_buffer.read(), 'application/pdf')
    email.send(fail_silently=False)

    logger.info(f"📩 Email з PDF, QR і посиланням на бота відправлено для замовлення #{order.id}")