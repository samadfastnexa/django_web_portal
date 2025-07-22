from django.db import models
from django.conf import settings

class Dealer(models.Model):
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class MeetingSchedule(models.Model):
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fas_meetings'
    )
    date = models.DateField()
    location = models.CharField(max_length=200)
    min_farmers_required = models.PositiveIntegerField(default=5)
    confirmed_attendees = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Meeting on {self.date} at {self.location}"

class SalesOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('entertained', 'Entertained'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
    )

    schedule = models.ForeignKey(MeetingSchedule, on_delete=models.CASCADE)
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Order #{self.id} - {self.status}"

class SalesOrderAttachment(models.Model):
    sales_order = models.ForeignKey(SalesOrder, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to='sales_order_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
