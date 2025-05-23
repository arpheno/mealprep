from typing import List, Optional, Union, Any, Dict
from pydantic import BaseModel, Field, model_validator
import logging # For logging discarded nutrients

# Configure a logger for schema validation issues
schema_logger = logging.getLogger(__name__)
schema_logger.setLevel(logging.WARNING)
# Ensure logs go to console if no other handler is configured (e.g., during management command execution)
if not schema_logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    schema_logger.addHandler(handler)

class NutrientSchema(BaseModel):
    id: int  # FDC ID of the nutrient itself
    number: Optional[str] = None  # e.g., "208" for Energy. FDC Nutrient Number.
    name: Optional[str] = None
    rank: Optional[int] = None
    unitName: Optional[str] = None  # e.g., "KCAL", "MG", "G"

class FoodNutrientSourceSchema(BaseModel):
    id: Optional[int] = None
    code: Optional[str] = None
    description: Optional[str] = None

class FoodNutrientDerivationSchema(BaseModel):
    id: Optional[int] = None
    code: Optional[str] = None
    description: Optional[str] = None
    foodNutrientSource: Optional[FoodNutrientSourceSchema] = None

class NutrientAcquisitionDetailsSchema(BaseModel):
    sampleUnitId: Optional[int] = None
    purchaseDate: Optional[str] = None
    storeCity: Optional[str] = None
    storeState: Optional[str] = None

class NutrientAnalysisDetailsSchema(BaseModel):
    subSampleId: Optional[int] = None
    amount: Optional[float] = None
    nutrientId: Optional[int] = None
    labMethodDescription: Optional[str] = None
    labMethodOriginalDescription: Optional[str] = None
    labMethodLink: Optional[str] = None
    labMethodTechnique: Optional[str] = None
    nutrientAcquisitionDetails: Optional[List[NutrientAcquisitionDetailsSchema]] = None

class FoodNutrientSchema(BaseModel):
    dataPoints: Optional[int] = None
    min_val: Optional[float] = Field(None, alias="min")
    max_val: Optional[float] = Field(None, alias="max")
    median: Optional[float] = None
    entry_type: Optional[str] = Field(None, alias="type", description="e.g., 'FoodNutrient'")
    
    nutrient: NutrientSchema
    amount: float
    foodNutrientDerivation: Optional[FoodNutrientDerivationSchema] = None
    nutrientAnalysisDetails: Optional[NutrientAnalysisDetailsSchema] = None

    class Config:
        populate_by_name = True

class MeasureUnitSchema(BaseModel):
    id: Optional[int] = None
    abbreviation: Optional[str] = None
    name: Optional[str] = None

class FoodPortionSchema(BaseModel):
    id: int # FDC ID for the portion, now mandatory
    amount: float # Amount, now mandatory
    dataPoints: Optional[int] = None
    gramWeight: float # Gram weight, now mandatory
    minYearAcquired: Optional[int] = None
    modifier: Optional[str] = None
    portionDescription: Optional[str] = ""
    sequenceNumber: Optional[int] = None
    measureUnit: Optional[MeasureUnitSchema] = None

class FoodCategorySchema(BaseModel):
    id: Optional[int] = None
    code: Optional[str] = None
    description: Optional[str] = None

class InputFoodItemSchema(BaseModel):
    fdcId: Optional[int] = None
    dataType: Optional[Union[str, None]] = None
    description: Optional[str] = None
    foodClass: Optional[str] = None
    publicationDate: Optional[str] = None
    foodCategory: Optional[FoodCategorySchema] = None

class InputFoodFoundationSchema(BaseModel):
    id: Optional[int] = None
    foodDescription: Optional[str] = None
    inputFood: Optional[InputFoodItemSchema] = None

class NutrientConversionFactorSchema(BaseModel):
    factor_type: Optional[str] = Field(None, alias="type")
    value: Optional[float] = None

    class Config:
        populate_by_name = True

class FoundationFoodItemSchema(BaseModel):
    fdcId: int
    dataType: Optional[Union[str, None]] = None
    description: str
    foodClass: Optional[str] = None
    footNote: Optional[str] = None
    isHistoricalReference: Optional[bool] = None
    ndbNumber: Optional[int] = None
    publicationDate: Optional[str] = None
    scientificName: Optional[str] = None
    
    foodCategory: Optional[FoodCategorySchema] = None
    foodNutrients: List[FoodNutrientSchema] = []
    foodPortions: List[FoodPortionSchema] = []
    inputFoods: List[InputFoodFoundationSchema] = []
    nutrientConversionFactors: List[NutrientConversionFactorSchema] = []

    @model_validator(mode='before')
    @classmethod
    def filter_missing_nutrient_amounts(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'foodNutrients' in data and isinstance(data['foodNutrients'], list):
            original_count = len(data['foodNutrients'])
            valid_food_nutrients = []
            for nutrient_entry in data['foodNutrients']:
                if isinstance(nutrient_entry, dict):
                    amount = nutrient_entry.get('amount')
                    nutrient_info = nutrient_entry.get('nutrient', {})
                    nutrient_name = nutrient_info.get('name', 'Unknown')
                    nutrient_id = nutrient_info.get('id', 'Unknown')

                    if amount is None:
                        schema_logger.warning(
                            f"Discarding nutrient entry (ID: {nutrient_id}, Name: '{nutrient_name}') for FDC ID {data.get('fdcId', 'Unknown Food')} due to missing 'amount'."
                        )
                        continue # Skip this nutrient entry
                    try:
                        # Attempt a basic float conversion to catch obviously non-numeric types early
                        # Pydantic will do a more thorough validation later.
                        float(amount)
                        valid_food_nutrients.append(nutrient_entry)
                    except (ValueError, TypeError):
                        schema_logger.warning(
                            f"Discarding nutrient entry (ID: {nutrient_id}, Name: '{nutrient_name}') for FDC ID {data.get('fdcId', 'Unknown Food')} because 'amount' ('{amount}') cannot be converted to a number."
                        )
                        continue # Skip this nutrient entry
                else:
                    # If the entry isn't a dict, it's malformed; let Pydantic handle it or skip
                    schema_logger.warning(f"Skipping malformed nutrient entry (not a dict): {nutrient_entry} for FDC ID {data.get('fdcId', 'Unknown Food')}")
                    continue
            
            if len(valid_food_nutrients) < original_count:
                schema_logger.info(
                    f"For FDC ID {data.get('fdcId', 'Unknown Food')}: {original_count - len(valid_food_nutrients)} nutrient entries were discarded due to missing/invalid 'amount'."
                )
            data['foodNutrients'] = valid_food_nutrients
        return data

    @model_validator(mode='before')
    @classmethod
    def filter_invalid_food_portions(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'foodPortions' in data and isinstance(data['foodPortions'], list):
            original_portions_count = len(data['foodPortions'])
            valid_food_portions = []
            for portion_entry in data['foodPortions']:
                if isinstance(portion_entry, dict):
                    portion_id = portion_entry.get('id')
                    gram_weight = portion_entry.get('gramWeight')
                    amount = portion_entry.get('amount') # Get amount
                    description = portion_entry.get('portionDescription', 'N/A')

                    if portion_id is None or gram_weight is None or amount is None: # Check amount here
                        schema_logger.warning(
                            f"Discarding food portion (ID: {portion_id if portion_id else 'Missing'}, Amount: {amount if amount is not None else 'Missing'}, GramWeight: {gram_weight if gram_weight is not None else 'Missing'}, Description: '{description}') for FDC ID {data.get('fdcId', 'Unknown Food')} due to missing 'id', 'gramWeight', or 'amount'."
                        )
                        continue  # Skip this portion entry
                    try:
                        # Ensure gramWeight can be a float
                        if gram_weight is not None:
                             float(gram_weight)
                        # Ensure id can be an int
                        if portion_id is not None:
                            int(portion_id)
                        # Ensure amount can be a float
                        if amount is not None:
                            float(amount)
                        valid_food_portions.append(portion_entry)
                    except (ValueError, TypeError):
                        schema_logger.warning(
                            f"Discarding food portion (ID: {portion_id}, Description: '{description}') for FDC ID {data.get('fdcId', 'Unknown Food')} because 'id', 'gramWeight', or 'amount' has an invalid type."
                        )
                        continue # Skip this portion entry
                else:
                    schema_logger.warning(f"Skipping malformed food portion entry (not a dict): {portion_entry} for FDC ID {data.get('fdcId', 'Unknown Food')}")
                    continue
            
            if len(valid_food_portions) < original_portions_count:
                schema_logger.info(
                    f"For FDC ID {data.get('fdcId', 'Unknown Food')}: {original_portions_count - len(valid_food_portions)} food portion entries were discarded due to missing/invalid 'id', 'gramWeight', or 'amount'."
                )
            data['foodPortions'] = valid_food_portions
        return data

# For parsing the top-level structure of the JSON file
class FoundationFoodsFileSchema(BaseModel):
    FoundationFoods: List[FoundationFoodItemSchema] 