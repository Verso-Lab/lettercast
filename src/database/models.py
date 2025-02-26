from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, JSON
from uuid import UUID
from sqlalchemy import text, JSON, UniqueConstraint, TIMESTAMP, TypeDecorator, String
from datetime import datetime

class NewlineString(TypeDecorator):
    """Custom type for handling newline characters in database strings."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Escape newlines when saving to database."""
        if value is not None:
            return value.replace('\n', '\\n')
        return None

    def process_result_value(self, value, dialect):
        """Unescape newlines when loading from database."""
        if value is not None:
            return value.replace('\\n', '\n')
        return None

class TimestampMixin(SQLModel):
    """Add created_at timestamp to models."""
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )

class PodcastBase(SQLModel):
    name: str = Field(nullable=False)
    rss_url: str = Field(nullable=False, sa_column_kwargs={"unique": True})
    publisher: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    frequency: Optional[float] = None
    tags: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)
    category: str
    prompt_addition: Optional[str] = None

class Podcast(PodcastBase, TimestampMixin, table=True):
    __tablename__ = "podcasts"
    
    id: UUID = Field(
        default=None,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
        primary_key=True
    )
    
    episodes: List["Episode"] = Relationship(back_populates="podcast")
    subscriptions: List["Subscription"] = Relationship(back_populates="podcast")

class UserBase(SQLModel):
    email: str = Field(nullable=False, sa_column_kwargs={"unique": True})

class User(UserBase, TimestampMixin, table=True):
    __tablename__ = "users"
    
    id: str = Field(primary_key=True)
    subscriptions: List["Subscription"] = Relationship(back_populates="user")

class EpisodeBase(SQLModel):
    rss_guid: str = Field(nullable=False)
    title: str = Field(nullable=False)
    episode_description: Optional[str] = None
    publish_date: datetime = Field(nullable=False, sa_type=TIMESTAMP(timezone=True))
    summary: Optional[str] = Field(default=None, sa_type=NewlineString)

class Episode(EpisodeBase, TimestampMixin, table=True):
    __tablename__ = "episodes"
    __table_args__ = (
        UniqueConstraint("podcast_id", "rss_guid"),
    )
    
    id: UUID = Field(
        default=None,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
        primary_key=True
    )
    podcast_id: UUID = Field(foreign_key="podcasts.id")
    podcast: Optional[Podcast] = Relationship(back_populates="episodes")

    @property
    def is_processed(self) -> bool:
        return self.created_at is not None

class SubscriptionBase(SQLModel):
    active: bool = Field(default=True, nullable=False)

class Subscription(SubscriptionBase, TimestampMixin, table=True):
    __tablename__ = "subscriptions"

    user_id: str = Field(foreign_key="users.id", primary_key=True)
    podcast_id: UUID = Field(foreign_key="podcasts.id", primary_key=True)
    
    podcast: Podcast = Relationship(back_populates="subscriptions")
    user: User = Relationship(back_populates="subscriptions")
