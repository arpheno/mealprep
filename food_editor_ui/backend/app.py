from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os

# Adjust path to data directory relative to this script's location
# Assuming this script (app.py) is in food_editor_ui/backend/
# and the data directory is at the workspace root (mealprep/data/)
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
FOUNDATIONAL_FOODS_PATH = os.path.join(DATA_DIR, 'foundational_foods.json')
MY_FOODS_PATH = os.path.join(DATA_DIR, 'my_foods.json')
SURVEY_FOODS_PATH = os.path.join(DATA_DIR, 'surveyDownload.json')

# Import models from models.py
# Make sure models.py is in the same directory or accessible via PYTHONPATH
from .models import FoodItem, FoodList, NutrientInfo, FoodNutrient, FoodCategory, MeasureUnit, FoodPortion

app = FastAPI(
    title="Food Editor API",
    description="API for managing custom food lists and referencing foundational food data.",
    version="0.1.0"
)

# CORS middleware to allow frontend requests (adjust origins as needed for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for now
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Helper Functions ---
def load_json_data(file_path: str) -> Any:
    """Loads JSON data from a file. Returns raw loaded data (list or dict)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []  # Return empty list if file doesn't exist (e.g., my_foods.json initially)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Error decoding JSON from {file_path}")

def save_json_data(file_path: str, data: List[Dict[str, Any]]):
    """Saves data to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except IOError:
        raise HTTPException(status_code=500, detail=f"Error writing JSON to {file_path}")

# In-memory cache for foundational foods to avoid frequent disk reads for large files
# This will load the entire file into memory, which is acceptable for a few MBs to 10s of MBs.
# For very large files (100s of MBs or GBs), a database or a more sophisticated caching/indexing would be needed.
FOUNDATIONAL_FOODS_CACHE: Optional[List[FoodItem]] = None
FOUNDATIONAL_FOODS_DICT_CACHE: Optional[Dict[int, FoodItem]] = None

# In-memory cache for survey foods (New)
SURVEY_FOODS_CACHE: Optional[List[FoodItem]] = None
SURVEY_FOODS_DICT_CACHE: Optional[Dict[int, FoodItem]] = None

def get_foundational_foods() -> List[FoodItem]:
    """Loads foundational foods from JSON, using an in-memory cache."""
    global FOUNDATIONAL_FOODS_CACHE
    if FOUNDATIONAL_FOODS_CACHE is None:
        loaded_data: Any = load_json_data(FOUNDATIONAL_FOODS_PATH)
        
        actual_food_items_list: List[Dict[str, Any]] = []

        if isinstance(loaded_data, list):
            actual_food_items_list = loaded_data
        elif isinstance(loaded_data, dict):
            # Common key for FDC Foundation Foods is "FoundationFoods"
            if "FoundationFoods" in loaded_data and isinstance(loaded_data["FoundationFoods"], list):
                actual_food_items_list = loaded_data["FoundationFoods"]
            else:
                # Fallback: if the dictionary has only one key and its value is a list, use that.
                keys = list(loaded_data.keys())
                if len(keys) == 1 and isinstance(loaded_data[keys[0]], list):
                    actual_food_items_list = loaded_data[keys[0]]
                    print(f"INFO: Foundational foods list extracted from single dictionary key: {keys[0]}")
                else:
                    error_msg = (
                        f"ERROR: Could not find a list of food items in '{FOUNDATIONAL_FOODS_PATH}'. "
                        f"File content is a dictionary with keys: {keys}. "
                        "Expected a list or a dictionary with a 'FoundationFoods' key containing a list."
                    )
                    print(error_msg)
                    raise ValueError(error_msg)
        elif loaded_data == [] and not os.path.exists(FOUNDATIONAL_FOODS_PATH):
            # File not found, load_json_data returns [], so actual_food_items_list is []
            print(f"INFO: Foundational foods file '{FOUNDATIONAL_FOODS_PATH}' not found. Cache will be empty.")
            actual_food_items_list = [] # Already is, but for clarity
        else:
            error_msg = f"ERROR: Unsupported data type loaded from {FOUNDATIONAL_FOODS_PATH}: {type(loaded_data)}. Expected list or dict."
            print(error_msg)
            raise TypeError(error_msg)

        if not actual_food_items_list and os.path.exists(FOUNDATIONAL_FOODS_PATH):
             print(f"WARNING: Extracted food item list from {FOUNDATIONAL_FOODS_PATH} is empty. Check file structure and content.")
             FOUNDATIONAL_FOODS_CACHE = []
        elif not actual_food_items_list: # Covers file not found or empty list extracted
            FOUNDATIONAL_FOODS_CACHE = []
        else:
            try:
                parsed_items = []
                for i, item_data in enumerate(actual_food_items_list):
                    if not isinstance(item_data, dict):
                        err_msg = (f"ERROR: Item at index {i} in foundational foods list from '{FOUNDATIONAL_FOODS_PATH}' "
                                   f"is not a dictionary (type: {type(item_data)}). Value: {str(item_data)[:200]}")
                        print(err_msg)
                        raise TypeError(err_msg)
                    parsed_items.append(FoodItem(**item_data))
                FOUNDATIONAL_FOODS_CACHE = parsed_items
            except TypeError as e: # Catch ** mapping error more broadly
                print(f"ERROR: TypeError during Pydantic model instantiation for foundational foods: {e}. "
                      "This likely means an item in the list was not a dictionary. Please check JSON structure.")
                raise
            except Exception as e: # Catch other Pydantic validation errors
                print(f"ERROR: Pydantic validation error while processing foundational foods from '{FOUNDATIONAL_FOODS_PATH}': {e}")
                # For detailed debugging, you could log the specific item that failed validation.
                raise
            
    if FOUNDATIONAL_FOODS_CACHE is None:
         print("WARNING: FOUNDATIONAL_FOODS_CACHE is None after attempting to load. Defaulting to empty list.")
         FOUNDATIONAL_FOODS_CACHE = []
    return FOUNDATIONAL_FOODS_CACHE

def get_foundational_foods_as_dict() -> Dict[int, FoodItem]:
    """Loads foundational foods and provides quick lookup by fdcId."""
    global FOUNDATIONAL_FOODS_DICT_CACHE
    if FOUNDATIONAL_FOODS_DICT_CACHE is None:
        foods = get_foundational_foods()
        FOUNDATIONAL_FOODS_DICT_CACHE = {food.fdcId: food for food in foods}
    return FOUNDATIONAL_FOODS_DICT_CACHE

# New function for survey foods
def get_survey_foods() -> List[FoodItem]:
    """Loads survey foods from surveyDownload.json, using an in-memory cache."""
    global SURVEY_FOODS_CACHE
    if SURVEY_FOODS_CACHE is None:
        loaded_data: Any = load_json_data(SURVEY_FOODS_PATH)
        actual_food_items_list: List[Dict[str, Any]] = []

        if isinstance(loaded_data, list):
            actual_food_items_list = loaded_data
        elif isinstance(loaded_data, dict):
            # Common keys for Survey/SR Legacy data
            potential_keys = ["SurveyFoods", "SRLegacyFoods"]
            found_key = False
            for key in potential_keys:
                if key in loaded_data and isinstance(loaded_data[key], list):
                    actual_food_items_list = loaded_data[key]
                    print(f"INFO: Survey foods list extracted from dictionary key: {key}")
                    found_key = True
                    break
            if not found_key:
                # Fallback: if the dictionary has only one key and its value is a list, use that.
                dict_keys = list(loaded_data.keys())
                if len(dict_keys) == 1 and isinstance(loaded_data[dict_keys[0]], list):
                    actual_food_items_list = loaded_data[dict_keys[0]]
                    print(f"INFO: Survey foods list extracted from single dictionary key: {dict_keys[0]}")
                else:
                    error_msg = (
                        f"ERROR: Could not find a list of food items in '{SURVEY_FOODS_PATH}'. "
                        f"File content is a dictionary with keys: {dict_keys}. Expected a list or common FDC keys."
                    )
                    print(error_msg)
                    raise ValueError(error_msg)
        elif loaded_data == [] and not os.path.exists(SURVEY_FOODS_PATH):
            print(f"INFO: Survey foods file '{SURVEY_FOODS_PATH}' not found. Cache will be empty.")
            actual_food_items_list = []
        else:
            error_msg = f"ERROR: Unsupported data type loaded from {SURVEY_FOODS_PATH}: {type(loaded_data)}. Expected list or dict."
            print(error_msg)
            raise TypeError(error_msg)

        if not actual_food_items_list and os.path.exists(SURVEY_FOODS_PATH):
            print(f"WARNING: Extracted food item list from {SURVEY_FOODS_PATH} is empty. Check file structure and content.")
            SURVEY_FOODS_CACHE = []
        elif not actual_food_items_list:
            SURVEY_FOODS_CACHE = []
        else:
            try:
                parsed_items = []
                for i, item_data in enumerate(actual_food_items_list):
                    if not isinstance(item_data, dict):
                        err_msg = (f"ERROR: Item at index {i} in survey foods list from '{SURVEY_FOODS_PATH}' "
                                   f"is not a dictionary (type: {type(item_data)}). Value: {str(item_data)[:200]}")
                        print(err_msg)
                        raise TypeError(err_msg)
                    # Survey data might have slightly different field names or missing fields.
                    # The FoodItem model is already quite flexible with Optional fields.
                    parsed_items.append(FoodItem(**item_data))
                SURVEY_FOODS_CACHE = parsed_items
            except TypeError as e:
                print(f"ERROR: TypeError during Pydantic model instantiation for survey foods: {e}. Check JSON structure and model compatibility.")
                raise
            except Exception as e:
                print(f"ERROR: Pydantic validation error while processing survey foods from '{SURVEY_FOODS_PATH}': {e}")
                raise
            
    if SURVEY_FOODS_CACHE is None:
        print("WARNING: SURVEY_FOODS_CACHE is None after attempting to load. Defaulting to empty list.")
        SURVEY_FOODS_CACHE = []
    return SURVEY_FOODS_CACHE

def get_survey_foods_as_dict() -> Dict[int, FoodItem]:
    """Loads survey foods and provides quick lookup by fdcId."""
    global SURVEY_FOODS_DICT_CACHE
    if SURVEY_FOODS_DICT_CACHE is None:
        foods = get_survey_foods()
        SURVEY_FOODS_DICT_CACHE = {food.fdcId: food for food in foods if food.fdcId is not None} # Ensure fdcId exists
    return SURVEY_FOODS_DICT_CACHE

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    """Load foundational and survey foods into cache on startup."""
    print(f"Attempting to load foundational foods from: {FOUNDATIONAL_FOODS_PATH}")
    if not os.path.exists(FOUNDATIONAL_FOODS_PATH):
        print(f"Warning: Foundational foods file not found at {FOUNDATIONAL_FOODS_PATH}")
    else:
        get_foundational_foods() 
        get_foundational_foods_as_dict()
        print(f"Successfully loaded {len(FOUNDATIONAL_FOODS_CACHE) if FOUNDATIONAL_FOODS_CACHE else 0} foundational food items.")

    print(f"Attempting to load survey foods from: {SURVEY_FOODS_PATH}")
    if not os.path.exists(SURVEY_FOODS_PATH):
        print(f"Warning: Survey foods file not found at {SURVEY_FOODS_PATH}")
    else:
        get_survey_foods()
        get_survey_foods_as_dict()
        print(f"Successfully loaded {len(SURVEY_FOODS_CACHE) if SURVEY_FOODS_CACHE else 0} survey food items.")

    print(f"My foods path: {MY_FOODS_PATH}")
    if not os.path.exists(MY_FOODS_PATH):
        print(f"Warning: My foods file not found at {MY_FOODS_PATH}. It will be created if new foods are added.")

@app.get("/api/foundational_foods", response_model=List[FoodItem])
async def list_foundational_foods(
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Gets a paginated list of all foundational food items."""
    foods = get_foundational_foods()
    return foods[offset : offset + limit]

@app.get("/api/foundational_foods/search", response_model=List[FoodItem])
async def search_foundational_foods(
    query: str = Query(..., min_length=3, description="Search query for food description"),
    limit: int = Query(10, ge=1, le=100, description="Max number of search results")
):
    """Searches foundational food items by description (case-insensitive)."""
    foods = get_foundational_foods()
    # Simple case-insensitive search
    results = [food for food in foods if query.lower() in food.description.lower()]
    return results[:limit]

@app.get("/api/foundational_foods/{fdc_id}", response_model=FoodItem)
async def get_foundational_food_by_id(fdc_id: int):
    """Gets a specific foundational food item by its FDC ID."""
    foods_dict = get_foundational_foods_as_dict()
    food = foods_dict.get(fdc_id)
    if not food:
        raise HTTPException(status_code=404, detail=f"Foundational food with FDC ID {fdc_id} not found.")
    return food

@app.get("/api/survey_foods", response_model=List[FoodItem])
async def list_survey_foods(
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Gets a paginated list of all survey food items."""
    foods = get_survey_foods()
    return foods[offset : offset + limit]

@app.get("/api/survey_foods/search", response_model=List[FoodItem])
async def search_survey_foods(
    query: str = Query(..., min_length=3, description="Search query for food description"),
    limit: int = Query(10, ge=1, le=100, description="Max number of search results")
):
    """Searches survey food items by description (case-insensitive)."""
    foods = get_survey_foods()
    results = [food for food in foods if query.lower() in food.description.lower()]
    return results[:limit]

@app.get("/api/survey_foods/{fdc_id}", response_model=FoodItem)
async def get_survey_food_by_id(fdc_id: int):
    """Gets a specific survey food item by its FDC ID."""
    foods_dict = get_survey_foods_as_dict()
    food = foods_dict.get(fdc_id)
    if not food:
        raise HTTPException(status_code=404, detail=f"Survey food with FDC ID {fdc_id} not found.")
    return food

@app.get("/api/my_foods", response_model=List[FoodItem])
async def get_my_foods():
    """Gets all food items from my_foods.json."""
    my_foods_data = load_json_data(MY_FOODS_PATH)
    if not isinstance(my_foods_data, list):
        # This would be an unexpected structure for my_foods.json, which should always be a list.
        raise HTTPException(status_code=500, detail=f"my_foods.json is not a list as expected. Found type: {type(my_foods_data)}")
    return [FoodItem(**item) for item in my_foods_data]

@app.post("/api/my_foods", response_model=FoodItem, status_code=201)
async def add_my_food(food_item_create: FoodItem):
    """Adds a new food item to my_foods.json.
    The input should be a complete FoodItem object.
    If food_item_create.fdcId is positive, it's assumed to be a reference and should be unique.
    If food_item_create.fdcId is not provided or is <= 0, a new negative ID will be generated.
    """
    my_foods_raw = load_json_data(MY_FOODS_PATH)
    my_foods_items = [FoodItem(**item) for item in my_foods_raw]

    # Determine the new fdcId for the custom food
    if food_item_create.fdcId > 0:
        # If a positive ID is provided, check for duplicates in my_foods (should generally be unique from foundational)
        # This case is more for 'copying' a foundational food with its ID, then modifying.
        # Or, if the user *really* wants to use a specific positive ID for their custom entry.
        if any(f.fdcId == food_item_create.fdcId for f in my_foods_items):
            raise HTTPException(
                status_code=409,
                detail=f"Food item with fdcId {food_item_create.fdcId} already exists in my_foods.json. Use a unique ID or let the system generate one."
            )
        new_fdc_id = food_item_create.fdcId
    else:
        # Generate a new negative ID
        min_fdc_id = min((f.fdcId for f in my_foods_items if f.fdcId < 0), default=0)
        new_fdc_id = min_fdc_id - 1

    new_food = food_item_create.copy(deep=True)
    new_food.fdcId = new_fdc_id
    new_food.foodClass = "Custom" # Ensure it's marked as custom
    if not new_food.foodCategory:
         new_food.foodCategory = FoodCategory(description="Custom Foods", code="9999", id=new_fdc_id) # default if not provided
    else:
        # Ensure custom food category also gets a negative/unique ID if it's new or has a generic one
        if new_food.foodCategory.id >= 0 or not new_food.foodCategory.id:
            new_food.foodCategory.id = new_fdc_id # Use the food's fdcId for its custom category id

    my_foods_items.append(new_food)
    
    # Convert Pydantic models back to dicts for saving
    my_foods_to_save = [item.dict(by_alias=True) for item in my_foods_items]
    save_json_data(MY_FOODS_PATH, my_foods_to_save)
    
    return new_food


# To run the app (save this as app.py and run with uvicorn):
# uvicorn food_editor_ui.backend.app:app --reload --port 8008
# (Assuming you run from the workspace root, adjust path if needed)

if __name__ == "__main__":
    import uvicorn
    # Note: Running directly like this is for development.
    # For production, use a process manager like Gunicorn with Uvicorn workers.
    print("Starting Uvicorn server for Food Editor API...")
    print(f"Access API at http://localhost:8008")
    print(f"Swagger UI at http://localhost:8008/docs")
    uvicorn.run("app:app", host="0.0.0.0", port=8008, reload=True, app_dir=os.path.dirname(__file__)) 