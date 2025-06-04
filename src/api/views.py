from django.shortcuts import render
from django.db.models import Case, When, IntegerField
from rest_framework import viewsets, permissions, filters
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from collections import defaultdict
import logging
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
from .domain_services import IngredientCreationDomainService

logger = logging.getLogger(__name__)

# Create your views here.

class NutrientViewSet(viewsets.ModelViewSet):
    """API endpoint that allows nutrients to be viewed or edited."""
    queryset = Nutrient.objects.all().order_by('name')
    serializer_class = NutrientSerializer
    permission_classes = [permissions.AllowAny]  # Allow any access for testing
    pagination_class = None  # Disable pagination to return all nutrients

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


class AIIngredientCreationAPIView(APIView):
    """
    API endpoint for creating ingredients using AI generation.
    Accepts food descriptions and optional images to generate nutritional data.
    """
    permission_classes = [permissions.AllowAny]  # Allow any access for testing
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.domain_service = IngredientCreationDomainService()

    def post(self, request, *args, **kwargs):
        """
        Create a new ingredient from user description using AI.
        
        Expected request data:
        {
            "description": "kidneybohnen, dose",
            "image": "base64_encoded_image_data" (optional)
        }
        """
        try:
            # Validate required fields
            description = request.data.get('description')
            if not description:
                return Response(
                    {"error": "Description is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            description = description.strip()
            if len(description) < 3:
                return Response(
                    {"error": "Description must be at least 3 characters long"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Optional image data for future enhancement
            image_data = request.data.get('image')
            
            # Check for similar ingredients and warn user
            is_unique, uniqueness_message = self.domain_service.validate_ingredient_uniqueness(description)
            
            # Create the ingredient using domain service
            logger.info(f"Creating AI ingredient for description: {description}")
            ingredient = self.domain_service.create_ingredient_from_description(
                description=description,
                image_data=image_data
            )
            
            # Serialize the created ingredient
            serializer = IngredientSerializer(ingredient)
            
            response_data = {
                "ingredient": serializer.data,
                "uniqueness_check": {
                    "is_unique": is_unique,
                    "message": uniqueness_message
                },
                "success": True,
                "message": f"Successfully created ingredient: {ingredient.name}"
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            logger.error(f"Validation error in AI ingredient creation: {e}")
            return Response(
                {"error": f"Validation error: {str(e)}", "success": False},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error in AI ingredient creation: {e}")
            return Response(
                {"error": f"Failed to create ingredient: {str(e)}", "success": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_ingredient_description(request):
    """
    Validate ingredient description and check for duplicates.
    
    Expected request data:
    {
        "description": "kidneybohnen, dose"
    }
    """
    try:
        description = request.data.get('description')
        if not description:
            return Response(
                {"error": "Description is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        domain_service = IngredientCreationDomainService()
        is_unique, message = domain_service.validate_ingredient_uniqueness(description)
        
        return Response({
            "is_unique": is_unique,
            "message": message,
            "description": description
        })
        
    except Exception as e:
        logger.error(f"Error validating ingredient description: {e}")
        return Response(
            {"error": f"Validation failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
