from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, MetaData
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import pytz

# Create Base with explicit naming convention
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

class Podcast(Base):
    __tablename__ = "podcasts"
    __table_args__ = {'extend_existing': True}  # Allow reflection of existing table

    id = Column(String, primary_key=True)
    podcast_name = Column(String)
    rss_url = Column(String)
    publisher = Column(String)
    description = Column(Text)
    image_url = Column(String)
    frequency = Column(String)
    tags = Column(JSON)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

    episodes = relationship("Episode", back_populates="podcast")

class Episode(Base):
    __tablename__ = "episodes"
    __table_args__ = {'extend_existing': True}  # Allow reflection of existing table

    id = Column(String, primary_key=True)
    podcast_id = Column(String, ForeignKey("podcasts.id"))
    rss_guid = Column(String)
    episode_name = Column(String)
    publish_date = Column(DateTime(timezone=True))
    url = Column(String)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    newsletter_path = Column(String)

    podcast = relationship("Podcast", back_populates="episodes") 
