from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Crop, CropStage, Trial, TrialTreatment, TrialImage, Product
from .serializers import CropSerializer, CropStageSerializer, TrialSerializer, TrialTreatmentSerializer, ProductSerializer
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.text import slugify
from datetime import date
from django.http import HttpResponse
from io import BytesIO
from .exports import build_trials_workbook, build_trials_pdf

# Optional dependencies for exports
try:
    from openpyxl import Workbook
except Exception:
    Workbook = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
except Exception:
    SimpleDocTemplate = None


class CropViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing crops with their stages.
    Supports form data, multipart, and JSON formats.
    """
    queryset = Crop.objects.all()
    serializer_class = CropSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_view_name(self):
        return "Crop Management"

    def get_view_description(self, html=False):
        return "Manage crops and their cultivation stages"

    @swagger_auto_schema(
        operation_description="Retrieve a list of all crops with their stages",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="List of crops retrieved successfully",
                schema=CropSerializer(many=True)
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new crop with stages using form data format. Use nested notation for stages: stages[0][stage_name], stages[0][days_after_sowing], etc. Example form data: name=Rice, variety=Basmati-385, season=Kharif, stages[0][stage_name]=Transplanting, stages[0][days_after_sowing]=25, stages[0][brand]=Syngenta, stages[0][active_ingredient]=Chlorpyrifos, stages[0][dose_per_acre]=500ml, stages[0][purpose]=Pest control and nutrient management",
        tags=['Crop manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            201: openapi.Response(
                description="Crop created successfully",
                schema=CropSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific crop by ID",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Crop retrieved successfully",
                schema=CropSerializer
            ),
            404: openapi.Response(description="Crop not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a crop and its stages using form data format. Use nested notation for stages: stages[0][stage_name], stages[0][days_after_sowing], etc.",
        tags=['Crop manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Crop updated successfully",
                schema=CropSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Crop not found")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a crop using form data format",
        tags=['Crop manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Crop partially updated successfully",
                schema=CropSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Crop not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a crop and all its stages",
        tags=['Crop manage'],
        responses={
            204: openapi.Response(description="Crop deleted successfully"),
            404: openapi.Response(description="Crop not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class CropStageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual crop stages.
    Supports form data, multipart, and JSON formats.
    """
    queryset = CropStage.objects.all()
    serializer_class = CropStageSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_view_name(self):
        return "Crop Stage Management"

    def get_view_description(self, html=False):
        return "Manage individual crop cultivation stages"

    @swagger_auto_schema(
        operation_description="Retrieve a list of all crop stages",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="List of crop stages retrieved successfully",
                schema=CropStageSerializer(many=True)
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new crop stage using form data format. Example form data: crop=1, stage_name=Germination, days_after_sowing=7, brand=Mahyco, active_ingredient=Thiamethoxam, dose_per_acre=100g, purpose=Seed treatment for early pest protection",
        tags=['Crop manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            201: openapi.Response(
                description="Crop stage created successfully",
                schema=CropStageSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific crop stage by ID",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Crop stage retrieved successfully",
                schema=CropStageSerializer
            ),
            404: openapi.Response(description="Crop stage not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a crop stage using form data format",
        tags=['Crop manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Crop stage updated successfully",
                schema=CropStageSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Crop stage not found")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class TrialViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing field trials.
    """
    queryset = Trial.objects.all()
    serializer_class = TrialSerializer

    @swagger_auto_schema(
        operation_description="Retrieve a list of all trials with their treatments",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="List of trials retrieved successfully",
                schema=TrialSerializer(many=True)
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new trial",
        tags=['Crop manage'],
        responses={
            201: openapi.Response(
                description="Trial created successfully",
                schema=TrialSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific trial by ID with all treatments",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Trial retrieved successfully",
                schema=TrialSerializer
            ),
            404: openapi.Response(description="Trial not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a trial",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Trial updated successfully",
                schema=TrialSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Trial not found")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a trial",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Trial partially updated successfully",
                schema=TrialSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Trial not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a trial and all its treatments",
        tags=['Crop manage'],
        responses={
            204: openapi.Response(description="Trial deleted successfully"),
            404: openapi.Response(description="Trial not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class TrialTreatmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing trial treatments.
    """
    queryset = TrialTreatment.objects.all()
    serializer_class = TrialTreatmentSerializer

    @swagger_auto_schema(
        operation_description="Retrieve a list of all trial treatments",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="List of treatments retrieved successfully",
                schema=TrialTreatmentSerializer(many=True)
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new trial treatment",
        tags=['Crop manage'],
        responses={
            201: openapi.Response(
                description="Treatment created successfully",
                schema=TrialTreatmentSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific trial treatment by ID",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Treatment retrieved successfully",
                schema=TrialTreatmentSerializer
            ),
            404: openapi.Response(description="Treatment not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a trial treatment",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Treatment updated successfully",
                schema=TrialTreatmentSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Treatment not found")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a trial treatment",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Treatment partially updated successfully",
                schema=TrialTreatmentSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Treatment not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a trial treatment",
        tags=['Crop manage'],
        responses={
            204: openapi.Response(description="Treatment deleted successfully"),
            404: openapi.Response(description="Treatment not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products used in trials.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @swagger_auto_schema(
        operation_description="Retrieve a list of all products",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="List of products retrieved successfully",
                schema=ProductSerializer(many=True)
            )
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new product",
        tags=['Crop manage'],
        responses={
            201: openapi.Response(
                description="Product created successfully",
                schema=ProductSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Retrieve a specific product by ID",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Product retrieved successfully",
                schema=ProductSerializer
            ),
            404: openapi.Response(description="Product not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a product",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Product updated successfully",
                schema=ProductSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Product not found")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update a product",
        tags=['Crop manage'],
        responses={
            200: openapi.Response(
                description="Product partially updated successfully",
                schema=ProductSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Product not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a product",
        tags=['Crop manage'],
        responses={
            204: openapi.Response(description="Product deleted successfully"),
            404: openapi.Response(description="Product not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


def station_trials(request, station_slug: str):
    """Render Trials Station page for a given station (separate feature).

    This does not modify existing crop features. If no trials exist for the
    station, sample Sahiwal trials are seeded for preview.
    """
    station_name = station_slug.replace('-', ' ').title()

    trials = list(Trial.objects.filter(station__iexact=station_name).order_by('trial_name'))

    # Handle image uploads (multiple files) per treatment
    if request.method == 'POST':
        try:
            trial_id = int(request.POST.get('trial_id', '0'))
        except ValueError:
            trial_id = 0
        treatment_id = request.POST.get('treatment_id')
        image_type = request.POST.get('image_type')
        files = request.FILES.getlist('images')

        if not files:
            messages.error(request, 'Please select one or more images to upload.')
            return redirect(reverse('station_trials', args=[station_slug]))

        if image_type not in ('before', 'after'):
            messages.error(request, 'Invalid image type. Choose before or after.')
            return redirect(reverse('station_trials', args=[station_slug]))

        try:
            trial = Trial.objects.get(id=trial_id, station__iexact=station_name)
        except Trial.DoesNotExist:
            messages.error(request, 'Trial not found for this station.')
            return redirect(reverse('station_trials', args=[station_slug]))

        try:
            treatment = TrialTreatment.objects.get(id=treatment_id, trial=trial)
        except TrialTreatment.DoesNotExist:
            messages.error(request, 'Selected treatment not found for this trial.')
            return redirect(reverse('station_trials', args=[station_slug]))

        created = 0
        for f in files:
            TrialImage.objects.create(treatment=treatment, image=f, image_type=image_type)
            created += 1
        messages.success(request, f'Uploaded {created} {image_type} image(s) for {treatment.label}.')
        return redirect(reverse('station_trials', args=[station_slug]))

    # Seed the provided Sahiwal sample if empty (for immediate preview only)
    if not trials and station_name == 'Sahiwal':
        t1 = Trial.objects.create(
                station='Sahiwal',
                trial_name='Trial-1',
                location_area='Chak 78/5R',
                crop_variety='Wheat/Fakhr.e.bhakkar',
                application_date=date(2024, 12, 13),
                design_replicates='Replicated',
                water_volume_used='120 L/A',
                previous_sprays='Nil',
                temp_min_c=11.0,
                temp_max_c=21.0,
                humidity_min_percent=57,
                humidity_max_percent=74,
                wind_velocity_kmh=4.0,
                rainfall='Nil'
            )
        t2 = Trial.objects.create(
                station='Sahiwal',
                trial_name='Trial-2',
                location_area='Chak 187/9L',
                crop_variety='Wheat/ FSD 2008',
                application_date=date(2024, 12, 14),
                design_replicates='Replicated',
                water_volume_used='120 L/A',
                previous_sprays='Nil',
                temp_min_c=10.0,
                temp_max_c=22.0,
                humidity_min_percent=55,
                humidity_max_percent=87,
                wind_velocity_kmh=4.0,
                rainfall='Nil'
            )
        # Seed a few treatment rows for each trial
        for idx, trial in enumerate([t1, t2], start=1):
            for tnum in range(1, 4):
                TrialTreatment.objects.create(
                    trial=trial,
                    label=f"T{tnum}",
                    crop_stage_soil="Loamy soil, adequate moisture",
                    pest_stage_start="Aphids at early infestation",
                    crop_safety_stress_rating=5,
                    details="Aphids ~40% control observed after 7 days",
                    growth_improvement_type="Improved tillering",
                    best_dose="120 ml/acre",
                    others="No phytotoxicity noted"
                )
        trials = [t1, t2]

    context = {
        'station': station_name,
        'trials': trials,
    }
    return render(request, 'crop_manage/trials_station.html', context)


def export_trials_xlsx(request):
    """Export all Trials and Treatments to a styled, sized XLSX."""
    try:
        trials_qs = Trial.objects.all()
        treatments_qs = TrialTreatment.objects.select_related('trial', 'product').all()
        output = build_trials_workbook(trials_qs, treatments_qs)
        resp = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        resp['Content-Disposition'] = 'attachment; filename="trials_report.xlsx"'
        return resp
    except Exception as e:
        return HttpResponse(f'Failed to build XLSX: {e}', status=500)


def export_trials_pdf(request):
    """Export all Trials and Treatments to a styled, page-safe PDF."""
    try:
        trials_qs = Trial.objects.all()
        treatments_qs = TrialTreatment.objects.select_related('trial', 'product').all()
        buffer = build_trials_pdf(trials_qs, treatments_qs)
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = 'attachment; filename="trials_report.pdf"'
        return resp
    except Exception as e:
        return HttpResponse(f'Failed to build PDF: {e}', status=500)

    @swagger_auto_schema(
        operation_description="Partially update a crop stage using form data format",
        tags=['Crop manage'],
        consumes=['application/x-www-form-urlencoded', 'multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Crop stage partially updated successfully",
                schema=CropStageSerializer
            ),
            400: openapi.Response(description="Bad request - validation errors"),
            404: openapi.Response(description="Crop stage not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a crop stage",
        tags=['Crop manage'],
        responses={
            204: openapi.Response(description="Crop stage deleted successfully"),
            404: openapi.Response(description="Crop stage not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


# =====================
# Reports pages (simple templates)
# =====================
def reports_index(request):
    """Landing page for Crop_Manage reports."""
    return render(request, 'crop_manage/reports/index.html')


def weed_efficacy_report(request):
    """Render weed efficacy charts for Wheat based on provided datasets."""
    return render(request, 'crop_manage/reports/weed_efficacy.html')
