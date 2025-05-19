from django.shortcuts import render
from django.db.models import Case, When, IntegerField
from rest_framework import viewsets, permissions, filters
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from collections import defaultdict
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

# Create your views here.

class NutrientViewSet(viewsets.ModelViewSet):
    """API endpoint that allows nutrients to be viewed or edited."""
    queryset = Nutrient.objects.all().order_by('name')
    serializer_class = NutrientSerializer
    permission_classes = [permissions.AllowAny]  # Allow any access for testing

class IngredientViewSet(viewsets.ModelViewSet):
    """API endpoint that allows ingredients to be viewed or edited."""
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]  # Allow any access for testing

class PersonProfileViewSet(viewsets.ModelViewSet):
    """API endpoint that allows person profiles to be viewed or edited."""
    queryset = PersonProfile.objects.all().order_by('name')
    serializer_class = PersonProfileSerializer
    permission_classes = [permissions.AllowAny]  # Allow any access for testing

class MealComponentViewSet(viewsets.ModelViewSet):
    """API endpoint that allows meal components to be viewed or edited."""
    queryset = MealComponent.objects.all().order_by('name')
    serializer_class = MealComponentSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'category_tag', 'description_recipe']
    ordering_fields = ['name', 'category_tag']
    ordering = ['name']
    pagination_class = None

class MealPlanViewSet(viewsets.ModelViewSet):
    """API endpoint that allows meal plans to be viewed or edited."""
    queryset = MealPlan.objects.all().order_by('-creation_date')
    serializer_class = MealPlanSerializer
    permission_classes = [permissions.AllowAny]  # Allow any access for testing

class FoodPortionViewSet(viewsets.ModelViewSet):
    """API endpoint that allows food portions to be viewed or edited."""
    queryset = FoodPortion.objects.all().order_by('ingredient__name', 'sequence_number')
    serializer_class = FoodPortionSerializer
    permission_classes = [permissions.AllowAny]  # Allow any access for testing

class IngredientNutrientLinkViewSet(viewsets.ModelViewSet):
    """API endpoint that allows ingredient-nutrient links to be viewed or edited."""
    queryset = IngredientNutrientLink.objects.all()
    serializer_class = IngredientNutrientLinkSerializer
    permission_classes = [permissions.AllowAny]  # Allow any access for testing

class IngredientUsageViewSet(viewsets.ModelViewSet):
    """API endpoint that allows ingredient usages to be viewed or edited."""
    queryset = IngredientUsage.objects.all()
    serializer_class = IngredientUsageSerializer
    permission_classes = [permissions.AllowAny]  # Allow any access for testing

class DietaryReferenceValueViewSet(viewsets.ModelViewSet):
    """API endpoint that allows dietary reference values to be viewed or edited."""
    queryset = DietaryReferenceValue.objects.all()
    serializer_class = DietaryReferenceValueSerializer
    permission_classes = [permissions.AllowAny]  # Allow any access for testing

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
    permission_classes = [permissions.AllowAny]  # Allow any access for testing

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `name` query parameter in the URL.
        """
        queryset = Ingredient.objects.all()
        name_query = self.request.query_params.get('name', None)

        if name_query:
            queryset = queryset.filter(name__icontains=name_query)
            # Order by custom food first, then by exact match, then by name
            return queryset.annotate(
                is_custom_food=Case(
                    When(food_class='Custom', then=0),
                    default=1,
                    output_field=IntegerField(),
                ),
                starts_with=Case(
                    When(name__istartswith=name_query, then=0),
                    default=1,
                    output_field=IntegerField(),
                )
            ).order_by('is_custom_food', 'starts_with', 'name')[:30]  # Limit results

        # If no name_query, still prioritize custom foods
        return queryset.annotate(
            is_custom_food=Case(
                When(food_class='Custom', then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by('is_custom_food', 'name')[:20]  # Limit results
