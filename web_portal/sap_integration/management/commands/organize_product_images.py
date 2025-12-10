"""
Django management command to organize product images into database-specific folders.

Usage:
    python manage.py organize_product_images

This command will:
1. Scan the media/product_images/ directory for image files
2. Prompt for which database each image belongs to (4B-BIO or 4B-ORANG)
3. Move/copy images to the appropriate database folder
"""

import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Organize product images into database-specific folders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='',
            help='Source directory containing images (default: media/product_images/)',
        )
        parser.add_argument(
            '--database',
            type=str,
            choices=['4B-BIO', '4B-ORANG'],
            help='Target database folder (if not specified, will prompt for each file)',
        )
        parser.add_argument(
            '--copy',
            action='store_true',
            help='Copy files instead of moving them',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually moving files',
        )

    def handle(self, *args, **options):
        # Get media root
        media_root = settings.MEDIA_ROOT if hasattr(settings, 'MEDIA_ROOT') else os.path.join(settings.BASE_DIR, 'media')
        
        # Set up directories
        product_images_dir = Path(media_root) / 'product_images'
        source_dir = Path(options['source']) if options['source'] else product_images_dir
        
        if not source_dir.exists():
            raise CommandError(f'Source directory does not exist: {source_dir}')
        
        # Target folders
        bio_folder = product_images_dir / '4B-BIO'
        orang_folder = product_images_dir / '4B-ORANG'
        
        # Ensure target folders exist
        bio_folder.mkdir(parents=True, exist_ok=True)
        orang_folder.mkdir(parents=True, exist_ok=True)
        
        # Find all image files in source directory
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(source_dir.glob(f'*{ext}'))
            image_files.extend(source_dir.glob(f'*{ext.upper()}'))
        
        if not image_files:
            self.stdout.write(self.style.WARNING(f'No image files found in {source_dir}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(image_files)} image file(s) in {source_dir}'))
        
        # Process each image
        moved_count = 0
        skipped_count = 0
        
        for image_file in image_files:
            # Skip if already in a database folder
            if image_file.parent.name in ('4B-BIO', '4B-ORANG'):
                self.stdout.write(self.style.WARNING(f'Skipping {image_file.name} (already in database folder)'))
                skipped_count += 1
                continue
            
            # Skip README files
            if image_file.name == 'README.md':
                skipped_count += 1
                continue
            
            # Determine target database
            if options['database']:
                target_db = options['database']
            else:
                # Prompt user
                self.stdout.write(f'\nImage: {image_file.name}')
                response = input('Enter database (1=4B-BIO, 2=4B-ORANG, s=skip): ').strip().lower()
                
                if response == '1':
                    target_db = '4B-BIO'
                elif response == '2':
                    target_db = '4B-ORANG'
                elif response == 's':
                    self.stdout.write(self.style.WARNING(f'Skipped {image_file.name}'))
                    skipped_count += 1
                    continue
                else:
                    self.stdout.write(self.style.ERROR(f'Invalid input. Skipped {image_file.name}'))
                    skipped_count += 1
                    continue
            
            # Determine target path
            target_folder = bio_folder if target_db == '4B-BIO' else orang_folder
            target_path = target_folder / image_file.name
            
            # Check if target already exists
            if target_path.exists():
                self.stdout.write(self.style.WARNING(f'Target already exists: {target_path}. Skipping.'))
                skipped_count += 1
                continue
            
            # Perform operation
            if options['dry_run']:
                action = 'Would copy' if options['copy'] else 'Would move'
                self.stdout.write(f'{action}: {image_file.name} -> {target_db}/')
            else:
                try:
                    if options['copy']:
                        shutil.copy2(image_file, target_path)
                        self.stdout.write(self.style.SUCCESS(f'Copied: {image_file.name} -> {target_db}/'))
                    else:
                        shutil.move(str(image_file), str(target_path))
                        self.stdout.write(self.style.SUCCESS(f'Moved: {image_file.name} -> {target_db}/'))
                    moved_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing {image_file.name}: {str(e)}'))
                    skipped_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*50)
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS('DRY RUN - No files were actually moved'))
        self.stdout.write(self.style.SUCCESS(f'Processed: {moved_count} file(s)'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count} file(s)'))
        self.stdout.write('='*50)
