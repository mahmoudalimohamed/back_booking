import logging
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import datetime
from django.utils.timezone import localtime
logger = logging.getLogger(__name__)

def generate_ticket_pdf(booking, output_path):
    try:
        logger.info(f"Generating PDF for booking {booking.id}")
        
        # Refresh the booking object to ensure we have latest data
        booking.refresh_from_db()
        
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 20)
        c.setFillColorRGB(0.26, 0.33, 0.53)  # Dark blue
        c.drawCentredString(width / 2, height - 50, "Trip Ticket")
        
        # Passenger Details
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(50, height - 100, "Passenger Details")
        
        c.setFont("Helvetica", 11)
        c.drawString(50, height - 120, f"Name: {booking.customer_name}")
        c.drawString(50, height - 140, f"Phone: {booking.customer_phone}")
        
        # Journey Details
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 170, "Journey Details")
        
        c.setFont("Helvetica", 11)
        c.drawString(50, height - 190, f"From: {booking.trip.start_location}")
        c.drawString(50, height - 210, f"To: {booking.trip.destination}")
        c.drawString(50, height - 230, f"Bus Type: {booking.trip.bus_type}")
        c.drawString(50, height - 250, f"Departure: {localtime(booking.trip.departure_date).strftime('%a, %b %d, %I:%M %p')}")

        # Seat Information
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 300, "Seat Information")
        
        c.setFont("Helvetica", 11)
        seats_str = [str(seat) for seat in booking.selected_seats]
        c.drawString(50, height - 320, f"Seats: {', '.join(seats_str)}")
        
        # Payment Details
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 350, "Payment Details")
        
        c.setFont("Helvetica", 11)
        c.drawString(50, height - 370, f"Total Amount: {booking.total_price} EGP")
        c.drawString(50, height - 390, f"Payment Reference: {booking.payment_reference or 'N/A'}")
        c.drawString(50, height - 410, f"Payment Type: {booking.payment_type or 'N/A'}")
        c.drawString(50, height - 430, f"Payment Date: {localtime(booking.booking_date).strftime('%a, %b %d, %I:%M %p') if booking.booking_date else 'N/A'}")
        
        # Footer
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.39, 0.39, 0.39)
        c.drawCentredString(width / 2, 30, f"Booking ID: {booking.id} • Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        c.showPage()
        c.save()
        logger.info(f"PDF generated successfully for booking {booking.id}")
    except Exception as e:
        logger.error(f"Failed to generate PDF for booking {booking.id}: {str(e)}")
        raise

def send_ticket_email(booking, pdf_path):
    try:
        # Refresh the booking object to ensure we have latest data
        booking.refresh_from_db()
        
        subject = 'Your Trip Ticket'
        message = render_to_string('email/ticket_email.html', {
            'customer_name': booking.customer_name,
            'customer_phone': booking.customer_phone,
            'trip': {
                'start_location': booking.trip.start_location,
                'destination': booking.trip.destination,
                'departure_date': booking.trip.departure_date,
                'bus_type': booking.trip.bus_type
            },
            'selected_seats': booking.selected_seats,
            'total_price': booking.total_price
        })
        
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.EMAIL_HOST_USER,
            to=[booking.user.email]
        )
        email.attach(f'ticket-{booking.id}.pdf', open(pdf_path, 'rb').read(), 'application/pdf')
        email.content_subtype = 'html'
        email.send(fail_silently=False)
        logger.info(f"Email sent successfully for booking {booking.id}")
    except Exception as e:
        logger.error(f"Failed to send email for booking {booking.id}: {str(e)}")
        raise
