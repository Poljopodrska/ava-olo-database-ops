"""
Database Operations - Farmer CRM database connection
Connects to existing Windows PostgreSQL with real farmer data
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date
from decimal import Decimal
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import os
import sys

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL, DB_POOL_SETTINGS

logger = logging.getLogger(__name__)

class DatabaseOperations:
    """
    Database operations for existing farmer_crm database
    Connects to Windows PostgreSQL with real agricultural data
    """
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or DATABASE_URL
        # Ensure PostgreSQL only
        assert self.connection_string.startswith("postgresql://"), "❌ Only PostgreSQL connections allowed"
        
        # For WSL2 to Windows connection, we might need to adjust the connection
        if "host.docker.internal" in self.connection_string:
            # This is correct for WSL2 to Windows connection
            pass
        
        self.engine = create_engine(
            self.connection_string,
            **DB_POOL_SETTINGS
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    async def get_farmer_info(self, farmer_id: int) -> Optional[Dict[str, Any]]:
        """Get farmer information by ID"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT id, farm_name, manager_name, manager_last_name, 
                           city, wa_phone_number
                    FROM farmers 
                    WHERE id = :farmer_id
                    """),
                    {"farmer_id": farmer_id}
                ).fetchone()
                
                if result:
                    return {
                        "id": result[0],
                        "farm_name": result[1],
                        "manager_name": result[2],
                        "manager_last_name": result[3],
                        "total_hectares": 0,  # Default since column doesn't exist
                        "farmer_type": "Farm",  # Default since column doesn't exist
                        "city": result[4],
                        "wa_phone_number": result[5]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting farmer info: {str(e)}")
            return None
    
    async def get_all_farmers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of all farmers for UI selection"""
        try:
            with self.get_session() as session:
                results = session.execute(
                    text("""
                    SELECT id, farm_name, manager_name, manager_last_name, 
                           email, phone, city, wa_phone_number
                    FROM farmers 
                    ORDER BY farm_name
                    LIMIT :limit
                    """),
                    {"limit": limit}
                ).fetchall()
                
                farmers = []
                for row in results:
                    farmers.append({
                        "id": row[0],
                        "name": f"{row[2]} {row[3]}".strip() if row[2] and row[3] else "Unknown",
                        "farm_name": row[1] or "Unknown Farm",
                        "phone": row[5] or row[7] or "",
                        "location": row[6] or "",
                        "farm_type": "Farm",  # Default since column doesn't exist
                        "total_size_ha": 0.0  # Default since column doesn't exist
                    })
                
                return farmers
                
        except Exception as e:
            logger.error(f"Error getting all farmers: {str(e)}")
            return []
    
    async def get_farmer_fields(self, farmer_id: int) -> List[Dict[str, Any]]:
        """Get all fields for a farmer"""
        try:
            with self.get_session() as session:
                results = session.execute(
                    text("""
                    SELECT f.field_id, f.field_name, f.field_size, f.field_location,
                           f.soil_type, 
                           fc.crop_name, fc.variety, fc.planting_date, fc.status
                    FROM fields f
                    LEFT JOIN field_crops fc ON f.field_id = fc.field_id 
                        AND fc.status = 'active'
                    WHERE f.farmer_id = :farmer_id
                    ORDER BY f.field_name
                    """),
                    {"farmer_id": farmer_id}
                ).fetchall()
                
                fields = []
                for row in results:
                    fields.append({
                        "field_id": row[0],
                        "field_name": row[1],
                        "field_size": float(row[2]) if row[2] else 0,
                        "field_location": row[3],
                        "soil_type": row[4],
                        "current_crop": row[5],
                        "variety": row[6],
                        "planting_date": row[7].isoformat() if row[7] else None,
                        "crop_status": row[8]
                    })
                
                return fields
                
        except Exception as e:
            logger.error(f"Error getting farmer fields: {str(e)}")
            return []
    
    async def get_recent_conversations(self, farmer_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversations for context from incoming_messages table"""
        try:
            with self.get_session() as session:
                results = session.execute(
                    text("""
                    SELECT id, message_text, timestamp, role
                    FROM incoming_messages
                    WHERE farmer_id = :farmer_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                    """),
                    {"farmer_id": farmer_id, "limit": limit}
                ).fetchall()
                
                conversations = []
                for row in results:
                    conversations.append({
                        "id": row[0],
                        "user_input": row[1] if row[3] == 'user' else "",
                        "ava_response": row[1] if row[3] == 'assistant' else "",
                        "timestamp": row[2],
                        "message_type": "chat",
                        "confidence_score": 0.8,
                        "approved_status": False
                    })
                
                return conversations
                
        except Exception as e:
            logger.error(f"Error getting conversations: {str(e)}")
            return []
    
    async def save_conversation(self, farmer_id: int, conversation_data: Dict[str, Any]) -> Optional[int]:
        """Save a conversation to incoming_messages table"""
        try:
            with self.get_session() as session:
                # Save user message
                result1 = session.execute(
                    text("""
                    INSERT INTO incoming_messages (farmer_id, phone_number, message_text, role, timestamp)
                    VALUES (:farmer_id, :phone_number, :message_text, 'user', CURRENT_TIMESTAMP)
                    RETURNING id
                    """),
                    {
                        "farmer_id": farmer_id,
                        "phone_number": conversation_data.get("wa_phone_number", "unknown"),
                        "message_text": conversation_data.get("question")
                    }
                )
                
                # Save assistant response
                result2 = session.execute(
                    text("""
                    INSERT INTO incoming_messages (farmer_id, phone_number, message_text, role, timestamp)
                    VALUES (:farmer_id, :phone_number, :message_text, 'assistant', CURRENT_TIMESTAMP)
                    RETURNING id
                    """),
                    {
                        "farmer_id": farmer_id,
                        "phone_number": conversation_data.get("wa_phone_number", "unknown"),
                        "message_text": conversation_data.get("answer")
                    }
                )
                session.commit()
                conv_id = result2.scalar()
                
                logger.info(f"Saved conversation pair")
                return conv_id
                
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            return None
    
    async def get_crop_info(self, crop_name: str) -> Optional[Dict[str, Any]]:
        """Get crop information from crop_protection_croatia"""
        try:
            with self.get_session() as session:
                # First check if we have crop technology info
                result = session.execute(
                    text("""
                    SELECT DISTINCT crop_type
                    FROM crop_technology
                    WHERE LOWER(crop_type) = LOWER(:crop_name)
                    LIMIT 1
                    """),
                    {"crop_name": crop_name}
                ).fetchone()
                
                if result:
                    return {
                        "id": 1,
                        "crop_name": result[0],
                        "croatian_name": result[0],
                        "category": "Crop",
                        "planting_season": "Spring",
                        "harvest_season": "Fall",
                        "description": f"Information about {result[0]}"
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting crop info: {str(e)}")
            return None
    
    async def get_conversations_for_approval(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get conversations grouped by approval status for agronomic dashboard"""
        try:
            with self.get_session() as session:
                # Get latest user messages for each farmer
                results = session.execute(
                    text("""
                    WITH latest_messages AS (
                        SELECT DISTINCT ON (farmer_id) 
                               m.id, m.farmer_id, m.message_text, m.timestamp,
                               f.manager_name, f.manager_last_name, f.phone, 
                               f.city, f.farm_name
                        FROM incoming_messages m
                        JOIN farmers f ON m.farmer_id = f.id
                        WHERE m.role = 'user'
                        ORDER BY farmer_id, m.timestamp DESC
                    )
                    SELECT * FROM latest_messages
                    ORDER BY timestamp DESC
                    LIMIT 100
                    """)
                ).fetchall()
                
                # For now, all conversations are unapproved since the table doesn't have approval status
                unapproved = []
                
                for row in results:
                    conv = {
                        "id": row[0],
                        "farmer_id": row[1],
                        "farmer_name": f"{row[4]} {row[5]}".strip() if row[4] and row[5] else "Unknown",
                        "farmer_phone": row[6] or "",
                        "farmer_location": row[7] or "",
                        "farmer_type": "Farm",
                        "farmer_size": "0.0",
                        "last_message": row[2][:100] + "..." if row[2] and len(row[2]) > 100 else row[2] or "",
                        "timestamp": row[3]
                    }
                    unapproved.append(conv)
                
                return {"unapproved": unapproved, "approved": []}
                
        except Exception as e:
            logger.error(f"Error getting conversations for approval: {str(e)}")
            return {"unapproved": [], "approved": []}
    
    async def get_conversation_details(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed conversation information"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("""
                    SELECT m.id, m.farmer_id, m.message_text, m.timestamp, m.role,
                           f.manager_name, f.manager_last_name, f.phone, 
                           f.city, f.farm_name
                    FROM incoming_messages m
                    JOIN farmers f ON m.farmer_id = f.id
                    WHERE m.id = :conversation_id
                    """),
                    {"conversation_id": conversation_id}
                ).fetchone()
                
                if result:
                    return {
                        "id": result[0],
                        "farmer_id": result[1],
                        "farmer_name": f"{result[5]} {result[6]}".strip() if result[5] and result[6] else "Unknown",
                        "user_input": result[2] if result[4] == 'user' else "",
                        "ava_response": result[2] if result[4] == 'assistant' else "",
                        "timestamp": result[3],
                        "approved_status": False
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting conversation details: {str(e)}")
            return None

    async def health_check(self) -> bool:
        """Check database connectivity to farmer_crm database"""
        try:
            with self.get_session() as session:
                result = session.execute(text("SELECT COUNT(*) FROM farmers"))
                count = result.scalar()
                logger.info(f"Database health check: Connected to farmer_crm with {count} farmers")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

    async def test_windows_postgresql(self) -> bool:
        """Test connection to Windows PostgreSQL"""
        try:
            with self.get_session() as session:
                # Test farmers table
                farmer_count = session.execute(text("SELECT COUNT(*) FROM farmers")).scalar()
                print(f"✅ Connected to farmer_crm! Found {farmer_count} farmers")
                
                # Show some sample data
                farmers = session.execute(text("SELECT farm_name, manager_name, city FROM farmers LIMIT 5")).fetchall()
                print("\n📋 Sample farmers:")
                for farm in farmers:
                    print(f"  - {farm[0]}: {farm[1]} ({farm[2]})")
                
                # Test other tables
                tables = ['fields', 'field_crops', 'incoming_messages', 'crop_protection_croatia']
                print("\n📊 Table counts:")
                for table in tables:
                    count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"  - {table}: {count} records")
                
                return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False