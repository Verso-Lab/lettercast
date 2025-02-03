from typing import List

from sqlalchemy import Boolean, Column, DateTime, ForeignKeyConstraint, JSON, PrimaryKeyConstraint, Text, UniqueConstraint, Uuid, text, event
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.base import Mapped

Base = declarative_base()


class Podcasts(Base):
    __tablename__ = 'podcasts'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='podcasts_pkey'),
        UniqueConstraint('rss_url', name='podcasts_rss_url_key')
    )

    id = mapped_column(Uuid, server_default=text('gen_random_uuid()'))
    name = mapped_column(Text, nullable=False)
    rss_url = mapped_column(Text, nullable=False)
    publisher = mapped_column(Text)
    description = mapped_column(Text)
    image_url = mapped_column(Text)
    created_at = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))
    frequency = mapped_column(Text)
    tags = mapped_column(JSON)
    category = mapped_column(Text)
    prompt_addition = mapped_column(Text)

    episodes: Mapped[List['Episodes']] = relationship('Episodes', uselist=True, back_populates='podcast')
    subscriptions: Mapped[List['Subscriptions']] = relationship('Subscriptions', uselist=True, back_populates='podcast')


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='users_pkey'),
        UniqueConstraint('email', name='users_email_key')
    )

    id = mapped_column(Text)
    email = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))

    subscriptions: Mapped[List['Subscriptions']] = relationship('Subscriptions', uselist=True, back_populates='user')


class Episodes(Base):
    __tablename__ = 'episodes'
    __table_args__ = (
        ForeignKeyConstraint(['podcast_id'], ['podcasts.id'], ondelete='CASCADE', name='episodes_podcast_id_fkey'),
        PrimaryKeyConstraint('id', name='episodes_pkey'),
        UniqueConstraint('podcast_id', 'rss_guid', name='episodes_podcast_id_rss_guid_key')
    )

    id = mapped_column(Uuid, server_default=text('gen_random_uuid()'))
    podcast_id = mapped_column(Uuid, nullable=False)
    rss_guid = mapped_column(Text, nullable=False)
    title = mapped_column(Text, nullable=False)
    episode_description = mapped_column(Text)
    publish_date = mapped_column(DateTime(True), nullable=False)
    summary = mapped_column(Text)
    created_at = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))

    podcast: Mapped['Podcasts'] = relationship('Podcasts', back_populates='episodes')


class Subscriptions(Base):
    __tablename__ = 'subscriptions'
    __table_args__ = (
        ForeignKeyConstraint(['podcast_id'], ['podcasts.id'], ondelete='CASCADE', name='subscriptions_podcast_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='subscriptions_user_id_fkey'),
        PrimaryKeyConstraint('user_id', 'podcast_id', name='subscriptions_pkey')
    )

    user_id = mapped_column(Text, nullable=False)
    podcast_id = mapped_column(Uuid, nullable=False)
    active = mapped_column(Boolean, nullable=False, server_default=text('true'))
    created_at = mapped_column(DateTime(True), server_default=text('CURRENT_TIMESTAMP'))

    podcast: Mapped['Podcasts'] = relationship('Podcasts', back_populates='subscriptions')
    user: Mapped['Users'] = relationship('Users', back_populates='subscriptions')

@event.listens_for(Episodes, 'init')
def init_summary(target, args, kwargs):
    """Initialize summary with decoded newlines"""
    if 'summary' in kwargs and kwargs['summary']:
        kwargs['summary'] = kwargs['summary'].replace('\n', '\\n')

@event.listens_for(Episodes.summary, 'set')
def encode_newlines(target, value, oldvalue, initiator):
    """Encode newlines when setting summary"""
    if value:
        return value.replace('\n', '\\n')
    return value

@event.listens_for(Episodes, 'load')
def decode_newlines(target, context):
    """Decode newlines after loading from database"""
    if target.summary:
        target.summary = target.summary.replace('\\n', '\n')
