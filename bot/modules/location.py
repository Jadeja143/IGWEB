"""
Location Module
Handles Instagram location-based operations using proper location search
"""

import logging
from typing import List, Dict, Any

log = logging.getLogger(__name__)

class LocationModule:
    """Instagram location operations"""
    
    def __init__(self, auth):
        self.auth = auth
    
    def search_locations(self, query: str) -> List[Dict[str, Any]]:
        """Search for locations using Instagram API"""
        if not self.auth.is_logged_in():
            raise Exception("Not logged in to Instagram")
        
        try:
            # Use Instagram's location search API
            locations = self.auth.with_client(self.auth.client.location_search, query)
            
            result = []
            for location in locations[:10]:  # Limit to 10 results
                result.append({
                    'pk': str(location.pk),
                    'name': location.name,
                    'address': getattr(location, 'address', ''),
                    'city': getattr(location, 'city', ''),
                    'short_name': getattr(location, 'short_name', location.name),
                    'lng': getattr(location, 'lng', 0),
                    'lat': getattr(location, 'lat', 0)
                })
            
            return result
            
        except Exception as e:
            log.exception("Error searching locations for query '%s': %s", query, e)
            return []
    
    def get_location_medias(self, location_pk: str, amount: int = 50) -> List[Dict[str, Any]]:
        """Get recent media from a location"""
        if not self.auth.is_logged_in():
            raise Exception("Not logged in to Instagram")
        
        try:
            medias = self.auth.with_client(
                self.auth.client.location_medias_recent,
                int(location_pk),
                amount=amount
            )
            
            result = []
            for media in medias:
                result.append({
                    'pk': str(media.pk),
                    'code': media.code,
                    'user_id': str(media.user.pk),
                    'username': media.user.username,
                    'caption': media.caption_text[:100] if media.caption_text else '',
                    'like_count': media.like_count,
                    'media_type': media.media_type,
                    'taken_at': media.taken_at.isoformat() if media.taken_at else ''
                })
            
            return result
            
        except Exception as e:
            log.exception("Error getting medias for location %s: %s", location_pk, e)
            return []
    
    def get_location_info(self, location_pk: str) -> Dict[str, Any]:
        """Get detailed information about a location"""
        if not self.auth.is_logged_in():
            raise Exception("Not logged in to Instagram")
        
        try:
            location = self.auth.with_client(self.auth.client.location_info, int(location_pk))
            
            return {
                'pk': str(location.pk),
                'name': location.name,
                'address': getattr(location, 'address', ''),
                'city': getattr(location, 'city', ''),
                'short_name': getattr(location, 'short_name', location.name),
                'lng': getattr(location, 'lng', 0),
                'lat': getattr(location, 'lat', 0),
                'external_source': getattr(location, 'external_source', ''),
                'facebook_places_id': getattr(location, 'facebook_places_id', 0)
            }
            
        except Exception as e:
            log.exception("Error getting location info for %s: %s", location_pk, e)
            return {}
    
    def add_default_location(self, location_name: str) -> str:
        """Add a location to default locations list"""
        from .database import execute_db
        from datetime import datetime
        
        try:
            # First search for the location to validate it exists
            locations = self.search_locations(location_name)
            if not locations:
                return f"❌ Location '{location_name}' not found on Instagram"
            
            # Use the first result
            location = locations[0]
            
            # Store in database
            execute_db(
                "INSERT OR REPLACE INTO locations (location, location_pk, added_at) VALUES (?, ?, ?)",
                (location['name'], location['pk'], datetime.now().isoformat())
            )
            
            return f"✅ Added location: {location['name']}"
            
        except Exception as e:
            log.exception("Error adding default location %s: %s", location_name, e)
            return f"❌ Error adding location: {e}"
    
    def remove_default_location(self, location_name: str) -> str:
        """Remove a location from default locations list"""
        from .database import execute_db
        
        try:
            execute_db("DELETE FROM locations WHERE location=?", (location_name,))
            return f"✅ Removed location: {location_name}"
            
        except Exception as e:
            log.exception("Error removing location %s: %s", location_name, e)
            return f"❌ Error removing location: {e}"
    
    def get_default_locations(self) -> List[Dict[str, str]]:
        """Get list of default locations"""
        from .database import fetch_db
        
        try:
            locations = fetch_db("SELECT location, location_pk FROM locations ORDER BY location")
            return [{'name': loc[0], 'pk': loc[1]} for loc in locations]
            
        except Exception as e:
            log.exception("Error getting default locations: %s", e)
            return []
