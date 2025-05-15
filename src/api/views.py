from django.shortcuts import render
from django.db.models import Case, When, IntegerField
from rest_framework import viewsets, permissions, filters
from rest_framework import generics
from .models import Nutrient, Ingredient, PersonProfile, MealComponent, MealPlan, FoodPortion, IngredientNutrientLink, IngredientUsage, DietaryReferenceValue
from .serializers import (
    NutrientSerializer, 
    IngredientSerializer, 
    PersonProfileSerializer, 
    MealComponentSerializer, 
    MealPlanSerializer,
    IngredientSearchSerializer,
    FoodPortionSerializer,
    IngredientNutrientLinkSerializer,
    IngredientUsageSerializer,
    DietaryReferenceValueSerializer
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from collections import defaultdict

# Create your views here.

class NutrientViewSet(viewsets.ModelViewSet):
    """API endpoint that allows nutrients to be viewed or edited."""
    queryset = Nutrient.objects.all().order_by('name')
    serializer_class = NutrientSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Example permission

class IngredientViewSet(viewsets.ModelViewSet):
    """API endpoint that allows ingredients to be viewed or edited."""
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer

class PersonProfileViewSet(viewsets.ModelViewSet):
    """API endpoint that allows person profiles to be viewed or edited."""
    queryset = PersonProfile.objects.all().order_by('name')
    serializer_class = PersonProfileSerializer

class MealComponentViewSet(viewsets.ModelViewSet):
    """API endpoint that allows meal components to be viewed or edited."""
    queryset = MealComponent.objects.all().order_by('name')
    serializer_class = MealComponentSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'category_tag', 'description_recipe']
    ordering_fields = ['name', 'category_tag']
    ordering = ['name']

class MealPlanViewSet(viewsets.ModelViewSet):
    """API endpoint that allows meal plans to be viewed or edited."""
    queryset = MealPlan.objects.all().order_by('-creation_date')
    serializer_class = MealPlanSerializer

class FoodPortionViewSet(viewsets.ModelViewSet):
    """API endpoint that allows food portions to be viewed or edited."""
    queryset = FoodPortion.objects.all().order_by('ingredient__name', 'sequence_number')
    serializer_class = FoodPortionSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Example permission

class IngredientNutrientLinkViewSet(viewsets.ModelViewSet):
    """API endpoint that allows ingredient-nutrient links to be viewed or edited."""
    queryset = IngredientNutrientLink.objects.all()
    serializer_class = IngredientNutrientLinkSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class IngredientUsageViewSet(viewsets.ModelViewSet):
    """API endpoint that allows ingredient usages to be viewed or edited."""
    queryset = IngredientUsage.objects.all()
    serializer_class = IngredientUsageSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Example permission

class DietaryReferenceValueViewSet(viewsets.ModelViewSet):
    """API endpoint that allows dietary reference values to be viewed or edited."""
    queryset = DietaryReferenceValue.objects.all()
    serializer_class = DietaryReferenceValueSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Example permission

# Note: For the through models (IngredientNutrientLink, IngredientUsage),
# it's often not necessary to create separate ViewSets if they are primarily managed
# through their parent models (e.g., creating/updating nutrient links when creating/updating an Ingredient).
# If direct manipulation of these links is needed, ViewSets can be added for them too.

class IngredientSearchAPIView(generics.ListAPIView):
    """
    API endpoint for searching ingredients by name.
    Accepts a query parameter 'name' (e.g., /api/ingredients/search/?name=chicken).
    """
    serializer_class = IngredientSearchSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `name` query parameter in the URL.
        """
        queryset = Ingredient.objects.all()
        name_query = self.request.query_params.get('name', None)
        if name_query is not None:
            queryset = queryset.filter(name__icontains=name_query)
        # Order by exact match first, then by name
        # This uses Case/When to prioritize results that start with the search term
        if name_query:
            return queryset.annotate(
                starts_with=Case(
                    When(name__istartswith=name_query, then=0),
                    default=1,
                    output_field=IntegerField(),
                )
            ).order_by('starts_with', 'name')[:20]  # Limit results for performance
        return queryset.order_by('name')[:20]  # If no query, just sort by name

class CalculateNutritionalTargetsView(APIView):
    """
    Calculates the combined nutritional targets for a list of person profiles.
    Accepts a POST request with a list of "person_profile_ids".
    Returns a dictionary 전쟁 by nutrient name with their aggregated RDA, min UL, and unit.
    """
    permission_classes = [permissions.AllowAny] # Or configure more specific permissions as needed

    def post(self, request, *args, **kwargs):
        person_profile_ids = request.data.get("person_profile_ids", [])
        
        # Ensure IDs are integers if they are passed as strings
        try:
            valid_person_profile_ids = [int(pid) for pid in person_profile_ids]
        except ValueError:
            return Response({"error": "Invalid person profile IDs provided. IDs must be integers."}, status=status.HTTP_400_BAD_REQUEST)

        profiles = PersonProfile.objects.filter(id__in=valid_person_profile_ids)

        # Optional: Check if all provided IDs were found
        if len(profiles) != len(set(valid_person_profile_ids)):
            # This could mean some IDs were invalid or duplicates were passed.
            # Depending on requirements, you might want to raise an error or just proceed with found profiles.
            # For now, proceed with found profiles.
            pass


        if not profiles.exists():
            # If no valid profiles are found (e.g., empty list or all IDs invalid), return empty targets.
            return Response({}, status=status.HTTP_200_OK)

        plan_targets = defaultdict(lambda: {"rda": 0, "ul": None, "unit": ""})
        
        # Step 1: Initialize with all system nutrients and their canonical units.
        # This ensures all nutrients from the Nutrient table are considered.
        all_system_nutrients_map = {n.name: n for n in Nutrient.objects.all()}
        for n_name, n_obj in all_system_nutrients_map.items():
            plan_targets[n_name]['unit'] = n_obj.unit
            # RDA is already 0 due to defaultdict.
            # UL is already None due to defaultdict.

        plan_targets_ul_initialized = set() # Tracks nutrients for which UL has been set by the first profile

        # Step 2: Process each profile and aggregate their personalized DRVs.
        for profile in profiles:
            # get_personalized_drvs() should return a dict:
            # {nutrient_name: {"rda": X, "ul": Y, "unit": "unit_str"}}
            # It's crucial that X and Y are in 'unit_str'.
            # This view assumes that if 'unit_str' differs from the canonical Nutrient.unit,
            # the values X and Y are already converted or compatible.
            personalized_drvs = profile.get_personalized_drvs() 
            
            for nutrient_name, drv_values in personalized_drvs.items():
                # If this nutrient is not a known system nutrient (e.g., purely from custom_targets),
                # it needs to be added to plan_targets with its unit from drv_values.
                if nutrient_name not in all_system_nutrients_map:
                    if nutrient_name not in plan_targets: # First time seeing this custom nutrient
                        plan_targets[nutrient_name]['unit'] = drv_values.get('unit', '')
                        # RDA (0) and UL (None) are set by defaultdict.
                    # If already in plan_targets (from another profile's custom target), unit is already set.
                
                # Critical Assumption: Values from drv_values (rda, ul) are consistent with
                # the unit established for nutrient_name in plan_targets.
                # For system nutrients, this is Nutrient.unit.
                # For custom nutrients, it's the unit from the first profile that introduced it.
                # If get_personalized_drvs() returns different units for the same nutrient
                # across different profiles, direct summation/min is incorrect without conversion.

                plan_targets[nutrient_name]["rda"] += drv_values.get("rda") or 0
                
                current_profile_ul = drv_values.get("ul") # This is the UL for this nutrient for this person.

                # UL Aggregation: Take the minimum UL among all profiles.
                # If a profile has no UL (None), it doesn't constrain the plan's UL.
                if nutrient_name not in plan_targets_ul_initialized:
                    # This is the first profile providing a UL (or None) for this nutrient.
                    plan_targets[nutrient_name]["ul"] = current_profile_ul
                    plan_targets_ul_initialized.add(nutrient_name)
                else:
                    # Subsequent profiles: update plan's UL if this profile's UL is more restrictive.
                    if current_profile_ul is not None: # This profile has a specific UL.
                        if plan_targets[nutrient_name]["ul"] is not None:
                            # Both plan and current profile have ULs; take the minimum.
                            plan_targets[nutrient_name]["ul"] = min(plan_targets[nutrient_name]["ul"], current_profile_ul)
                        else:
                            # Plan had no UL (e.g., previous profiles had None), so this profile's UL becomes the plan's UL.
                            plan_targets[nutrient_name]["ul"] = current_profile_ul
                    # If current_profile_ul is None, this profile doesn't add a UL constraint, so plan_targets[nutrient_name]["ul"] remains unchanged.
        
        # Step 3: Ensure all system nutrients are present in the final output,
        # even if no profile provided data for them (they'll have 0 RDA, None UL, and their canonical unit).
        # This also ensures their canonical unit is correctly set if they were somehow missed or unit was cleared.
        for n_name, n_obj in all_system_nutrients_map.items():
            if n_name not in plan_targets: # Should not happen if defaultdict used correctly, but as a safeguard.
                plan_targets[n_name]['rda'] = 0
                plan_targets[n_name]['ul'] = None 
                plan_targets[n_name]['unit'] = n_obj.unit
            elif not plan_targets[n_name].get('unit'): # If unit is missing for a system nutrient (unlikely).
                 plan_targets[n_name]['unit'] = n_obj.unit

        # Prepare response: convert defaultdict to dict.
        # Potentially filter out nutrients with no unit, though ideally all should have one.
        response_data = dict(plan_targets)

        return Response(response_data, status=status.HTTP_200_OK)
