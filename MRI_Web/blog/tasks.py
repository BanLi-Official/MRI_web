from celery import shared_task
from .models import ProcessedImage

@shared_task
def process_image_task(pk):
    obj = ProcessedImage.objects.get(pk=pk)
    obj.process_image()
