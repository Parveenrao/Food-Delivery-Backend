from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from app.models.restaurant import Restaurant, MenuItem, MenuCategory, RestaurantStatus
from app.models.user import User
from app.core.exception import ValidationException, NotFoundException, AuthorizationException
from app.core.logging import logger
from app.utils.helpers import calculate_distance


class RestaurantService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_restaurant(self, owner_id: int, restaurant_data: dict) -> Restaurant:
        
        
        # Check if owner already has a restaurant
        existing = self.db.query(Restaurant).filter(
            Restaurant.owner_id == owner_id
        ).first()
        
        if existing:
            raise ValidationException("Owner already has a restaurant")
        
        restaurant = Restaurant(owner_id=owner_id, **restaurant_data)
        self.db.add(restaurant)
        self.db.commit()
        self.db.refresh(restaurant)
        
        logger.info(f"Restaurant created", restaurant_id=restaurant.id, owner_id=owner_id)
        
        return restaurant
    
    def get_restaurant_by_id(self, restaurant_id: int) -> Optional[Restaurant]:
        
        return self.db.query(Restaurant).filter(
            Restaurant.id == restaurant_id,
            Restaurant.is_active == True
        ).first()
    
    def get_restaurants_by_location(
        self, 
        latitude: float, 
        longitude: float, 
        radius_km: float = 10
    ) -> List[Dict]:
        
        
        restaurants = self.db.query(Restaurant).filter(
            Restaurant.is_active == True,
            Restaurant.status == RestaurantStatus.OPEN
        ).all()
        
        nearby_restaurants = []
        
        for restaurant in restaurants:
            if restaurant.latitude and restaurant.longitude:
                distance = calculate_distance(
                    latitude, longitude,
                    restaurant.latitude, restaurant.longitude
                )
                
                if distance <= radius_km:
                    nearby_restaurants.append({
                        'restaurant': restaurant,
                        'distance_km': round(distance, 2)
                    })
        
        
        nearby_restaurants.sort(key=lambda x: x['distance_km'])
        
        return nearby_restaurants
    
    def update_restaurant(self, restaurant_id: int, owner_id: int, update_data: dict) -> Restaurant:
        
        
        restaurant = self.get_restaurant_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundException("Restaurant")
        
        if restaurant.owner_id != owner_id:
            raise AuthorizationException("Not authorized to update this restaurant")
        
        for key, value in update_data.items():
            if hasattr(restaurant, key) and value is not None:
                setattr(restaurant, key, value)
        
        self.db.commit()
        self.db.refresh(restaurant)
        
        logger.info(f"Restaurant updated", restaurant_id=restaurant_id)
        
        return restaurant
    
    def update_restaurant_status(
        self, 
        restaurant_id: int, 
        owner_id: int, 
        status: RestaurantStatus
    ) -> Restaurant:
        
        
        restaurant = self.get_restaurant_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundException("Restaurant")
        
        if restaurant.owner_id != owner_id:
            raise AuthorizationException("Not authorized")
        
        restaurant.status = status
        self.db.commit()
        self.db.refresh(restaurant)
        
        logger.info(f"Restaurant status updated", restaurant_id=restaurant_id, status=status.value)
        
        return restaurant
    
    def add_menu_item(self, restaurant_id: int, owner_id: int, item_data: dict) -> MenuItem:
        
        
        restaurant = self.get_restaurant_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundException("Restaurant")
        
        if restaurant.owner_id != owner_id:
            raise AuthorizationException("Not authorized")
        
        # Validate price
        if item_data.get('price', 0) <= 0:
            raise ValidationException("Price must be greater than 0")
        
        menu_item = MenuItem(restaurant_id=restaurant_id, **item_data)
        self.db.add(menu_item)
        self.db.commit()
        self.db.refresh(menu_item)
        
        logger.info(f"Menu item added", restaurant_id=restaurant_id, item_id=menu_item.id)
        
        return menu_item
    
    def get_menu_items(self, restaurant_id: int, available_only: bool = True) -> List[MenuItem]:
        
        
        query = self.db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id)
        
        if available_only:
            query = query.filter(MenuItem.is_available == True)
        
        return query.all()
    
    def update_menu_item_availability(
        self, 
        item_id: int, 
        restaurant_id: int, 
        owner_id: int, 
        is_available: bool
    ) -> MenuItem:
        
        
        restaurant = self.get_restaurant_by_id(restaurant_id)
        if not restaurant or restaurant.owner_id != owner_id:
            raise AuthorizationException("Not authorized")
        
        menu_item = self.db.query(MenuItem).filter(
            MenuItem.id == item_id,
            MenuItem.restaurant_id == restaurant_id
        ).first()
        
        if not menu_item:
            raise NotFoundException("Menu item")
        
        menu_item.is_available = is_available
        self.db.commit()
        self.db.refresh(menu_item)
        
        logger.info(f"Menu item availability updated", item_id=item_id, available=is_available)
        
        return menu_item
    
    def search_restaurants(self, search_term: str, limit: int = 20) -> List[Restaurant]:
    
        
        search_filter = f"%{search_term}%"
        
        return self.db.query(Restaurant).filter(
            Restaurant.is_active == True,
            (Restaurant.name.ilike(search_filter)) |
            (Restaurant.description.ilike(search_filter))
        ).limit(limit).all()
