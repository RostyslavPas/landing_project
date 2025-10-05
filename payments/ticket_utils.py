from django.conf import settings
import io
import qrcode
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from email.mime.image import MIMEImage
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import os
import logging
from django.urls import reverse

logger = logging.getLogger(__name__)


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

# def generate_ticket_pdf(order):
#     """Генерує PDF з квитком"""
#     buffer = io.BytesIO()
#     p = canvas.Canvas(buffer, pagesize=A4)
#     width, height = A4
#
#     # Фон
#     p.setFillColorRGB(0.97, 0.97, 0.97)
#     p.rect(0, 0, width, height, fill=1, stroke=0)
#
#     # Білий контейнер
#     margin = 40
#     box_width = width - 2 * margin
#     box_height = height - 2 * margin
#
#     p.setFillColorRGB(1, 1, 1)
#     p.roundRect(margin, margin, box_width, box_height, 10, fill=1, stroke=0)
#
#     # Header
#     p.setFillColorRGB(0.84, 0.88, 0.80)
#     p.roundRect(margin, height - margin - 100, box_width, 100, 10, fill=1, stroke=0)
#
#     p.setFont('Helvetica-Bold', 24)
#     p.setFillColorRGB(0.12, 0.12, 0.11)
#     p.drawCentredString(width / 2, height - margin - 35, "Ваш квиток підтверджено")
#
#     # Назва події
#     y_pos = height - margin - 150
#     p.setFont('Helvetica-Bold', 18)
#     p.setFillColorRGB(0.2, 0.2, 0.2)
#     p.drawString(margin + 30, y_pos, order.event_name)
#
#     # Деталі
#     y_pos -= 40
#     p.setFont('Helvetica', 12)
#     p.setFillColorRGB(0.3, 0.3, 0.3)
#
#     details = [
#         f"Дата: 29 листопада 2025, 17:00-20:00",
#         f"Місце: м.Київ, вул. Бориса Грінченка 7 (HEAVEN)",
#         f"Сума: {order.amount} грн",
#         f"Номер: {order.id}",
#     ]
#
#     for detail in details:
#         p.drawString(margin + 30, y_pos, detail)
#         y_pos -= 25
#
#     # QR-код
#     qr_img = generate_ticket_qr(order.id)
#     qr_buffer = io.BytesIO()
#     qr_img.save(qr_buffer, format='PNG')
#     qr_buffer.seek(0)
#
#     qr_size = 150
#     qr_x = width / 2 - qr_size / 2
#     qr_y = y_pos - qr_size - 40
#
#     p.drawImage(ImageReader(qr_buffer), qr_x, qr_y, qr_size, qr_size)
#
#     p.setFont('Helvetica', 11)
#     p.setFillColorRGB(0.4, 0.4, 0.4)
#     p.drawCentredString(width / 2, qr_y - 20, "Покажіть цей QR при вході")
#
#     # Footer
#     p.setFont('Helvetica', 10)
#     p.setFillColorRGB(0.5, 0.5, 0.5)
#     p.drawCentredString(width / 2, margin + 30, "Дякуємо, що обрали PASUE")
#
#     p.showPage()
#     p.save()
#     buffer.seek(0)
#     return buffer


# def send_ticket_email_with_pdf(order):
#     """Відправляє email з PDF та QR"""
#     # Генерація QR для HTML
#     qr_img = generate_ticket_qr(order.id)
#     qr_buffer = io.BytesIO()
#     qr_img.save(qr_buffer, format='PNG')
#     qr_buffer.seek(0)
#     qr_bytes = qr_buffer.getvalue()
#
#     # Генерація PDF
#     pdf_buffer = generate_ticket_pdf(order)
#
#     # HTML шаблон
#     html_content = render_to_string('emails/ticket.html', {'order': order})
#
#     subject = f'Ваш квиток на {order.event_name}'
#
#     email = EmailMultiAlternatives(
#         subject=subject,
#         body='Ваш квиток у вкладенні',
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         to=[order.email]
#     )
#
#     email.attach_alternative(html_content, "text/html")
#
#     # QR inline
#     qr_image = MIMEImage(qr_bytes, _subtype='png')
#     qr_image.add_header("Content-ID", "<qrcode.png>")
#     qr_image.add_header("Content-Disposition", "inline", filename="qrcode.png")
#     email.attach(qr_image)
#
#     # PDF вкладення
#     email.attach(f'ticket_{order.id}.pdf', pdf_buffer.read(), 'application/pdf')
#
#     email.send(fail_silently=False)
#     return True


def generate_ticket_pdf(order, qr_img):
    """Генерує красивий PDF квитка з кольорами"""
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

    # === HEADER З ГРАДІЄНТОМ (імітація) ===
    header_height = 120
    c.setFillColorRGB(0.94, 0.90, 0.85)  # #efe5da
    c.roundRect(margin, height - margin - header_height, box_width, header_height, 15, fill=1, stroke=0)

    # Логотип (якщо є локально)
    logo_path = 'static/images/main_logo.png'
    if os.path.exists(logo_path):
        c.drawImage(logo_path, width/2 - 45, height - margin - 90, 90, 90, mask='auto')

    # Заголовок
    c.setFont('Helvetica-Bold', 24)
    c.setFillColorRGB(0.12, 0.12, 0.11)
    c.drawCentredString(width / 2, height - margin - 50, "Вітаємо у PASUE Club ✨")

    # === ТІЛО ===
    y_pos = height - margin - header_height - 50

    # Назва події
    c.setFont('Helvetica-Bold', 20)
    c.setFillColorRGB(0.64, 0.60, 0.34)  # #a27155
    c.drawCentredString(width / 2, y_pos, order.event_name)
    y_pos -= 40

    # === ДЕТАЛІ В РАМЦІ ===
    details_box_height = 120
    details_y = y_pos - details_box_height

    # Фон деталей
    c.setFillColorRGB(0.98, 0.96, 0.95)  # #faf6f1
    c.roundRect(margin + 30, details_y, box_width - 60, details_box_height, 10, fill=1, stroke=0)

    # Ліва бордюра
    c.setFillColorRGB(0.76, 0.60, 0.42)  # #c19a6b
    c.rect(margin + 30, details_y, 4, details_box_height, fill=1, stroke=0)

    # Текст деталей
    c.setFont('Helvetica', 13)
    c.setFillColorRGB(0.2, 0.2, 0.2)

    detail_y = details_y + details_box_height - 25
    details_text = [
        "✨ Коли: 29 листопада 2025, 17:00—20:00",
        "✨ Де: м.Київ, клуб HEAVEN, вул. Бориса Грінченка, 7",
        f"✨ Номер квитка: #{order.id}",
        f"✨ Email: {order.email}",
        f"✨ Сума: {order.amount} грн"
    ]

    for line in details_text:
        c.drawString(margin + 50, detail_y, line)
        detail_y -= 20

    y_pos = details_y - 40

    # === QR КОД ===
    qr_size = 180
    qr_x = width / 2 - qr_size / 2
    qr_y = y_pos - qr_size - 20

    # Білий фон під QR
    c.setFillColorRGB(1, 1, 1)
    c.roundRect(qr_x - 10, qr_y - 10, qr_size + 20, qr_size + 20, 10, fill=1, stroke=0)

    # QR код
    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

    # Текст під QR
    c.setFont('Helvetica', 12)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(width / 2, qr_y - 25, "Покажіть цей QR при вході")

    # === FOOTER ===
    c.setFont('Helvetica', 11)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width / 2, margin + 40, "З любов'ю, команда PASUE Club 💛")
    c.drawCentredString(width / 2, margin + 25, "pasue.club@gmail.com")

    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    return pdf_buffer


def send_ticket_email_with_pdf(order):
    """Відправка email з PDF і QR (HTML і PDF)"""
    # Генеруємо QR для перевірки
    qr_img = generate_ticket_qr(order)

    # Генеруємо PDF з QR
    pdf_buffer = generate_ticket_pdf(order, qr_img)

    # HTML шаблон
    html_content = render_to_string('emails/ticket.html', {'order': order})

    # Plain text (обов'язково!)
    text_content = f"Ваш квиток на {order.event_name}\nНомер замовлення: {order.id}"

    # Створюємо Email
    email = EmailMultiAlternatives(
        subject='Вітаємо у PASUE Club ✨ Твій квиток на атмосферний вечір',
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