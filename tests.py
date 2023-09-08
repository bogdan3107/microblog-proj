#!/usr/bin/env python
from datetime import datetime, timedelta
import unittest
from app import create_app, db
from app.models import User, Post
from config import Config
from whoosh.index import create_in
from whoosh.fields import *
from app.search import add_to_index, remove_from_index, query_index
import tempfile, shutil


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    ELASTICSEARCH_URL = None


class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username='susan')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_avatar(self):
        u = User(username='john', email='john@example.com')
        self.assertEqual(u.avatar(128), ('https://www.gravatar.com/avatar/'
                                         'd4c74594d841139328695756648b6bd6'
                                         '?d=identicon&s=128'))

    def test_follow(self):
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        self.assertEqual(u1.followed.all(), [])
        self.assertEqual(u1.followers.all(), [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 1)
        self.assertEqual(u1.followed.first().username, 'susan')
        self.assertEqual(u2.followers.count(), 1)
        self.assertEqual(u2.followers.first().username, 'john')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 0)
        self.assertEqual(u2.followers.count(), 0)

    def test_follow_posts(self):
        # create four users
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        u3 = User(username='mary', email='mary@example.com')
        u4 = User(username='david', email='david@example.com')
        db.session.add_all([u1, u2, u3, u4])

        # create four posts
        now = datetime.datetime.utcnow()
        p1 = Post(body="post from john", author=u1,
                  timestamp=now + timedelta(seconds=1))
        p2 = Post(body="post from susan", author=u2,
                  timestamp=now + timedelta(seconds=4))
        p3 = Post(body="post from mary", author=u3,
                  timestamp=now + timedelta(seconds=3))
        p4 = Post(body="post from david", author=u4,
                  timestamp=now + timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # setup the followers
        u1.follow(u2)  # john follows susan
        u1.follow(u4)  # john follows david
        u2.follow(u3)  # susan follows mary
        u3.follow(u4)  # mary follows david
        db.session.commit()

        # check the followed posts of each user
        f1 = u1.followed_posts().all()
        f2 = u2.followed_posts().all()
        f3 = u3.followed_posts().all()
        f4 = u4.followed_posts().all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])



class TestSearch(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.index_dir = tempfile.mkdtemp()
        self.index = create_in(self.index_dir, schema=Schema(id=ID(stored=True), title=TEXT(stored=True), body=TEXT))
        self.client = self.app.test_client()
        db.create_all()

    def tearDown(self):
        shutil.rmtree(self.index_dir)


    def test_add_to_index(self):
        post = Post(body="This is a test post.")
        add_to_index(self.index, post)

        # Проверяем, что запись добавлена в индекс
        with self.index.searcher() as searcher:
            results = query_index(self.index, "Test", 1, 10)
            self.assertEqual(len(results), 1)

    def test_remove_from_index(self):
        post = Post(body="This is a test post.")
        add_to_index(self.index, post)

        # Удаляем запись из индекса
        remove_from_index(self.index, post)

        # Проверяем, что запись больше нет в индексе
        with self.index.searcher() as searcher:
            results = query_index(self.index, "Test", 1, 10)
            self.assertEqual(len(results), 0)

    def test_query_index(self):
        post = Post(body="This is a test post.")
        add_to_index(self.index, post)

        # Выполняем запрос к индексу
        ids, total = query_index(self.index, "Test", page=1, per_page=10)

        # Проверяем, что найдена одна запись
        self.assertEqual(len(ids), 1)
        # Проверяем, что общее количество результатов равно 1
        self.assertEqual(total, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)