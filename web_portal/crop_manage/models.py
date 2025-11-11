from django.db import models
from django.conf import settings


class Crop(models.Model):
    name = models.CharField(max_length=100, help_text="Crop common name (e.g., Wheat, Rice)")
    variety = models.CharField(max_length=100, blank=True, null=True, help_text="Optional variety/hybrid (e.g., HD-2967)")
    season = models.CharField(max_length=50, blank=True, null=True, help_text="Growing season (e.g., Rabi/Kharif)")
    remarks = models.TextField(blank=True, null=True, help_text="Any additional notes about the crop")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.variety})" if self.variety else self.name


class CropStage(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="stages", help_text="Select the crop this stage belongs to")
    stage_name = models.CharField(max_length=200, help_text="Stage title (e.g., Pre-sowing, Tillering)")
    days_after_sowing = models.IntegerField(help_text="Number of days from sowing to this stage")
    brand = models.CharField(max_length=200, blank=True, null=True, help_text="Brand/manufacturer of product used at this stage")
    active_ingredient = models.CharField(max_length=200, blank=True, null=True, help_text="Active ingredient(s) used (e.g., Thiram + Carboxin)")
    dose_per_acre = models.CharField(max_length=100, blank=True, null=True, help_text="Dose per acre (units included, e.g., 2.5 gm/kg seed)")
    purpose = models.TextField(blank=True, null=True, help_text="Purpose or objective of this stage/treatment")
    remarks = models.TextField(blank=True, null=True, help_text="Additional notes or instructions")

    def __str__(self):
        return f"{self.crop.name} - {self.stage_name}"


class CropStageImage(models.Model):
    """Multiple images can be attached to a crop stage."""
    crop_stage = models.ForeignKey(CropStage, on_delete=models.CASCADE, related_name="images")
    image = models.FileField(upload_to="crop_stage_images/")
    caption = models.CharField(max_length=200, blank=True, null=True)
    taken_at = models.DateField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["crop_stage", "uploaded_at"]
        verbose_name = "Crop Stage Image"
        verbose_name_plural = "Crop Stage Images"

    def __str__(self):
        return f"{self.crop_stage} image"


class Product(models.Model):
    """Simple catalog of products used in trials.

    Kept minimal: name, brand, active ingredient, formulation, and remarks.
    """
    name = models.CharField(max_length=150, help_text="Commercial product name")
    brand = models.CharField(max_length=150, blank=True, null=True, help_text="Company/brand (e.g., UPL, Bayer)")
    active_ingredient = models.CharField(max_length=200, blank=True, null=True, help_text="Active ingredient(s) and concentration")
    formulation = models.CharField(max_length=100, blank=True, null=True, help_text="Formulation type (e.g., EC, SC, WG)")
    remarks = models.TextField(blank=True, null=True, help_text="Extra information, label guidance, or local notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "brand"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        if self.brand:
            return f"{self.brand} - {self.name}"
        return self.name


class Trial(models.Model):
    """Trials Station record (kept separate from Crop/CropStage).

    Minimal fields based on provided structure. This is intentionally
    independent to avoid changing any existing functionality.
    """

    # Station and trial info
    station = models.CharField(max_length=100)
    trial_name = models.CharField(max_length=100)

    # Location and crop details
    location_area = models.CharField(max_length=200)
    crop_variety = models.CharField(max_length=200)

    # Dates and design
    application_date = models.DateField()
    design_replicates = models.CharField(max_length=100)

    # Operational details
    water_volume_used = models.CharField(max_length=50)
    previous_sprays = models.CharField(max_length=200, blank=True, null=True)

    # Weather info
    temp_min_c = models.DecimalField(max_digits=4, decimal_places=1)
    temp_max_c = models.DecimalField(max_digits=4, decimal_places=1)
    humidity_min_percent = models.PositiveIntegerField()
    humidity_max_percent = models.PositiveIntegerField()
    wind_velocity_kmh = models.DecimalField(max_digits=4, decimal_places=1)
    rainfall = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["station", "trial_name"]
        verbose_name = "Trial"
        verbose_name_plural = "Trials"

    def __str__(self):
        return f"{self.station} - {self.trial_name}"


class TrialTreatment(models.Model):
    """A treatment row within a Trial remarks table."""
    trial = models.ForeignKey(Trial, on_delete=models.CASCADE, related_name="treatments")
    label = models.CharField(max_length=20, help_text="e.g., T1, T2, Treatment 1")

    # Product applied in this treatment
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="treatments")

    crop_stage_soil = models.TextField(blank=True, null=True)
    pest_stage_start = models.TextField(blank=True, null=True)
    crop_safety_stress_rating = models.PositiveSmallIntegerField(blank=True, null=True)
    details = models.TextField(blank=True, null=True, help_text="Type of insect/weeds/disease and % control")
    growth_improvement_type = models.TextField(blank=True, null=True)
    best_dose = models.CharField(max_length=100, blank=True, null=True)
    others = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["trial", "label"]

    def __str__(self):
        return f"{self.trial} - {self.label}"


class TrialImage(models.Model):
    """Multiple images per treatment, categorized as before/after."""
    BEFORE = "before"
    AFTER = "after"
    IMAGE_TYPE_CHOICES = [(BEFORE, "Before"), (AFTER, "After")]

    treatment = models.ForeignKey(TrialTreatment, on_delete=models.CASCADE, related_name="images")
    image = models.FileField(upload_to="trial_images/")
    image_type = models.CharField(max_length=10, choices=IMAGE_TYPE_CHOICES)
    caption = models.CharField(max_length=200, blank=True, null=True)
    taken_at = models.DateField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["treatment", "image_type", "uploaded_at"]

    def __str__(self):
        return f"{self.treatment} - {self.image_type}"

class Pest(models.Model):
    """Catalog of pests: weeds, insects, diseases."""
    WEED = "weed"
    INSECT = "insect"
    DISEASE = "disease"
    CATEGORY_CHOICES = [
        (WEED, "Weed"),
        (INSECT, "Insect"),
        (DISEASE, "Disease"),
    ]

    name = models.CharField(max_length=120, unique=True, help_text="Common name of pest/species or pathogen")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, help_text="Select whether this is a weed, insect, or disease")
    species_group = models.CharField(max_length=120, blank=True, null=True, help_text="Optional group/genus (e.g., Echinochloa spp., Aphididae)")
    life_stages = models.CharField(max_length=120, blank=True, null=True, help_text="e.g., Egg, Larva, Nymph, Adult")
    notes = models.TextField(blank=True, null=True, help_text="Identification cues, local names, or any remarks")

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class PestManagementGuideline(models.Model):
    """Guidelines per pest and optionally per crop (herbicide/insecticide/fungicide)."""
    HERBICIDE = "herbicide"
    INSECTICIDE = "insecticide"
    FUNGICIDE = "fungicide"
    CONTROL_CHOICES = [
        (HERBICIDE, "Herbicide"),
        (INSECTICIDE, "Insecticide"),
        (FUNGICIDE, "Fungicide"),
    ]

    pest = models.ForeignKey(Pest, on_delete=models.CASCADE, related_name="guidelines", help_text="Select the target pest for this guideline")
    crop = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True, related_name="pest_guidelines", help_text="Optional: limit guideline to a specific crop")
    control_category = models.CharField(max_length=20, choices=CONTROL_CHOICES, help_text="Type of control: Herbicide, Insecticide, or Fungicide")
    type_label = models.CharField(max_length=100, help_text="e.g., Pre-emergence, Chewing, Preventive, Seed Treatment")
    time_of_application = models.CharField(max_length=200, blank=True, null=True, help_text="When to apply relative to crop/pest stage")
    water_volume = models.CharField(max_length=50, blank=True, null=True, help_text="Spray volume (e.g., L/acre or L/ha)")
    nozzles = models.CharField(max_length=100, blank=True, null=True, help_text="Recommended nozzle type/model")
    number_of_applications = models.CharField(max_length=50, blank=True, null=True, help_text="Total sprays and intervals (e.g., 2–3 sprays, 10-day interval)")
    observation_time = models.CharField(max_length=300, blank=True, null=True, help_text="When efficacy should be observed/measured")
    method_of_application = models.CharField(max_length=200, blank=True, null=True, help_text="Application method (e.g., foliar spray, seed treatment, drench)")
    method_of_observation = models.CharField(max_length=200, blank=True, null=True, help_text="Observation method (e.g., visual scale, counts per m²)")
    trial_starting_stage = models.CharField(max_length=200, blank=True, null=True, help_text="Crop or pest stage at trial start")
    products = models.ManyToManyField('Product', blank=True, related_name='pest_guidelines', help_text="Products applicable under this guideline")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pest", "crop", "control_category", "type_label"]
        verbose_name = "Pest Management Guideline"
        verbose_name_plural = "Pest Management Guidelines"

    def __str__(self):
        crop_part = f" for {self.crop.name}" if self.crop else ""
        return f"{self.pest.name} - {self.get_control_category_display()} - {self.type_label}{crop_part}"


# -------- Trial Observation & Remarks System ---------

class TrialInitCondition(models.Model):
    """Baseline trial conditions prior to application."""
    trial = models.OneToOneField('Trial', on_delete=models.CASCADE, related_name='init_condition', help_text="Linked trial; one baseline record per trial")
    crop_health_ok = models.BooleanField(default=True, help_text="Crop must be healthy with no stress symptoms")
    weed_growth_stage = models.CharField(max_length=120, blank=True, null=True, help_text="e.g., 3–5 leaf stage for weeds")
    meets_requirements = models.BooleanField(default=False, help_text="Whether baseline meets initiation criteria")
    notes = models.TextField(blank=True, null=True, help_text="Any remarks about baseline setup and observations")

    def __str__(self):
        return f"InitConditions for Trial {self.trial_id}"


class EnvironmentalCondition(models.Model):
    """Environmental conditions around application for a specific treatment."""
    trial_treatment = models.ForeignKey('TrialTreatment', on_delete=models.CASCADE, related_name='environmental_conditions', help_text="Treatment row this environment snapshot belongs to")
    recorded_at = models.DateTimeField(auto_now_add=True, help_text="Auto-recorded timestamp when conditions were captured")
    temperature_c = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Ambient temperature (°C) at application/observation")
    humidity_pct = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Relative humidity (%)")
    wind_speed_kmh = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Wind speed (km/h) measured at canopy height")
    soil_moisture_pct = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Soil moisture (%) or relative scale")
    rainfall_24h_mm = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Rainfall in last 24 hours (mm)")
    notes = models.TextField(blank=True, null=True, help_text="Additional weather details or context")

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"Env @TT {self.trial_treatment_id} ({self.recorded_at:%Y-%m-%d})"


class SpeciesPerformanceObservation(models.Model):
    """Efficacy observations against specific weed/pest species at given DAA."""
    trial_treatment = models.ForeignKey('TrialTreatment', on_delete=models.CASCADE, related_name='species_observations', help_text="Treatment under which the observation is recorded")
    pest = models.ForeignKey(Pest, on_delete=models.CASCADE, related_name='species_observations', help_text="Observed target species/pest")
    observation_day = models.IntegerField(help_text="Days after application")
    control_efficacy_pct = models.DecimalField(max_digits=5, decimal_places=2, help_text="0–100%")
    method = models.CharField(max_length=60, blank=True, null=True, help_text="e.g., Visual Assessment, Counting per sq.m")
    dose_ml_per_acre = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True, help_text="Dose used for this observation (ml per acre)")
    notes = models.TextField(blank=True, null=True, help_text="Extra context: plot conditions, anomalies, etc.")

    class Meta:
        ordering = ['trial_treatment', 'pest', 'observation_day']

    def __str__(self):
        return f"{self.pest.name} DAA-{self.observation_day}: {self.control_efficacy_pct}%"


class DoseResponseObservation(models.Model):
    """Dose-response tracking across observations for a treatment."""
    trial_treatment = models.ForeignKey('TrialTreatment', on_delete=models.CASCADE, related_name='dose_response', help_text="Treatment this dose-response record belongs to")
    dose_ml_per_acre = models.DecimalField(max_digits=7, decimal_places=2, help_text="Dose evaluated (ml per acre)")
    observation_day = models.IntegerField(help_text="Days after application")
    efficacy_pct = models.DecimalField(max_digits=5, decimal_places=2, help_text="Observed efficacy (%)")
    notes = models.TextField(blank=True, null=True, help_text="Notes about response or variability")

    class Meta:
        ordering = ['trial_treatment', 'dose_ml_per_acre', 'observation_day']

    def __str__(self):
        return f"Dose {self.dose_ml_per_acre} ml/A DAA-{self.observation_day}: {self.efficacy_pct}%"


class ComparativePerformance(models.Model):
    """Comparison against reference products for the same trial treatment."""
    trial_treatment = models.ForeignKey('TrialTreatment', on_delete=models.CASCADE, related_name='comparisons', help_text="Treatment row being compared")
    reference_product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='comparisons', help_text="Comparator/reference product")
    observation_day = models.IntegerField(help_text="Days after application")
    efficacy_pct = models.DecimalField(max_digits=5, decimal_places=2, help_text="Observed efficacy (%) of the reference product")
    notes = models.TextField(blank=True, null=True, help_text="Comparison notes or anomalies")

    class Meta:
        ordering = ['trial_treatment', 'reference_product', 'observation_day']

    def __str__(self):
        return f"Ref {self.reference_product.name} DAA-{self.observation_day}: {self.efficacy_pct}%"


class Recommendation(models.Model):
    """Product recommendation decision derived from trial data."""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='recommendations', help_text="Recommended product based on trial observations")
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='recommendations', help_text="Target crop for recommendation")
    pest = models.ForeignKey(Pest, on_delete=models.CASCADE, related_name='recommendations', help_text="Target pest for recommendation")
    recommended_dose_ml_per_acre = models.DecimalField(max_digits=7, decimal_places=2, help_text="Recommended dose (ml per acre)")
    basis = models.TextField(help_text="Evidence and rationale for recommendation")
    source_trial = models.ForeignKey('Trial', on_delete=models.SET_NULL, null=True, blank=True, related_name='derived_recommendations', help_text="Optional: link to the trial that supports this recommendation")
    success_metrics = models.TextField(blank=True, null=True, help_text="Criteria used to judge efficacy and success")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['crop', 'pest', 'product']

    def __str__(self):
        return f"{self.product.name} {self.recommended_dose_ml_per_acre} ml/A for {self.crop.name} vs {self.pest.name}"


class TrialRepetitionPlan(models.Model):
    """Protocol for repeating trials to optimize dosage."""
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='repetition_plans', help_text="Crop planned for repeated trials")
    pest = models.ForeignKey(Pest, on_delete=models.CASCADE, related_name='repetition_plans', help_text="Target pest for repeated trials")
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='repetition_plans', help_text="Product to be evaluated in repetitions")
    dose_min_ml_per_acre = models.DecimalField(max_digits=7, decimal_places=2, help_text="Minimum planned dose (ml per acre)")
    dose_max_ml_per_acre = models.DecimalField(max_digits=7, decimal_places=2, help_text="Maximum planned dose (ml per acre)")
    adjustment_increment_ml_per_acre = models.DecimalField(max_digits=7, decimal_places=2, help_text="Step size to adjust dose between repetitions (ml per acre)")
    success_metrics = models.TextField(help_text="How success is defined (e.g., >85% control at DAA-21)")
    status = models.CharField(max_length=30, default='planned', help_text="Trial repetition status: planned/scheduled/completed")
    notes = models.TextField(blank=True, null=True, help_text="Additional plan notes or considerations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['crop', 'pest', 'product']

    def __str__(self):
        return f"Repetition Plan: {self.product.name} on {self.crop.name} vs {self.pest.name}"
