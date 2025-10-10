from django.core.management.base import BaseCommand
from farmerMeetingDataEntry.models import FieldDayAttendance, FieldDayAttendanceCrop


class Command(BaseCommand):
    help = 'Migrate existing comma-separated crops to FieldDayAttendanceCrop model'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting crop migration...'))
        
        # Get all attendance records with crops
        attendances = FieldDayAttendance.objects.exclude(crop__isnull=True).exclude(crop__exact='')
        
        migrated_count = 0
        for attendance in attendances:
            if attendance.crop and ',' in attendance.crop:
                # Split comma-separated crops
                crops = [crop.strip() for crop in attendance.crop.split(',') if crop.strip()]
                
                # Create FieldDayAttendanceCrop records
                for crop_name in crops:
                    FieldDayAttendanceCrop.objects.get_or_create(
                        attendance=attendance,
                        crop_name=crop_name,
                        defaults={'acreage': attendance.acreage / len(crops)}  # Distribute acreage evenly
                    )
                
                migrated_count += 1
                self.stdout.write(f'Migrated crops for attendance {attendance.id}: {crops}')
            
            elif attendance.crop:
                # Single crop
                FieldDayAttendanceCrop.objects.get_or_create(
                    attendance=attendance,
                    crop_name=attendance.crop,
                    defaults={'acreage': attendance.acreage}
                )
                migrated_count += 1
                self.stdout.write(f'Migrated single crop for attendance {attendance.id}: {attendance.crop}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully migrated crops for {migrated_count} attendance records')
        )