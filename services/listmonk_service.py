"""Listmonk integration service for managing email subscribers."""

import logging
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, Optional
from config import LISTMONK_URL, LISTMONK_API_KEY, LISTMONK_ENABLED

# Configure logging
logger = logging.getLogger(__name__)


def get_subscriber_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get subscriber information by email address.
    
    Args:
        email: Email address to search for
        
    Returns:
        Subscriber data dict if found, None if not found or error
    """
    if not LISTMONK_ENABLED:
        logger.info("Listmonk integration disabled - skipping subscriber lookup")
        return None
        
    if not LISTMONK_API_KEY:
        logger.warning("Listmonk API key not configured - skipping subscriber lookup")
        return None
    
    try:
        url = f"{LISTMONK_URL}/api/subscribers"
        params = {
            "query": f"subscribers.email = '{email}'",
            "per_page": "1",
            "page": "1"
        }
        
        response = requests.get(
            url, 
            auth=HTTPBasicAuth("admin", LISTMONK_API_KEY), 
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch subscriber {email}. Status: {response.status_code}, Response: {response.text}")
            return None
            
        data = response.json().get("data", {}).get("results", [])
        if not data:
            logger.info(f"No subscriber found in Listmonk for email: {email}")
            return None
            
        subscriber = data[0]
        logger.info(f"Found Listmonk subscriber ID {subscriber['id']} for email {email}")
        return subscriber
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching subscriber {email}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching subscriber {email}: {e}")
        return None


def delete_subscriber_by_email(email: str) -> Dict[str, Any]:
    """
    Delete a subscriber from Listmonk by email address.
    
    Args:
        email: Email address of subscriber to delete
        
    Returns:
        Dict with success status and details
    """
    result = {
        "success": False,
        "email": email,
        "subscriber_id": None,
        "error": None,
        "skipped": False
    }
    
    if not LISTMONK_ENABLED:
        result["skipped"] = True
        result["error"] = "Listmonk integration disabled"
        logger.info("Listmonk integration disabled - skipping subscriber deletion")
        return result
        
    if not LISTMONK_API_KEY:
        result["skipped"] = True
        result["error"] = "Listmonk API key not configured"
        logger.warning("Listmonk API key not configured - skipping subscriber deletion")
        return result
    
    try:
        # First, get the subscriber ID
        subscriber = get_subscriber_by_email(email)
        if not subscriber:
            result["error"] = "Subscriber not found in Listmonk"
            logger.info(f"No subscriber found in Listmonk for {email} - nothing to delete")
            return result
            
        subscriber_id = subscriber["id"]
        result["subscriber_id"] = subscriber_id
        
        # Delete the subscriber
        url = f"{LISTMONK_URL}/api/subscribers/{subscriber_id}"
        response = requests.delete(
            url, 
            auth=HTTPBasicAuth("admin", LISTMONK_API_KEY),
            timeout=10
        )
        
        if response.status_code == 200:
            result["success"] = True
            logger.info(f"Successfully deleted Listmonk subscriber ID {subscriber_id} for email {email}")
        else:
            result["error"] = f"Delete failed with status {response.status_code}: {response.text}"
            logger.error(f"Failed to delete Listmonk subscriber {subscriber_id}. Status: {response.status_code}, Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        result["error"] = f"Network error: {e}"
        logger.error(f"Network error while deleting subscriber {email}: {e}")
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
        logger.error(f"Unexpected error while deleting subscriber {email}: {e}")
    
    return result


def add_subscriber(email: str, name: str = "", lists: list = None) -> Dict[str, Any]:
    """
    Add a subscriber to Listmonk.
    
    Args:
        email: Email address
        name: Subscriber name (optional)
        lists: List of list IDs to subscribe to (optional)
        
    Returns:
        Dict with success status and details
    """
    result = {
        "success": False,
        "email": email,
        "subscriber_id": None,
        "error": None,
        "skipped": False
    }
    
    if not LISTMONK_ENABLED:
        result["skipped"] = True
        result["error"] = "Listmonk integration disabled"
        logger.info("Listmonk integration disabled - skipping subscriber creation")
        return result
        
    if not LISTMONK_API_KEY:
        result["skipped"] = True
        result["error"] = "Listmonk API key not configured"
        logger.warning("Listmonk API key not configured - skipping subscriber creation")
        return result
    
    try:
        url = f"{LISTMONK_URL}/api/subscribers"
        data = {
            "email": email,
            "name": name,
            "status": "enabled",
            "lists": lists or [],
            "preconfirm_subscriptions": True
        }
        
        response = requests.post(
            url,
            auth=HTTPBasicAuth("admin", LISTMONK_API_KEY),
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            subscriber_data = response.json().get("data", {})
            result["success"] = True
            result["subscriber_id"] = subscriber_data.get("id")
            logger.info(f"Successfully added Listmonk subscriber for email {email}")
        else:
            result["error"] = f"Add failed with status {response.status_code}: {response.text}"
            logger.error(f"Failed to add Listmonk subscriber {email}. Status: {response.status_code}, Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        result["error"] = f"Network error: {e}"
        logger.error(f"Network error while adding subscriber {email}: {e}")
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
        logger.error(f"Unexpected error while adding subscriber {email}: {e}")
    
    return result
