from fastapi import WebSocket
from typing import Dict , List , Optional
import asyncio
from app.core.logging import logger
import json


class ConnectionManager:
    def __init__(self):
        # Store connection by user_id
        
        self.user_connection : Dict[int , WebSocket] = {}
        
        # Store connecton by role for broadcasting
        
        self.role_connection : Dict[str , List[WebSocket]] = {
            "customer" : [],
            "restaurant_owner" : [],
            "delivery_partner" : [],
            "admin" : []
            
        }
        
    
    async def connect(self , websocket : WebSocket , user_id : int , user_role : str):
        await websocket.accept()
        
        self.user_connection[user_id] = websocket 
        
        if user_role in self.user_connection:
            self.role_connection[user_role].append(websocket)
        
        logger.info(f"Websocket is connected " , user_id=user_id , role = user_role)
    
    
    def disconnect(self , user_id : int , user_role : str):
        websocket = self.user_connection.remove(user_id)
        
        if websocket and user_role in self.role_connection:
            try:
                self.role_connection.remove(user_role)
            
            except ValueError:
                pass                   
        
        logger.info(f"Websocket Disconnected" , user_id = user_id , role = user_role)
    
    async def send_personal_msg(self , msg : dict , user_id : int):
        websocket = self.user_connection.get(user_id)
        
        if websocket:
            try:
                await websocket.send_text(json.dumps(msg))
            
            except Exception as e:
                logger.error(f"Failed to send personal message" , user_id = user_id , error = str(e)) 
                
                self.user_connection.pop(user_id , None)
                
    
    async def send_to_role(self , message :dict , role : str):
        if role not in self.role_connection:
            return 
        
        
        disconnected = []
        
        for websocket in self.role_connection[role]:
            try:
                await websocket.send_text(json.dumps(message))
            
            except Exception as e:
                logger.error(f"Failed to send role message" , role = role , error = str(e))
                
                disconnected.append(websocket)
                
        
        # clean up disconnected websockets 
        
        for ws in disconnected:
            try:
                self.role_connection[role].remove(ws)                            
        
            except ValueError:
                pass
    
    async def broadcast(self, msg :dict):
        disconnected_users = []
        
        for user_id , websocket in self.user_connection.items():
            try:
                await websocket.send_text(json.dumps(msg))    
                
            except Exception as e:
                logger.error(f"Failed to broadcast message" , user_id = user_id , error = str(e)) 
                
                disconnected_users.append(user_id)
                
         
         # clean  up disconnected users 
         
        for user_id in disconnected_users:
            self.user_connection.pop(user_id , None)
            

manager = ConnectionManager()            
                                   
