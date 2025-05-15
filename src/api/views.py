from django.shortcuts import render
from django.db.models import Case, When, IntegerField
from rest_framework import viewsets, permissions
from rest_framework import generics
from .models import Nutrient, Ingredient, PersonProfile, MealComponent, MealPlan
from .serializers import (
    NutrientSerializer, 
    IngredientSerializer, 
    PersonProfileSerializer, 
    MealComponentSerializer, 
    MealPlanSerializer,
    IngredientSearchSerializer
)

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

class MealPlanViewSet(viewsets.ModelViewSet):
    """API endpoint that allows meal plans to be viewed or edited."""
    queryset = MealPlan.objects.all().order_by('-creation_date')
    serializer_class = MealPlanSerializer

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
