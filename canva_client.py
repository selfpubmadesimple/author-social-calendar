"""
Canva Connect API Client for Author Social Calendar
Handles OAuth authentication and image generation from text descriptions
"""
import os
import secrets
import hashlib
import base64
import logging
import requests
import urllib.parse
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CanvaClient:
    def __init__(self):
        self.client_id = os.environ.get('CANVA_CLIENT_ID')
        self.client_secret = os.environ.get('CANVA_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('CANVA_REDIRECT_URI', 'http://localhost:5000/auth/canva/callback')
        
        # Canva API endpoints
        self.auth_url = "https://www.canva.com/api/oauth/authorize"
        self.token_url = "https://www.canva.dev/api/oauth/token"
        self.api_base = "https://www.canva.dev/api/v1"
        
        # OAuth state storage (in production, use Redis or database)
        self.oauth_states = {}
        
    def generate_pkce_params(self):
        """Generate PKCE parameters for secure OAuth flow"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(96)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_auth_url(self, user_id=None):
        """Generate Canva OAuth authorization URL"""
        if not self.client_id:
            raise ValueError("CANVA_CLIENT_ID not configured")
        
        # Generate PKCE parameters
        code_verifier, code_challenge = self.generate_pkce_params()
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store PKCE params and state (use user_id as key if provided)
        session_key = user_id or 'default'
        self.oauth_states[session_key] = {
            'code_verifier': code_verifier,
            'state': state,
            'created_at': datetime.now()
        }
        
        # Clean up old states (older than 10 minutes)
        cutoff = datetime.now() - timedelta(minutes=10)
        self.oauth_states = {
            k: v for k, v in self.oauth_states.items() 
            if v['created_at'] > cutoff
        }
        
        # Required scopes for social media template creation
        scopes = [
            'design:read',
            'design:write', 
            'asset:read',
            'asset:write',
            'brandtemplate:read'
        ]
        
        auth_params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
            'response_type': 'code',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'state': state
        }
        
        return f"{self.auth_url}?{urllib.parse.urlencode(auth_params)}"
    
    def exchange_code_for_token(self, code, state, user_id=None):
        """Exchange authorization code for access token"""
        session_key = user_id or 'default'
        
        # Verify state and get PKCE params
        if session_key not in self.oauth_states:
            raise ValueError("Invalid OAuth state - session expired")
        
        oauth_data = self.oauth_states[session_key]
        if oauth_data['state'] != state:
            raise ValueError("Invalid OAuth state - possible CSRF attack")
        
        # Prepare token exchange request
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode('utf-8')
        ).decode('utf-8')
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'code_verifier': oauth_data['code_verifier'],
            'redirect_uri': self.redirect_uri
        }
        
        try:
            response = requests.post(self.token_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Clean up used OAuth state
            del self.oauth_states[session_key]
            
            return {
                'access_token': token_data['access_token'],
                'expires_in': token_data.get('expires_in', 14400),  # 4 hours default
                'token_type': token_data.get('token_type', 'Bearer'),
                'scope': token_data.get('scope'),
                'user_id': token_data.get('user', {}).get('id')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {e}")
            raise ValueError(f"Failed to exchange code for token: {e}")
    
    def create_design_from_template(self, access_token, template_id, title, text_content):
        """Create a new design from a Canva template with custom content"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Create design from template
        create_data = {
            'title': title,
            'design_type': 'social-media',
            'template_id': template_id
        }
        
        try:
            # Create design
            response = requests.post(
                f"{self.api_base}/designs", 
                headers=headers, 
                json=create_data
            )
            response.raise_for_status()
            design_data = response.json()
            design_id = design_data['design']['id']
            
            # Update text content (simplified - real implementation would need page/element targeting)
            update_data = {
                'operations': [
                    {
                        'type': 'set_text',
                        'element_id': 'text_element_1',  # Would need to discover actual element IDs
                        'value': text_content
                    }
                ]
            }
            
            # Note: This is a simplified example - real implementation would need:
            # 1. Get design pages/elements to find text elements
            # 2. Update specific text elements with provided content
            # 3. Handle different template structures
            
            return {
                'design_id': design_id,
                'design_url': design_data['design']['urls']['view_url'],
                'thumbnail_url': design_data['design'].get('thumbnail', {}).get('url')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Design creation failed: {e}")
            raise ValueError(f"Failed to create design: {e}")
    
    def export_design(self, access_token, design_id, format='PNG', quality='HD'):
        """Export a design as an image"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        export_data = {
            'format': format,
            'quality': quality,
            'pages': [1]  # Export first page
        }
        
        try:
            # Start export
            response = requests.post(
                f"{self.api_base}/designs/{design_id}/export",
                headers=headers,
                json=export_data
            )
            response.raise_for_status()
            export_data = response.json()
            
            # Get export job ID
            job_id = export_data['job']['id']
            
            # Poll for completion (simplified - should implement proper polling)
            import time
            for attempt in range(30):  # Wait up to 30 seconds
                status_response = requests.get(
                    f"{self.api_base}/export-jobs/{job_id}",
                    headers=headers
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                
                if status_data['job']['status'] == 'success':
                    # Return download URL for the exported image
                    return {
                        'success': True,
                        'download_url': status_data['job']['result']['export_url'],
                        'format': format,
                        'quality': quality
                    }
                elif status_data['job']['status'] == 'failed':
                    return {
                        'success': False,
                        'error': status_data['job'].get('error', 'Export failed')
                    }
                
                time.sleep(1)  # Wait 1 second before next check
            
            return {'success': False, 'error': 'Export timeout'}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Design export failed: {e}")
            return {'success': False, 'error': f"Export failed: {e}"}
    
    def search_templates(self, access_token, query, category='social-media'):
        """Search for Canva templates suitable for social media"""
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        params = {
            'query': query,
            'category': category,
            'limit': 10
        }
        
        try:
            response = requests.get(
                f"{self.api_base}/brand-templates", 
                headers=headers, 
                params=params
            )
            response.raise_for_status()
            
            templates_data = response.json()
            return {
                'success': True,
                'templates': templates_data.get('brand_templates', [])
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Template search failed: {e}")
            return {'success': False, 'error': f"Search failed: {e}"}

# Global client instance
canva_client = CanvaClient()