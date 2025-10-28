"""
NATS JetStream Integration for Agentic Fabric
============================================

This module provides integration with NATS JetStream for event streaming and async operations.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union
from uuid import uuid4

import nats
from nats.aio.client import Client as NATSClient
from nats.js import JetStreamContext
from nats.js.api import StreamInfo
from pydantic import BaseModel, Field

from .exceptions import EventError

logger = logging.getLogger(__name__)


class EventMetadata(BaseModel):
    """Event metadata model"""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    version: str = "1.0"
    correlation_id: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    trace_id: Optional[str] = None


class ToolEvent(BaseModel):
    """Tool lifecycle event"""
    event_type: str  # registered, updated, deleted, invoked
    tool_id: str
    tool_name: str
    tool_type: str
    tenant_id: str
    metadata: EventMetadata
    payload: Dict[str, Any] = Field(default_factory=dict)


class InvocationEvent(BaseModel):
    """Agent/Tool invocation event"""
    event_type: str  # started, completed, failed
    invocation_id: str
    target_type: str  # agent, tool
    target_id: str
    tenant_id: str
    user_id: str
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    metadata: EventMetadata
    payload: Dict[str, Any] = Field(default_factory=dict)


class SecretEvent(BaseModel):
    """Secret management event"""
    event_type: str  # created, updated, deleted, rotated
    secret_path: str
    tenant_id: str
    user_id: str
    metadata: EventMetadata
    payload: Dict[str, Any] = Field(default_factory=dict)


Event = Union[ToolEvent, InvocationEvent, SecretEvent]


class EventStreamConfig(BaseModel):
    """Event stream configuration"""
    name: str
    subjects: List[str]
    description: str = ""
    max_msgs: int = 1000000
    max_age: int = 86400  # 24 hours in seconds
    storage: str = "file"  # file or memory
    replicas: int = 1
    retention: str = "limits"  # limits, interest, workqueue


class EventConsumerConfig(BaseModel):
    """Event consumer configuration"""
    name: str
    stream: str
    filter_subject: Optional[str] = None
    deliver_policy: str = "all"  # all, last, new
    ack_policy: str = "explicit"  # explicit, none, all
    max_deliver: int = 5
    replay_policy: str = "instant"  # instant, original
    durable: bool = True


class EventPublisher:
    """Event publisher for NATS JetStream"""
    
    def __init__(self, client: NATSClient, js: JetStreamContext):
        """Initialize event publisher"""
        self.client = client
        self.js = js
        
    async def publish_agent_event(
        self,
        event_type: str,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        tenant_id: str,
        source: str,
        payload: Optional[Dict] = None,
        correlation_id: Optional[str] = None
    ):
        """Publish agent lifecycle event - DEPRECATED"""
        # Agent events have been removed from the SDK
        # This method is kept for backward compatibility but does nothing
        pass
        
    async def publish_tool_event(
        self,
        event_type: str,
        tool_id: str,
        tool_name: str,
        tool_type: str,
        tenant_id: str,
        source: str,
        payload: Optional[Dict] = None,
        correlation_id: Optional[str] = None
    ):
        """Publish tool lifecycle event"""
        metadata = EventMetadata(
            source=source,
            correlation_id=correlation_id,
            tenant_id=tenant_id
        )
        
        event = ToolEvent(
            event_type=event_type,
            tool_id=tool_id,
            tool_name=tool_name,
            tool_type=tool_type,
            tenant_id=tenant_id,
            metadata=metadata,
            payload=payload or {}
        )
        
        subject = f"tools.{event_type}.{tenant_id}"
        await self._publish_event(subject, event)
        
    async def publish_invocation_event(
        self,
        event_type: str,
        invocation_id: str,
        target_type: str,
        target_id: str,
        tenant_id: str,
        user_id: str,
        source: str,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
        payload: Optional[Dict] = None,
        correlation_id: Optional[str] = None
    ):
        """Publish invocation event"""
        metadata = EventMetadata(
            source=source,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        event = InvocationEvent(
            event_type=event_type,
            invocation_id=invocation_id,
            target_type=target_type,
            target_id=target_id,
            tenant_id=tenant_id,
            user_id=user_id,
            duration_ms=duration_ms,
            error=error,
            metadata=metadata,
            payload=payload or {}
        )
        
        subject = f"invocations.{event_type}.{tenant_id}"
        await self._publish_event(subject, event)
        
    async def publish_secret_event(
        self,
        event_type: str,
        secret_path: str,
        tenant_id: str,
        user_id: str,
        source: str,
        payload: Optional[Dict] = None,
        correlation_id: Optional[str] = None
    ):
        """Publish secret management event"""
        metadata = EventMetadata(
            source=source,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        event = SecretEvent(
            event_type=event_type,
            secret_path=secret_path,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=metadata,
            payload=payload or {}
        )
        
        subject = f"secrets.{event_type}.{tenant_id}"
        await self._publish_event(subject, event)
        
    async def _publish_event(self, subject: str, event: Event):
        """Publish event to NATS JetStream"""
        try:
            message_data = event.model_dump_json()
            
            # Publish to JetStream
            await self.js.publish(
                subject=subject,
                payload=message_data.encode(),
                headers={
                    "event_id": event.metadata.event_id,
                    "timestamp": event.metadata.timestamp.isoformat(),
                    "source": event.metadata.source,
                    "version": event.metadata.version,
                    "tenant_id": event.metadata.tenant_id or "",
                    "user_id": event.metadata.user_id or "",
                    "correlation_id": event.metadata.correlation_id or "",
                }
            )
            
            logger.info(f"Published event {event.metadata.event_id} to {subject}")
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise EventError(f"Failed to publish event: {e}")


class EventSubscriber:
    """Event subscriber for NATS JetStream"""
    
    def __init__(self, client: NATSClient, js: JetStreamContext):
        """Initialize event subscriber"""
        self.client = client
        self.js = js
        self._subscriptions: Dict[str, Any] = {}
        
    async def subscribe_to_agent_events(
        self,
        handler: Callable,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        consumer_name: str = "agent-events-consumer"
    ):
        """Subscribe to agent events - DEPRECATED"""
        # Agent events have been removed from the SDK
        # This method is kept for backward compatibility but does nothing
        pass
        
    async def subscribe_to_tool_events(
        self,
        handler: Callable[[ToolEvent], Awaitable[None]],
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        consumer_name: str = "tool-events-consumer"
    ):
        """Subscribe to tool events"""
        subject = "tools.*"
        if tenant_id:
            subject += f".{tenant_id}"
        if event_type:
            subject = f"tools.{event_type}.*"
            
        await self._subscribe(subject, handler, consumer_name, ToolEvent)
        
    async def subscribe_to_invocation_events(
        self,
        handler: Callable[[InvocationEvent], Awaitable[None]],
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        consumer_name: str = "invocation-events-consumer"
    ):
        """Subscribe to invocation events"""
        subject = "invocations.*"
        if tenant_id:
            subject += f".{tenant_id}"
        if event_type:
            subject = f"invocations.{event_type}.*"
            
        await self._subscribe(subject, handler, consumer_name, InvocationEvent)
        
    async def subscribe_to_secret_events(
        self,
        handler: Callable[[SecretEvent], Awaitable[None]],
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        consumer_name: str = "secret-events-consumer"
    ):
        """Subscribe to secret events"""
        subject = "secrets.*"
        if tenant_id:
            subject += f".{tenant_id}"
        if event_type:
            subject = f"secrets.{event_type}.*"
            
        await self._subscribe(subject, handler, consumer_name, SecretEvent)
        
    async def _subscribe(
        self,
        subject: str,
        handler: Callable,
        consumer_name: str,
        event_class: type
    ):
        """Subscribe to events with given handler"""
        try:
            async def message_handler(msg):
                try:
                    # Parse event data
                    event_data = json.loads(msg.data.decode())
                    event = event_class.model_validate(event_data)
                    
                    # Call handler
                    await handler(event)
                    
                    # Acknowledge message
                    await msg.ack()
                    
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    await msg.nak()
                    
            # Subscribe to the subject
            subscription = await self.js.subscribe(
                subject=subject,
                cb=message_handler,
                durable=consumer_name,
                config=nats.js.api.ConsumerConfig(
                    durable_name=consumer_name,
                    ack_policy=nats.js.api.AckPolicy.EXPLICIT,
                    max_deliver=5,
                    deliver_policy=nats.js.api.DeliverPolicy.ALL,
                )
            )
            
            self._subscriptions[consumer_name] = subscription
            logger.info(f"Subscribed to {subject} with consumer {consumer_name}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {subject}: {e}")
            raise EventError(f"Failed to subscribe to {subject}: {e}")
            
    async def unsubscribe(self, consumer_name: str):
        """Unsubscribe from events"""
        if consumer_name in self._subscriptions:
            await self._subscriptions[consumer_name].unsubscribe()
            del self._subscriptions[consumer_name]
            logger.info(f"Unsubscribed consumer {consumer_name}")


class EventStreamManager:
    """NATS JetStream manager for event streaming"""
    
    def __init__(self, nats_url: str = "nats://localhost:4222", publish_timeout: float = 5.0):
        """Initialize event stream manager
        
        Args:
            nats_url: NATS server URL
            publish_timeout: Timeout in seconds for publish operations (default: 5.0)
        """
        self.nats_url = nats_url
        self.publish_timeout = publish_timeout
        self.client: Optional[NATSClient] = None
        self.js: Optional[JetStreamContext] = None
        self.publisher: Optional[EventPublisher] = None
        self.subscriber: Optional[EventSubscriber] = None
        
    async def connect(self):
        """Connect to NATS JetStream"""
        try:
            # Connect with longer timeout and reconnect settings
            self.client = await nats.connect(
                self.nats_url,
                connect_timeout=10,
                reconnect_time_wait=2,
                max_reconnect_attempts=5,
            )
            # jetstream() may be async in mocks; support both
            js_obj = self.client.jetstream()
            self.js = await js_obj if asyncio.iscoroutine(js_obj) else js_obj
            
            # Initialize publisher and subscriber
            self.publisher = EventPublisher(self.client, self.js)
            self.subscriber = EventSubscriber(self.client, self.js)
            
            logger.info(f"Connected to NATS JetStream at {self.nats_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise EventError(f"Failed to connect to NATS: {e}")
    
    def is_connected(self) -> bool:
        """Check if NATS client is connected"""
        return self.client is not None and self.client.is_connected and self.js is not None

    async def emit_audit_event(self, subject: str, payload: Dict[str, Any]) -> None:
        """Publish an audit event to the AUDIT stream. Subject should start with 'audit.'"""
        # Check connection health first
        if not self.is_connected():
            logger.warning("NATS not connected, skipping audit event publish")
            return
            
        if not subject.startswith("audit."):
            subject = f"audit.{subject}"
        try:
            # Ensure JSON-serializable payload (e.g., datetime)
            def _json_default(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)
            serialized = json.dumps(payload, default=_json_default)
            
            # Publish with timeout
            await asyncio.wait_for(
                self.js.publish(subject=subject, payload=serialized.encode()),
                timeout=self.publish_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Audit event publish timed out after {self.publish_timeout}s")
        except Exception as e:
            logger.warning(f"Failed to publish audit event: {e}")
            # Don't raise - audit is best-effort
            
    async def disconnect(self):
        """Disconnect from NATS JetStream"""
        if self.client:
            await self.client.close()
            self.client = None
            self.js = None
            self.publisher = None
            self.subscriber = None
            logger.info("Disconnected from NATS JetStream")
            
    async def create_stream(self, config: EventStreamConfig):
        """Create or update a JetStream stream"""
        try:
            if not self.js:
                raise EventError("Not connected to NATS JetStream")
                
            stream_config = nats.js.api.StreamConfig(
                name=config.name,
                subjects=config.subjects,
                description=config.description,
                max_msgs=config.max_msgs,
                max_age=config.max_age,
                storage=nats.js.api.StorageType.FILE if config.storage == "file" else nats.js.api.StorageType.MEMORY,
                num_replicas=config.replicas,
                retention=nats.js.api.RetentionPolicy.LIMITS,
            )
            
            # Create or update stream
            await self.js.add_stream(stream_config)
            logger.info(f"Created/updated stream: {config.name}")
            
        except Exception as e:
            logger.error(f"Failed to create stream {config.name}: {e}")
            raise EventError(f"Failed to create stream {config.name}: {e}")
            
    async def delete_stream(self, stream_name: str):
        """Delete a JetStream stream"""
        try:
            if not self.js:
                raise EventError("Not connected to NATS JetStream")
                
            await self.js.delete_stream(stream_name)
            logger.info(f"Deleted stream: {stream_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete stream {stream_name}: {e}")
            raise EventError(f"Failed to delete stream {stream_name}: {e}")
            
    async def list_streams(self) -> List[StreamInfo]:
        """List all JetStream streams"""
        try:
            if not self.js:
                raise EventError("Not connected to NATS JetStream")
                
            # Use the correct method to get stream info
            stream_iterator = await self.js.streams_info_iterator()
            stream_dicts = stream_iterator.streams
            
            # Convert dict responses to StreamInfo objects if needed
            streams = []
            for stream_dict in stream_dicts:
                if hasattr(stream_dict, 'config'):
                    # Already a StreamInfo object
                    streams.append(stream_dict)
                else:
                    # Convert dict to StreamInfo using NATS StreamInfo.from_response
                    from nats.js.api import StreamInfo
                    stream_info = StreamInfo.from_response(stream_dict)
                    streams.append(stream_info)
                
            return streams
            
        except Exception as e:
            logger.error(f"Failed to list streams: {e}")
            raise EventError(f"Failed to list streams: {e}")
            
    async def get_stream_info(self, stream_name: str) -> StreamInfo:
        """Get information about a stream"""
        try:
            if not self.js:
                raise EventError("Not connected to NATS JetStream")
                
            return await self.js.stream_info(stream_name)
            
        except Exception as e:
            logger.error(f"Failed to get stream info for {stream_name}: {e}")
            raise EventError(f"Failed to get stream info for {stream_name}: {e}")
            
    async def setup_default_streams(self):
        """Set up default event streams"""
        default_streams = [
            EventStreamConfig(
                name="AGENTS",
                subjects=["agents.>"],
                description="Agent lifecycle events",
                max_msgs=1000000,
                max_age=604800,  # 7 days
            ),
            EventStreamConfig(
                name="TOOLS",
                subjects=["tools.>"],
                description="Tool lifecycle events",
                max_msgs=1000000,
                max_age=604800,  # 7 days
            ),
            EventStreamConfig(
                name="INVOCATIONS",
                subjects=["invocations.>"],
                description="Agent and tool invocation events",
                max_msgs=5000000,
                max_age=2592000,  # 30 days
            ),
            EventStreamConfig(
                name="SECRETS",
                subjects=["secrets.>"],
                description="Secret management events",
                max_msgs=100000,
                max_age=7776000,  # 90 days
            ),
        ]
        
        for stream_config in default_streams:
            await self.create_stream(stream_config)
            
        logger.info("Set up default event streams")

    async def setup_audit_stream(self) -> None:
        """Create AUDIT stream for audit logging events."""
        if not self.js:
            raise EventError("Not connected to NATS JetStream")

        audit_stream = EventStreamConfig(
            name="AUDIT",
            subjects=["audit.>"],
            description="Audit logging events",
            max_msgs=10_000_000,
            max_age=90 * 24 * 3600,  # 90 days
            storage="file",
            replicas=1,
        )
        await self.create_stream(audit_stream)
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


# Convenience functions
async def setup_event_streaming(nats_url: str = "nats://localhost:4222") -> EventStreamManager:
    """Set up event streaming with default configuration"""
    manager = EventStreamManager(nats_url)
    await manager.connect()
    await manager.setup_default_streams()
    return manager


async def publish_agent_registered(
    publisher: EventPublisher,
    agent_id: str,
    agent_name: str,
    agent_type: str,
    tenant_id: str,
    payload: Optional[Dict] = None
):
    """Convenience function to publish agent registered event - DEPRECATED"""
    # Agent events have been removed from the SDK
    # This function is kept for backward compatibility but does nothing
    pass


async def publish_invocation_started(
    publisher: EventPublisher,
    invocation_id: str,
    target_type: str,
    target_id: str,
    tenant_id: str,
    user_id: str,
    payload: Optional[Dict] = None
):
    """Convenience function to publish invocation started event"""
    await publisher.publish_invocation_event(
        event_type="started",
        invocation_id=invocation_id,
        target_type=target_type,
        target_id=target_id,
        tenant_id=tenant_id,
        user_id=user_id,
        source="af_gateway",
        payload=payload
    )


async def publish_invocation_completed(
    publisher: EventPublisher,
    invocation_id: str,
    target_type: str,
    target_id: str,
    tenant_id: str,
    user_id: str,
    duration_ms: int,
    payload: Optional[Dict] = None
):
    """Convenience function to publish invocation completed event"""
    await publisher.publish_invocation_event(
        event_type="completed",
        invocation_id=invocation_id,
        target_type=target_type,
        target_id=target_id,
        tenant_id=tenant_id,
        user_id=user_id,
        source="af_gateway",
        duration_ms=duration_ms,
        payload=payload
    ) 