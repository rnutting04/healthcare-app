import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from .auth import verify_websocket_token

logger = logging.getLogger(__name__)

class TranslationConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for real-time translation updates with authentication"""

    async def connect(self):
        """Handle WebSocket connection with authentication"""
        self.authenticated = False
        self.user_id = None
        # Set to track group subscriptions for this connection, ensuring efficient cleanup on disconnect
        self.subscribed_groups = set()

        # Don't accept connection yet - wait for authentication
        await self.accept()
        
        # Send authentication request
        await self.send_json({
            'type': 'auth_required',
            'message': 'Please authenticate with your JWT token.'
        })

        logger.info("WebSocket connection created, pending authentication for job {self.job_id}.")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Unsubscribe from all groups this connection was part of
        for group_name in self.subscribed_groups:
            await self.channel_layer.group_discard(
                group_name,
                self.channel_name
            )
        
        if self.authenticated:
            logger.info(f"WebSocket disconnected for job {self.job_id} (user: {self.user_id})")
        else:
            logger.info(f"Unauthenticated WebSocket disconnected for job {self.job_id}")

    async def receive_json(self, content):
        """Handle incoming WebSocket messages"""
        try:
            message_type = content.get('type')

            if message_type == 'authenticate':
                await self.handle_authentication(content)
                return

            if not self.authenticated:
                await self.send_json({
                    'type': 'error',
                    'message': 'Authentication required.'
                })
                return

            # Routes for authenticated clients
            if message_type == 'subscribe_to_translations':
                await self.handle_subscription(content)
            elif message_type == 'ping':
                await self.send_json({'type': 'pong'})
            else:
                await self.send_json({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                })

        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
            
            await self.send_json({
                'type': 'error',
                'message': 'An unexpected error occured on the server'
            })

    async def handle_authentication(self, auth_data):
        """
        Verifies the JWT sent by the client
        """
        token = auth_data.get('token')

        if not token:
            await self.send_json({
                'type': 'auth_failed',
                'message': 'Token not provided.'
            })
            return

        payload, error = verify_websocket_token(token)

        if error:
            await self.send_json({
                'type': 'auth_failed',
                'message': error
            })
            return
            
        # Authentication sucessful
        self.authenticated = True
        self.user_id = payload.get('user_id')
        
        await self.send_json({
            'type': 'auth_success',
            'message': 'Authentication successful.'
        })

        logger.info(f"WebSocket authenticated for job {self.job_id} (user: {self.user_id})")

    async def handle_subscription(self, content):
        """
        Subscribes the authenticated client to one or more translation job groups.
        """
        request_ids = content.get("request_ids", [])
        #check for expected format
        if not isinstance(request_ids, list):
            await self.send_json({
                'type': 'error',
                'message': 'request_ids must be a list.'
            })
            return

        for request_id in request_ids:
            group_name = f"translation_{request_id}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            self.subscribed_groups.add(group_name)

        logger.info(f"User {self.user_id} subscribed to translation groups: {request_ids}")

        await self.send_json({
            'type': 'subscription_success',
            'subscribed_ids': request_ids
        })

    # --- Channel Layer Message Handlers ---

    async def translation_complete(self, event):
        """
        Handles 'job complete' messages from the channel layer.
        This is called when the worker finishes successfully.
        """
        await self.send_json({
            'type': 'job_complete',
            'job_id': event['job_id'],
            'status': 'completed',
            'result': event['result'],
        })

    async def translation_error(self, event):
        """
        Handles 'job error' messages from the channel layer.
        This is called when the worker fails.
        """
        await self.send_json({
            'type': 'job_error',
            'job_id': event['job_id'],
            'status': 'failed',
            'message': event['message'],
        })