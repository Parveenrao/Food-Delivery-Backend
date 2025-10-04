from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.websocket_manager import manager
from app.core.security import verify_token
from app.models.user import User
from app.core.logging import logger
import json

router = APIRouter()

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    '''WebSocket endpoint for real-time communication'''
    try:
        # Verify token
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=4001)
            return
        
        # Get user
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            await websocket.close(code=4001)
            return
        
        # Connect to WebSocket manager
        await manager.connect(websocket, user.id, user.role.value)
        
        try:
            while True:
                # Receive messages from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle different message types
                message_type = message_data.get('type')
                
                if message_type == 'ping':
                    await websocket.send_text(json.dumps({'type': 'pong'}))
                
                elif message_type == 'location_update' and user.role.value == 'delivery_partner':
                    # Handle delivery partner location updates
                    await handle_location_update(user.id, message_data, db)
                
                elif message_type == 'order_update' and user.role.value == 'restaurant_owner':
                    # Handle restaurant order updates
                    await handle_order_update(user.id, message_data, db)
                
        except WebSocketDisconnect:
            manager.disconnect(user.id, user.role.value)
            logger.info(f"WebSocket disconnected", user_id=user.id)
        
    except Exception as e:
        logger.error(f"WebSocket error", error=str(e))
        await websocket.close(code=4000)

async def handle_location_update(user_id: int, message_data: dict, db: Session):
    '''Handle delivery partner location updates'''
    try:
        latitude = message_data.get('latitude')
        longitude = message_data.get('longitude')
        order_id = message_data.get('order_id')
        
        if not all([latitude, longitude, order_id]):
            return
        
        # Update location in Redis for real-time tracking
        from app.utils.redis_client import redis_client
        location_data = {
            'user_id': user_id,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': message_data.get('timestamp'),
            'order_id': order_id
        }
        
        await redis_client.set(
            f"delivery_location:{user_id}:{order_id}",
            location_data,
            expire=300  # 5 minutes
        )
        
        # Notify customer about delivery partner location
        from app.models.order import Order
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            location_message = {
                'type': 'delivery_location_update',
                'order_id': order_id,
                'latitude': latitude,
                'longitude': longitude,
                'delivery_partner_id': user_id
            }
            
            await manager.send_personal_message(location_message, order.customer_id)
        
    except Exception as e:
        logger.error(f"Error handling location update", error=str(e))

async def handle_order_update(user_id: int, message_data: dict, db: Session):
    '''Handle restaurant order status updates'''
    try:
        order_id = message_data.get('order_id')
        new_status = message_data.get('status')
        
        if not all([order_id, new_status]):
            return
        
        # Verify restaurant owns the order
        from app.models.order import Order
        from app.models.restaurant import Restaurant
        
        order = db.query(Order).join(Restaurant).filter(
            Order.id == order_id,
            Restaurant.owner_id == user_id
        ).first()
        
        if order:
            # Trigger async order status update
            from app.task.order_task import update_order_status
            update_order_status.delay(order_id, new_status)
        
    except Exception as e:
        logger.error(f"Error handling order update", error=str(e))