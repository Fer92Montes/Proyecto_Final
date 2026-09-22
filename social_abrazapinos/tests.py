from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Friendship, Post, Profile


class SocialAppTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ana', password='Test1234')
        self.friend = User.objects.create_user(username='luis', password='Test1234')
        self.other = User.objects.create_user(username='marta', password='Test1234')
        Profile.objects.get_or_create(user=self.user)
        Profile.objects.get_or_create(user=self.friend)
        Profile.objects.get_or_create(user=self.other)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/social/login/', response.headers.get('Location', ''))

    def test_authenticated_user_can_access_profile(self):
        self.client.login(username='ana', password='Test1234')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_friend_relationship_and_friend_visibility(self):
        self.client.login(username='ana', password='Test1234')
        response = self.client.get(reverse('add_friend', args=['luis']))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Friendship.objects.filter(from_user=self.user, to_user=self.friend).exists())

        Post.objects.create(
            author=self.friend,
            title='Post de amigo',
            content='Contenido visible para amigos',
            visibility='friends',
        )

        response = self.client.get(reverse('social_home'))
        self.assertContains(response, 'Post de amigo')
