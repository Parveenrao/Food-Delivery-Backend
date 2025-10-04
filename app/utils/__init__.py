import re
import uuid
from datetime import datetime , timedelta
from typing import Dict , List , Optional , Any
import hashlib
import secrets
from math import radians , cos , sin , asin , sqrt


def generate_unique_id(prefix : str = "") -> str:
    
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"{prefix}-{unique_id}" if prefix else unique_id


def generate_order_number() -> str:
   
    timestamp = datetime.now().strftime("%Y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"ORD={timestamp}-{random_part}"    


def validate_email(email: str) -> bool:
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    '''Validate Indian phone numbers'''
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    pattern = r'^(\+91)?[6-9]\d{9}$'
    return bool(re.match(pattern, cleaned))


def format_phone(phone : str) -> str:
    cleaned = re.sub(r'[\s\-\(\)]' , '' , phone)
    
    # Case1 Plain digit number 
    
    if len(cleaned) == 10 and cleaned[0] in 6789:
        return f"+91{cleaned}"
    
    # Case2 number starts with 0
    
    elif len(cleaned) == 11 and  cleaned.startswith("0") and cleaned[1] in 6789:
        return f"+91{cleaned[1:]}"

    
    # Case 3 Nummber already with +91 
    
    elif cleaned.startswith("91") and len(cleaned) == 12:
        return f"+{cleaned}"
    elif cleaned.startswith("+91") and len(cleaned) == 13:
        return f"{cleaned}"
    

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
  
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


def calculate_deliver_fee(distance_km : float , base_fee : float = 2.99) -> float:
    per_km_charge = 0.50
    
    if distance_km<=2:
        return base_fee
    
    else:
        additional_km = distance_km -3 
        
        return round(base_fee + (additional_km * per_km_charge) , 2)
    

def calculated_estimated_delivery_time(distance_km : float , preparation_time_minutes : int = 20 , 
                                       average_speed_kmh : int = 30) -> datetime:
    travel_time_minutes = (distance_km / average_speed_kmh) * 60   
    
    total_minutes = preparation_time_minutes + travel_time_minutes
    
    return datetime.now() + timedelta(minutes= int(total_minutes))



def calculate_tax(subtotal: float, tax_rate: float = 0.08) -> float:
    
    return round(subtotal * tax_rate, 2)

def calculate_order_total(
    subtotal: float,
    delivery_fee: float,
    tax_rate: float = 0.08,
    discount_amount: float = 0.0
) -> Dict[str, float]:
    
    tax_amount = calculate_tax(subtotal, tax_rate)
    total = subtotal + delivery_fee + tax_amount - discount_amount
    
    return {
        'subtotal': round(subtotal, 2),
        'delivery_fee': round(delivery_fee, 2),
        'tax_amount': round(tax_amount, 2),
        'discount_amount': round(discount_amount, 2),
        'total_amount': round(total, 2)
    }
    

def generate_otp(length : int = 6) -> str:
    
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])     

def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix



def format_amount(amount : float , currency : str = 'INR') -> str:
    symbols = {
        'USD' : '$',
        "EUR": "€",
        "INR": "₹",
        "GBP": "£",
        "JPY": "¥"
        
    }
    
    symbol = symbols.get(currency.upper() , currency)
    
    return f"{symbol}{amount:,..2f}"
 
 
def parse_time_range(time_str: str) -> Optional[tuple]:
    
    try:
        start, end = time_str.split('-')
        start_hour, start_minute = map(int, start.split(':'))
        end_hour, end_minute = map(int, end.split(':'))
        return (start_hour, start_minute, end_hour, end_minute)
    except:
        return None

def is_within_business_hours(
    current_time: datetime,
    business_hours: str = "09:00-22:00"
) -> bool:
    
    time_range = parse_time_range(business_hours)
    if not time_range:
        return True
    
    start_hour, start_minute, end_hour, end_minute = time_range
    current_minutes = current_time.hour * 60 + current_time.minute
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    
    return start_minutes <= current_minutes <= end_minutes



def sanitize_filename(filename: str) -> str:
    
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    return filename.lower()    
    
            
     
def paginate_query(query, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    
    total = query.count()
    pages = (total + per_page - 1) // per_page
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages
    }
    
    
def mask_email(email: str) -> str:
    
    if '@' not in email:
        return email
    local, domain = email.split('@')
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


def mask_phone(phone: str) -> str:
    
    if len(phone) < 4:
        return phone
    return f"{phone[:2]}***{phone[-3:]}"


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    
    return dt.strftime(format_str)

def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    
    try:
        return datetime.strptime(date_str, format_str)
    except:
        return None

def get_time_ago(dt: datetime) -> str:
    
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

def chunk_list(lst: list, chunk_size: int) -> list:
   
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def remove_duplicates(lst: list) -> list:
    
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    
    try:
        return numerator / denominator if denominator != 0 else default
    except:
        return default

def calculate_percentage(part: float, whole: float) -> float:
   
    if whole == 0:
        return 0.0
    return round((part / whole) * 100, 2)

def generate_verification_token() -> str:
    
    return secrets.token_urlsafe(32)

def is_valid_latitude(lat: float) -> bool:
   
    return -90 <= lat <= 90

def is_valid_longitude(lon: float) -> bool:
    
    return -180 <= lon <= 180

def normalize_coordinates(lat: float, lon: float) -> Optional[tuple]:
   
    if is_valid_latitude(lat) and is_valid_longitude(lon):
        return (round(lat, 6), round(lon, 6))
    return None         
 
 
def get_client_ip(request) -> str:
    
    forwarded = request.headers.get("X-Forwarded-For")
    
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IO")
    if real_ip:
        return real_ip
    
def is_development() -> bool:
    
    from app.config import settings
    return settings.environment.lower() in ['development', 'dev', 'local']

def is_production() -> bool:
    
    from app.config import settings
    return settings.environment.lower() in ['production', 'prod']    