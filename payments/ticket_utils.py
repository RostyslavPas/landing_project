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

logger = logging.getLogger(__name__)

# Шлях до шрифту в static
font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
bold_font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans-Bold.ttf")

# Реєструємо шрифти
pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', bold_font_path))

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
    """Генерує красивий PDF квитка з підтримкою кирилиці"""
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_reader = ImageReader(qr_buffer)

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    # === ФОН ===
    c.setFillColorRGB(0.99, 0.98, 0.97)  # #fdfaf7
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # === БІЛИЙ КОНТЕЙНЕР ===
    margin = 40
    box_width = width - 2 * margin
    box_height = height - 2 * margin

    c.setFillColorRGB(1, 1, 1)
    c.roundRect(margin, margin, box_width, box_height, 15, fill=1, stroke=0)

    # Тінь контейнера
    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.setLineWidth(1)
    c.roundRect(margin, margin, box_width, box_height, 15, fill=0, stroke=1)

    # === HEADER З ГРАДІЄНТОМ ===
    header_height = 140
    c.setFillColorRGB(0.94, 0.90, 0.85)  # #efe5da
    c.roundRect(margin, height - margin - header_height, box_width, header_height, 15, fill=1, stroke=0)

    # Логотип
    logo_path = 'static/images/main_logo.png'
    logo_y = height - margin - 115
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, width / 2 - 40, logo_y, 80, 80, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            logger.warning(f"Cannot load logo image: {e}")

    # Заголовок
    c.setFont(FONT_BOLD, 22)
    c.setFillColorRGB(0.12, 0.12, 0.11)
    c.drawCentredString(width / 2, height - margin - 35, "Вітаємо у PASUE Club")

    # === ТІЛО ===
    y_pos = height - margin - header_height - 40

    # Назва події
    c.setFont(FONT_BOLD, 18)
    c.setFillColorRGB(0.64, 0.44, 0.33)  # #a27155
    c.drawCentredString(width / 2, y_pos, order.event_name)
    y_pos -= 35

    # === ДЕТАЛІ В РАМЦІ ===
    details_box_height = 140
    details_y = y_pos - details_box_height

    # Фон деталей
    c.setFillColorRGB(0.98, 0.96, 0.95)  # #faf6f1
    c.roundRect(margin + 30, details_y, box_width - 60, details_box_height, 10, fill=1, stroke=0)

    # Ліва бордюра
    c.setFillColorRGB(0.76, 0.60, 0.42)  # #c19a6b
    c.rect(margin + 30, details_y, 4, details_box_height, fill=1, stroke=0)

    # Текст деталей
    c.setFont(FONT_NORMAL, 12)
    c.setFillColorRGB(0.2, 0.2, 0.2)

    detail_y = details_y + details_box_height - 25
    details_text = [
        "Коли: 29 листопада 2025, 17:00-20:00",
        "Де: м.Київ, клуб HEAVEN",
        "    вул. Бориса Грінченка, 7",
        f"Номер квитка: #{order.id}",
        f"Email: {order.email}",
        f"Сума: {order.amount} грн"
    ]

    for line in details_text:
        c.drawString(margin + 50, detail_y, line)
        detail_y -= 22

    y_pos = details_y - 30

    # === QR КОД ===
    qr_size = 170
    qr_x = width / 2 - qr_size / 2
    qr_y = y_pos - qr_size - 20

    # Білий фон під QR з рамкою
    c.setFillColorRGB(1, 1, 1)
    c.roundRect(qr_x - 15, qr_y - 15, qr_size + 30, qr_size + 30, 10, fill=1, stroke=0)

    c.setStrokeColorRGB(0.76, 0.60, 0.42)  # #c19a6b
    c.setLineWidth(2)
    c.roundRect(qr_x - 15, qr_y - 15, qr_size + 30, qr_size + 30, 10, fill=0, stroke=1)

    # QR код
    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

    # Текст під QR
    c.setFont(FONT_NORMAL, 11)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(width / 2, qr_y - 30, "Покажіть цей QR при вході")

    # === FOOTER ===
    c.setFont(FONT_NORMAL, 10)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width / 2, margin + 45, "З любов'ю, команда PASUE Club")
    c.drawCentredString(width / 2, margin + 30, "pasue.club@gmail.com")

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