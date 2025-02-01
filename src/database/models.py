from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, MetaData, text
from sqlalchemy.dialects.postgresql import UUID
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
    __table_args__ = {'extend_existing': True}

    id = Column(UUID, primary_key=True, server_default=text('gen_random_uuid()'))
    name = Column(Text, nullable=False)
    publisher = Column(Text)
    description = Column(Text)
    rss_url = Column(Text, nullable=False)
    image_url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'))
    frequency = Column(Text)
    tags = Column(JSON)
    category = Column(Text)
    prompt_addition = Column(Text)

    episodes = relationship("Episode", back_populates="podcast")

class Episode(Base):
    __tablename__ = "episodes"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID, primary_key=True, server_default=text('gen_random_uuid()'))
    podcast_id = Column(UUID, ForeignKey("podcasts.id"), nullable=False)
    rss_guid = Column(Text, nullable=False, unique=True)
    title = Column(Text, nullable=False)
    publish_date = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'))

    podcast = relationship("Podcast", back_populates="episodes") 
