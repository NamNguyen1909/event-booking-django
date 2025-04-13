# events/signals.py

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Tag,Event

@receiver(post_migrate)
def create_default_tags_and_users(sender, **kwargs):
    # Tạo các tag mặc định
    default_tags = [
        'tech', 'health', 'education', 'religious', 'charity', 'networking',
        'startup', 'career', 'family', 'kids', 'outdoor', 'indoor',
        'free', 'paid', 'food', 'drink', 'fashion', 'environment',
        'art', 'film', 'sports_fan', 'fitness', 'music_band',
        'political', 'science', 'literature', 'music'
    ]
    for tag_name in default_tags:
        Tag.objects.get_or_create(name=tag_name)

    # Tạo superuser mặc định
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@gmail.com',
            password='123'
        )

    # Tạo user organizer mặc định
    if not User.objects.filter(username='organizer01').exists():
        User.objects.create_user(
            username='organizer01',
            email='organizer01@gmail.com',
            password='123',
            role='organizer'
        )

    # Tạo user attendee mặc định
    if not User.objects.filter(username='attendee01').exists():
        User.objects.create_user(
            username='attendee01',
            email='attendee01@gmail.com',
            password='123',
            role='attendee'
        )
        # Tạo superuser mặc định
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@gmail.com',
            password='123'
        )

    # Tạo user organizer mặc định
    if not User.objects.filter(username='organizer01').exists():
        organizer = User.objects.create_user(
            username='organizer01',
            email='organizer01@gmail.com',
            password='123',
            role='organizer'
        )
    else:
        organizer = User.objects.get(username='organizer01')

    # Tạo 3 sự kiện mặc định
    if not Event.objects.filter(title='Tech Conference').exists():
        event1 = Event.objects.create(
            organizer=organizer,
            title='Tech Conference',
            description='A conference about the latest in technology.',
            category='seminar',
            start_time='2025-05-01 09:00:00',
            end_time='2025-05-01 17:00:00',
            location='Tech Park, City Center',
            latitude=10.762622,
            longitude=106.660172,
            total_tickets=100,
            ticket_price=500000
        )
        event1.tags.add(Tag.objects.get(name='tech'))

    if not Event.objects.filter(title='Health Workshop').exists():
        event2 = Event.objects.create(
            organizer=organizer,
            title='Health Workshop',
            description='A workshop focused on health and wellness.',
            category='workshop',
            start_time='2025-06-10 10:00:00',
            end_time='2025-06-10 15:00:00',
            location='Health Center, District 1',
            latitude=10.762622,
            longitude=106.660172,
            total_tickets=50,
            ticket_price=300000,
            poster='https://res.cloudinary.com/ds05mb5xf/image/upload/v1744458340/mca9ohuf3hwohefenzrk.jpg'
        )
        event2.tags.add(Tag.objects.get(name='health'))

    if not Event.objects.filter(title='Music Festival').exists():
        event3 = Event.objects.create(
            organizer=organizer,
            title='Music Festival',
            description='A festival featuring live music performances.',
            category='festival',
            start_time='2025-07-20 18:00:00',
            end_time='2025-07-20 23:00:00',
            location='Open Air Stadium, District 7',
            latitude=10.762622,
            longitude=106.660172,
            total_tickets=200,
            ticket_price=700000,
            poster='https://res.cloudinary.com/ds05mb5xf/image/upload/v1744458340/mca9ohuf3hwohefenzrk.jpg'
        )
        event3.tags.add(Tag.objects.get(name='music'))