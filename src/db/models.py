from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .session import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(255), primary_key=True)  # From Clerk
    email = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user")

class Podcast(Base):
    __tablename__ = "podcasts"

    id = Column(UUID, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    publisher = Column(String(255))
    description = Column(Text)
    rss_url = Column(String(2048), nullable=False)
    
    # Relationships
    episodes = relationship("Episode", back_populates="podcast")
    subscriptions = relationship("Subscription", back_populates="podcast")

class Episode(Base):
    __tablename__ = "episodes"

    id = Column(UUID, primary_key=True, default=generate_uuid)
    podcast_id = Column(UUID, ForeignKey("podcasts.id"), nullable=False)
    rss_guid = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    publish_date = Column(DateTime(timezone=True))
    summary = Column(Text)
    
    # Relationships
    podcast = relationship("Podcast", back_populates="episodes")

class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id = Column(String(255), ForeignKey("users.id"), primary_key=True)
    podcast_id = Column(UUID, ForeignKey("podcasts.id"), primary_key=True)
    active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    podcast = relationship("Podcast", back_populates="subscriptions")
