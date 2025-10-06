import io
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


# def generate_ticket_pdf(order, qr_img):
#     """Генерує PDF з QR-кодом на готовому шаблоні"""
#
#     # Шлях до шаблону
#     template_path = 'static/images/grand_opening_party_ticket.png'
#
#     if not os.path.exists(template_path):
#         logger.error(f"Template not found: {template_path}")
#         raise FileNotFoundError(f"Ticket template not found at {template_path}")
#
#     # Відкриваємо шаблон
#     template_img = Image.open(template_path)
#     template_width, template_height = template_img.size
#
#     # Конвертуємо QR в PIL Image
#     qr_pil = qr_img.convert('RGB')
#
#     # Розмір QR-коду - підганяємо під правий блок квитка
#     qr_size = int(template_height * 0.35)  # 60% висоти квитка
#     qr_pil = qr_pil.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
#
#     # Позиція QR-коду (праворуч в пустому блоці)
#     # Квиток має пропорції приблизно 2:1 (ліва частина з текстом + права порожня)
#     qr_x = int(template_width * 0.70)  # починаємо з 68% ширини
#     qr_y = (template_height - qr_size) // 2  # по центру по вертикалі
#
#     # Накладаємо QR на шаблон
#     template_img.paste(qr_pil, (qr_x, qr_y))
#
#     # Створюємо PDF
#     pdf_buffer = io.BytesIO()
#     c = canvas.Canvas(pdf_buffer, pagesize=A4)
#     width, height = A4
#
#     # Зберігаємо комбіноване зображення в буфер
#     img_buffer = io.BytesIO()
#     template_img.save(img_buffer, format='PNG')
#     img_buffer.seek(0)
#     img_reader = ImageReader(img_buffer)
#
#     # Розраховуємо розміри для A4
#     # Зберігаємо пропорції шаблону
#     aspect_ratio = template_width / template_height
#
#     if aspect_ratio > (width / height):
#         # Шаблон ширший - підганяємо по ширині
#         pdf_width = width - 40  # margins
#         pdf_height = pdf_width / aspect_ratio
#         x = 20
#         y = (height - pdf_height) / 2
#     else:
#         # Шаблон вищий - підганяємо по висоті
#         pdf_height = height - 40  # margins
#         pdf_width = pdf_height * aspect_ratio
#         x = (width - pdf_width) / 2
#         y = 20
#
#     # Вставляємо зображення в PDF
#     c.drawImage(img_reader, x, y, width=pdf_width, height=pdf_height)
#
#     c.showPage()
#     c.save()
#     pdf_buffer.seek(0)
#
#     return pdf_buffer
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
    qr_size = int(template_height * 0.10)
    qr_pil = qr_pil.resize((qr_size, qr_size), Image.Resampling.LANCZOS)

    # Позиція QR-коду
    qr_x = int(template_width * 0.57 - qr_size / 2)
    qr_y = int(template_height * 0.14 - qr_size / 2)

    # Накладаємо QR на шаблон
    if template_img.mode != 'RGBA':
        template_img = template_img.convert('RGBA')

    template_img.paste(qr_pil, (qr_x, qr_y), qr_pil)

    # Конвертуємо назад в RGB для PDF
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


def send_ticket_email_with_pdf(order):
    """Відправка email з PDF і QR"""
    # Генеруємо QR для перевірки
    qr_img = generate_ticket_qr(order)

    # Генеруємо PDF з QR
    pdf_buffer = generate_ticket_pdf(order, qr_img)

    # HTML шаблон
    html_content = render_to_string('emails/ticket.html', {'order': order})

    # Plain text
    text_content = f"Ваш квиток на {order.event_name}\nНомер замовлення: {order.id}"

    # Створюємо Email
    email = EmailMultiAlternatives(
        subject='Вітаємо у PASUE Club - Твій квиток на атмосферний вечір',
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email]
    )

    # Додаємо HTML альтернативу
    email.attach_alternative(html_content, "text/html")

    # Додаємо PDF
    email.attach(f'ticket_{order.id}.pdf', pdf_buffer.read(), 'application/pdf')

    # Відправка
    email.send(fail_silently=False)
    logger.info(f"Email з PDF та QR відправлено для замовлення {order.id}")