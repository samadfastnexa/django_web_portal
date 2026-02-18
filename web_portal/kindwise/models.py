from django.db import models
from django.conf import settings


class KindwiseIdentification(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='kindwise_identifications'
	)
	image_name = models.CharField(max_length=255, null=True, blank=True)
	request_payload = models.JSONField()
	response_payload = models.JSONField()
	status = models.CharField(max_length=32, default='success')
	source_ip = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.TextField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = 'kindwise_kindwiseidentification'
		ordering = ['-created_at']

	def __str__(self):
		return f"KindwiseIdentification #{self.id} ({self.status})"
