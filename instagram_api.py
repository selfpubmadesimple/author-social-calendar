"""
Instagram Graph API Integration
Handles OAuth flow, token management, and content publishing to Instagram Business accounts.
"""

import os
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Configuration
FB_GRAPH_VERSION = 'v21.0'
FB_APP_ID = os.environ.get('FACEBOOK_APP_ID')
FB_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET')

# OAuth URLs
AUTH_URL = f'https://www.facebook.com/{FB_GRAPH_VERSION}/dialog/oauth'
TOKEN_URL = f'https://graph.facebook.com/{FB_GRAPH_VERSION}/oauth/access_token'

# Required scopes for Instagram Graph API
SCOPES = [
    'instagram_basic',
    'instagram_content_publish',
    'pages_show_list',
    'pages_read_engagement'
]


class InstagramAPIError(Exception):
    """Custom exception for Instagram API errors"""
    pass


class InstagramAPI:
    """
    Instagram Graph API client for content publishing.
    
    Requires:
    - Instagram Business Account
    - Facebook Page linked to Instagram account
    - Facebook App with Instagram Graph API enabled
    """
    
    def __init__(self, access_token=None):
        self.access_token = access_token
        self.base_url = f'https://graph.facebook.com/{FB_GRAPH_VERSION}'
    
    @staticmethod
    def get_auth_url(redirect_uri, state=None):
        """
        Generate Facebook OAuth authorization URL.
        
        Args:
            redirect_uri: Callback URL after authorization
            state: CSRF protection token
            
        Returns:
            Authorization URL to redirect user to
        """
        scope = ','.join(SCOPES)
        params = {
            'client_id': FB_APP_ID,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'response_type': 'code'
        }
        if state:
            params['state'] = state
        
        from urllib.parse import urlencode
        return f"{AUTH_URL}?{urlencode(params)}"
    
    @staticmethod
    def exchange_code_for_token(code, redirect_uri):
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in get_auth_url
            
        Returns:
            dict: Token data including access_token and expires_in
        """
        try:
            # Get short-lived token
            params = {
                'client_id': FB_APP_ID,
                'client_secret': FB_APP_SECRET,
                'redirect_uri': redirect_uri,
                'code': code
            }
            
            response = requests.get(TOKEN_URL, params=params, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            
            short_lived_token = token_data.get('access_token')
            if not short_lived_token:
                raise InstagramAPIError('Failed to get access token')
            
            # Exchange for long-lived token (60 days)
            long_lived_params = {
                'grant_type': 'fb_exchange_token',
                'client_id': FB_APP_ID,
                'client_secret': FB_APP_SECRET,
                'fb_exchange_token': short_lived_token
            }
            
            long_lived_response = requests.get(TOKEN_URL, params=long_lived_params, timeout=10)
            long_lived_response.raise_for_status()
            long_lived_data = long_lived_response.json()
            
            access_token = long_lived_data.get('access_token', short_lived_token)
            expires_in = long_lived_data.get('expires_in', 3600)
            
            return {
                'access_token': access_token,
                'expires_in': expires_in,
                'expires_at': datetime.utcnow() + timedelta(seconds=expires_in)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {str(e)}")
            raise InstagramAPIError(f"Token exchange failed: {str(e)}")
    
    def get_instagram_account_id(self):
        """
        Get Instagram Business Account ID from connected Facebook Page.
        
        Returns:
            tuple: (instagram_account_id, page_access_token)
        """
        try:
            # Get Facebook Pages
            pages_url = f'{self.base_url}/me/accounts'
            pages_response = requests.get(pages_url, params={'access_token': self.access_token}, timeout=10)
            pages_response.raise_for_status()
            pages_data = pages_response.json()
            
            if not pages_data.get('data'):
                raise InstagramAPIError('No Facebook Pages found. Please connect a Facebook Page to your Instagram Business account.')
            
            # Get first page's Instagram account
            page = pages_data['data'][0]
            page_id = page['id']
            page_access_token = page.get('access_token', self.access_token)
            
            # Get Instagram Business Account ID
            ig_account_url = f'{self.base_url}/{page_id}'
            ig_account_params = {
                'fields': 'instagram_business_account',
                'access_token': page_access_token
            }
            ig_account_response = requests.get(ig_account_url, params=ig_account_params, timeout=10)
            ig_account_response.raise_for_status()
            ig_account_data = ig_account_response.json()
            
            ig_user_id = ig_account_data.get('instagram_business_account', {}).get('id')
            
            if not ig_user_id:
                raise InstagramAPIError('No Instagram Business Account linked to Facebook Page. Please link your Instagram Business account to your Facebook Page.')
            
            return ig_user_id, page_access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get Instagram account: {str(e)}")
            raise InstagramAPIError(f"Failed to get Instagram account: {str(e)}")
    
    def get_profile(self):
        """
        Fetch Instagram profile information.
        
        Returns:
            dict: Profile data including username, followers_count, etc.
        """
        try:
            ig_user_id, page_token = self.get_instagram_account_id()
            
            profile_url = f'{self.base_url}/{ig_user_id}'
            profile_params = {
                'fields': 'id,username,name,profile_picture_url,followers_count,follows_count,media_count',
                'access_token': page_token
            }
            
            response = requests.get(profile_url, params=profile_params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch profile: {str(e)}")
            raise InstagramAPIError(f"Failed to fetch profile: {str(e)}")
    
    def create_media_container(self, image_url, caption):
        """
        Create Instagram media container (Step 1 of publishing).
        
        Args:
            image_url: Publicly accessible URL of the image
            caption: Post caption with hashtags
            
        Returns:
            str: Media container ID
        """
        try:
            ig_user_id, page_token = self.get_instagram_account_id()
            
            # Create media container
            container_url = f'{self.base_url}/{ig_user_id}/media'
            container_params = {
                'image_url': image_url,
                'caption': caption,
                'access_token': page_token
            }
            
            response = requests.post(container_url, params=container_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            container_id = data.get('id')
            if not container_id:
                raise InstagramAPIError('Failed to create media container')
            
            logger.info(f"Created media container: {container_id}")
            return container_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create media container: {str(e)}")
            raise InstagramAPIError(f"Failed to create media container: {str(e)}")
    
    def publish_media_container(self, container_id):
        """
        Publish media container to Instagram (Step 2 of publishing).
        
        Args:
            container_id: ID from create_media_container
            
        Returns:
            str: Published media ID
        """
        try:
            ig_user_id, page_token = self.get_instagram_account_id()
            
            # Publish the container
            publish_url = f'{self.base_url}/{ig_user_id}/media_publish'
            publish_params = {
                'creation_id': container_id,
                'access_token': page_token
            }
            
            response = requests.post(publish_url, params=publish_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            media_id = data.get('id')
            if not media_id:
                raise InstagramAPIError('Failed to publish media container')
            
            logger.info(f"Published media: {media_id}")
            return media_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to publish media: {str(e)}")
            raise InstagramAPIError(f"Failed to publish media: {str(e)}")
    
    def publish_post(self, image_url, caption):
        """
        Complete workflow: Create and publish Instagram post.
        
        Args:
            image_url: Publicly accessible URL of the image
            caption: Post caption with hashtags
            
        Returns:
            str: Published media ID
        """
        # Step 1: Create container
        container_id = self.create_media_container(image_url, caption)
        
        # Step 2: Publish container
        media_id = self.publish_media_container(container_id)
        
        return media_id
