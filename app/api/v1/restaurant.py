from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app.api.deps import get_current_user, get_restaurant_owner
from app.models.user import User
from app.models.restaurant import Restaurant, MenuItem, MenuCategory, RestaurantStatus
from app.schema.restaurant import (
    RestaurantCreate, RestaurantUpdate, RestaurantResponse, RestaurantDetailResponse,
    MenuItemCreate, MenuItemUpdate, MenuItemResponse,
    MenuCategoryCreate, MenuCategoryResponse
)
from app.core.exception import NotFoundException, ValidationException, AuthorizationException
from app.core.logging import logger

router = APIRouter(prefix="/restaurants", tags=["restaurants"])



@router.post("/", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
async def create_restaurant(
    restaurant_data: RestaurantCreate,
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Create a new restaurant (restaurant owners only)'''
    
    # Check if user already has a restaurant
    existing_restaurant = db.query(Restaurant).filter(
        Restaurant.owner_id == current_user.id
    ).first()
    
    if existing_restaurant:
        raise ValidationException("You already have a restaurant registered")
    
    # Create restaurant
    db_restaurant = Restaurant(
        name=restaurant_data.name,
        description=restaurant_data.description,
        phone=restaurant_data.phone,
        email=restaurant_data.email,
        address=restaurant_data.address,
        latitude=restaurant_data.latitude,
        longitude=restaurant_data.longitude,
        delivery_fee=restaurant_data.delivery_fee,
        minimum_order=restaurant_data.minimum_order,
        delivery_time=restaurant_data.delivery_time,
        owner_id=current_user.id
    )
    
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    
    logger.info(f"Restaurant created", restaurant_id=db_restaurant.id, owner_id=current_user.id)
    
    return db_restaurant

@router.get("/", response_model=List[RestaurantResponse])
async def list_restaurants(
    status: Optional[RestaurantStatus] = Query(None, description="Filter by restaurant status"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    limit: int = Query(20, le=100, description="Number of restaurants to return"),
    offset: int = Query(0, description="Number of restaurants to skip"),
    db: Session = Depends(get_db)
):
    '''Get list of all active restaurants'''
    
    query = db.query(Restaurant).filter(Restaurant.is_active == True)
    
    if status:
        query = query.filter(Restaurant.status == status)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Restaurant.name.ilike(search_filter)) |
            (Restaurant.description.ilike(search_filter))
        )
    
    restaurants = query.order_by(Restaurant.rating.desc()).offset(offset).limit(limit).all()
    
    return restaurants

@router.get("/{restaurant_id}", response_model=RestaurantDetailResponse)
async def get_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db)
):
    '''Get restaurant details with menu'''
    
    restaurant = db.query(Restaurant).options(
        joinedload(Restaurant.menu_items),
        joinedload(Restaurant.categories)
    ).filter(
        Restaurant.id == restaurant_id,
        Restaurant.is_active == True
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant")
    
    return restaurant

@router.patch("/{restaurant_id}", response_model=RestaurantResponse)
async def update_restaurant(
    restaurant_id: int,
    restaurant_update: RestaurantUpdate,
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Update restaurant details (owner only)'''
    
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant or access denied")
    
    # Update fields
    update_data = restaurant_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(restaurant, field, value)
    
    db.commit()
    db.refresh(restaurant)
    
    logger.info(f"Restaurant updated", restaurant_id=restaurant_id)
    
    return restaurant

@router.delete("/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_restaurant(
    restaurant_id: int,
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Deactivate restaurant (soft delete)'''
    
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant or access denied")
    
    restaurant.is_active = False
    db.commit()
    
    logger.info(f"Restaurant deactivated", restaurant_id=restaurant_id)
    
    return None

@router.get("/my/restaurant", response_model=RestaurantDetailResponse)
async def get_my_restaurant(
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Get current user's restaurant'''
    
    restaurant = db.query(Restaurant).options(
        joinedload(Restaurant.menu_items),
        joinedload(Restaurant.categories)
    ).filter(Restaurant.owner_id == current_user.id).first()
    
    if not restaurant:
        raise NotFoundException("You don't have a restaurant registered")
    
    return restaurant



@router.post("/{restaurant_id}/categories", response_model=MenuCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    restaurant_id: int,
    category_data: MenuCategoryCreate,
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Create menu category (owner only)'''
    
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant or access denied")
    
    db_category = MenuCategory(
        name=category_data.name,
        description=category_data.description,
        sort_order=category_data.sort_order,
        restaurant_id=restaurant_id
    )
    
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    logger.info(f"Category created", category_id=db_category.id, restaurant_id=restaurant_id)
    
    return db_category

@router.get("/{restaurant_id}/categories", response_model=List[MenuCategoryResponse])
async def list_categories(
    restaurant_id: int,
    db: Session = Depends(get_db)
):
    '''Get all categories for a restaurant'''
    
    categories = db.query(MenuCategory).filter(
        MenuCategory.restaurant_id == restaurant_id,
        MenuCategory.is_active == True
    ).order_by(MenuCategory.sort_order).all()
    
    return categories


@router.post("/{restaurant_id}/menu", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    restaurant_id: int,
    menu_item_data: MenuItemCreate,
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Add menu item to restaurant (owner only)'''
    
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant or access denied")
    
    # Verify category belongs to this restaurant
    category = db.query(MenuCategory).filter(
        MenuCategory.id == menu_item_data.category_id,
        MenuCategory.restaurant_id == restaurant_id
    ).first()
    
    if not category:
        raise ValidationException("Invalid category for this restaurant")
    
    # Validate prices
    if menu_item_data.price <= 0:
        raise ValidationException("Price must be greater than 0")
    
    if menu_item_data.discounted_price and menu_item_data.discounted_price >= menu_item_data.price:
        raise ValidationException("Discounted price must be less than regular price")
    
    db_menu_item = MenuItem(
        name=menu_item_data.name,
        description=menu_item_data.description,
        price=menu_item_data.price,
        discounted_price=menu_item_data.discounted_price,
        image_url=menu_item_data.image_url,
        is_vegetarian=menu_item_data.is_vegetarian,
        is_vegan=menu_item_data.is_vegan,
        is_available=menu_item_data.is_available,
        preparation_time=menu_item_data.preparation_time,
        restaurant_id=restaurant_id,
        category_id=menu_item_data.category_id
    )
    
    db.add(db_menu_item)
    db.commit()
    db.refresh(db_menu_item)
    
    logger.info(f"Menu item created", item_id=db_menu_item.id, restaurant_id=restaurant_id)
    
    return db_menu_item

@router.get("/{restaurant_id}/menu", response_model=List[MenuItemResponse])
async def get_restaurant_menu(
    restaurant_id: int,
    category_id: Optional[int] = Query(None, description="Filter by category"),
    is_vegetarian: Optional[bool] = Query(None, description="Filter vegetarian items"),
    is_vegan: Optional[bool] = Query(None, description="Filter vegan items"),
    available_only: bool = Query(True, description="Show only available items"),
    db: Session = Depends(get_db)
):
    '''Get restaurant menu items'''
    
    query = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id)
    
    if available_only:
        query = query.filter(MenuItem.is_available == True)
    
    if category_id:
        query = query.filter(MenuItem.category_id == category_id)
    
    if is_vegetarian is not None:
        query = query.filter(MenuItem.is_vegetarian == is_vegetarian)
    
    if is_vegan is not None:
        query = query.filter(MenuItem.is_vegan == is_vegan)
    
    menu_items = query.all()
    
    return menu_items

@router.get("/{restaurant_id}/menu/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    restaurant_id: int,
    item_id: int,
    db: Session = Depends(get_db)
):
    '''Get specific menu item details'''
    
    menu_item = db.query(MenuItem).filter(
        MenuItem.id == item_id,
        MenuItem.restaurant_id == restaurant_id
    ).first()
    
    if not menu_item:
        raise NotFoundException("Menu item")
    
    return menu_item

@router.patch("/{restaurant_id}/menu/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    restaurant_id: int,
    item_id: int,
    menu_item_update: MenuItemUpdate,
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Update menu item (owner only)'''
    
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant or access denied")
    
    menu_item = db.query(MenuItem).filter(
        MenuItem.id == item_id,
        MenuItem.restaurant_id == restaurant_id
    ).first()
    
    if not menu_item:
        raise NotFoundException("Menu item")
    
    # Update fields
    update_data = menu_item_update.model_dump(exclude_unset=True)
    
    # Validate prices if being updated
    if 'price' in update_data and update_data['price'] <= 0:
        raise ValidationException("Price must be greater than 0")
    
    if 'discounted_price' in update_data and update_data['discounted_price']:
        price = update_data.get('price', menu_item.price)
        if update_data['discounted_price'] >= price:
            raise ValidationException("Discounted price must be less than regular price")
    
    # Verify category if being updated
    if 'category_id' in update_data:
        category = db.query(MenuCategory).filter(
            MenuCategory.id == update_data['category_id'],
            MenuCategory.restaurant_id == restaurant_id
        ).first()
        
        if not category:
            raise ValidationException("Invalid category for this restaurant")
    
    for field, value in update_data.items():
        setattr(menu_item, field, value)
    
    db.commit()
    db.refresh(menu_item)
    
    logger.info(f"Menu item updated", item_id=item_id, restaurant_id=restaurant_id)
    
    return menu_item

@router.delete("/{restaurant_id}/menu/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    restaurant_id: int,
    item_id: int,
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Delete menu item (owner only)'''
    
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant or access denied")
    
    menu_item = db.query(MenuItem).filter(
        MenuItem.id == item_id,
        MenuItem.restaurant_id == restaurant_id
    ).first()
    
    if not menu_item:
        raise NotFoundException("Menu item")
    
    # Soft delete by marking as unavailable
    menu_item.is_available = False
    db.commit()
    
    logger.info(f"Menu item deleted", item_id=item_id, restaurant_id=restaurant_id)
    
    return None

@router.patch("/{restaurant_id}/status", response_model=RestaurantResponse)
async def update_restaurant_status(
    restaurant_id: int,
    status: RestaurantStatus,
    current_user: User = Depends(get_restaurant_owner),
    db: Session = Depends(get_db)
):
    '''Update restaurant status (open/closed/busy) - owner only'''
    
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.owner_id == current_user.id
    ).first()
    
    if not restaurant:
        raise NotFoundException("Restaurant or access denied")
    
    restaurant.status = status
    db.commit()
    db.refresh(restaurant)
    
    logger.info(f"Restaurant status updated", restaurant_id=restaurant_id, status=status.value)
    
    return restaurant